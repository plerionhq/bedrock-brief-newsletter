"""
Lambda function to generate the quarry section of the Bedrock Brief newsletter
"""

import json
import boto3
import os
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from utils import BEDROCK_SYSTEM_PROMPT, is_ai_related

# Get Bedrock model ID from environment variable
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Get API keys from environment variables
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def fetch_aws_ml_blog_posts(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch AWS ML blog posts from the RSS feed.
    
    Args:
        cutoff_date: Only fetch blog posts after this date
        
    Returns:
        List of blog post dictionaries
    """
    rss_url = "https://aws.amazon.com/blogs/machine-learning/feed/"
    
    try:
        print("Fetching blog posts from AWS ML blog...")
        feed = feedparser.parse(rss_url)
        posts = []
        
        for entry in feed.entries:
            # Parse the published date with timezone awareness
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
                published_date = published_date.replace(tzinfo=timezone.utc)
            else:
                published_date = datetime.now(timezone.utc)
            
            # Filter by cutoff date if provided
            if cutoff_date and published_date < cutoff_date:
                continue

            # if not is_ai_related(entry.title, entry.description):
            #     continue
            
            post = {
                'title': entry.title,
                'link': entry.link,
                'published_date': published_date,
                'description': entry.description,
                'author': getattr(entry, 'author', 'Unknown')
            }
            posts.append(post)
        
        print(f"Found {len(posts)} posts from AWS ML blog")
        return posts  # Limit to 10 most recent posts
        
    except Exception as e:
        print(f"Error fetching AWS ML blog posts: {e}")
        return []


def analyze_posts_with_bedrock(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use Bedrock to analyze posts and select the best one.
    
    Args:
        posts: List of blog post dictionaries
        
    Returns:
        Dictionary with the best post information
    """
    if not posts:
        return {}
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Format posts for analysis
        formatted_posts = []
        for i, post in enumerate(posts, 1):
            formatted_post = f"""
Number {i}:
Title: {post['title']}
Published: {post['published_date'].strftime('%Y-%m-%d %H:%M:%S')}
Author: {post['author']}
Link: {post['link']}
Description: {post['description']}
===============================================
"""
            formatted_posts.append(formatted_post)
        
        formatted_posts_str = "\n".join(formatted_posts)
        
        # Create the analysis prompt
        analysis_prompt = f"""
You are an expert content analyst specializing in AWS Machine Learning and AI technologies. 
You have been given a list of recent blog posts from the AWS Machine Learning blog.

Please analyze the following {len(posts)} blog posts and determine which one is the BEST overall.
Consider the following criteria:
1. Technical depth and educational value
2. Innovation and cutting-edge content
3. Clarity and quality of writing
4. Exclusion of sales pitches
5. Uniqueness and originality of the content
6. Applicability to largest audience

Here are the posts to analyze:

{formatted_posts_str}

Please provide your analysis in the following JSON format:
{{
    "best_post_number": <integer>
}}
"""
        
        # Call Bedrock for analysis
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response.get('body').read())
        analysis = response_body['content'][0]['text']
        
        # Parse JSON response
        try:
            if '```json' in analysis:
                json_start = analysis.find('```json') + 7
                json_end = analysis.find('```', json_start)
                analysis_json = analysis[json_start:json_end].strip()
            else:
                start_idx = analysis.find('{')
                end_idx = analysis.rfind('}') + 1
                analysis_json = analysis[start_idx:end_idx]
            
            result = json.loads(analysis_json)

            # look up the post number in the posts list
            best_post_number = result.get('best_post_number', -1)
            best_post = posts[best_post_number - 1]

            return best_post
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Bedrock analysis response: {e}")
            return {}
            
    except Exception as e:
        print(f"Error analyzing posts with Bedrock: {e}")
        return {}


def generate_blog_summary(best_post: Dict[str, Any]) -> str:
    """
    Generate an engaging summary of the best blog post using Bedrock.
    
    Args:
        best_post: Dictionary containing the best post information
        
    Returns:
        Engaging summary string
    """
    if not best_post:
        return "No featured blog post available."
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Create the summary prompt
        summary_prompt = f"""{BEDROCK_SYSTEM_PROMPT}

Based on the following AWS ML blog post, write a 3 sentence, 1 paragraph summary that captures the essence and value of the post. Include at least one technical detail that an engineer would find interesting.
RETURN ONLY THE SUMMARY, NO OTHER TEXT.
Do not include any intro, explanation, or preamble.

Title: {best_post['title']}
Description: {best_post['description']}
"""
        
        # Call Bedrock for summary
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": summary_prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response.get('body').read())
        summary = response_body['content'][0]['text'].strip()
        
        return summary
        
    except Exception as e:
        print(f"Error generating blog summary with Bedrock: {e}")
        return f"{best_post.get('best_post_title', 'Featured Blog Post')} - Check out this interesting AWS ML blog post for technical insights and practical guidance."


def get_featured_blog(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the most relevant blog post as the featured post using Bedrock analysis.
    
    Args:
        posts: List of blog posts
        
    Returns:
        Featured blog post dictionary with summary
    """
    if not posts:
        return {}
    
    # Use Bedrock to analyze and select the best post
    best_post = analyze_posts_with_bedrock(posts)
    
    if not best_post:
        # Fallback to first post if analysis fails
        if posts:
            best_post = posts[0]
    
    # Generate engaging summary for the best post
    summary = generate_blog_summary(best_post)
    best_post['summary'] = summary
    
    return best_post


def get_the_quarry_content(cutoff_date: datetime) -> Dict[str, Any]:
    """
    Get all The Quarry content (blog posts).
    
    Args:
        cutoff_date: Cutoff date for filtering content
        
    Returns:
        Dictionary with featured_blog and other_blogs
    """
    print(f"Fetching The Quarry content since {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Fetch AWS ML blog posts
    aws_posts = fetch_aws_ml_blog_posts(cutoff_date)
    
    if not aws_posts:
        return {
            "featured_blog": {},
            "other_blogs": []
        }
    
    # Select featured blog
    featured_blog = get_featured_blog(aws_posts)
    
    # Get other blogs (excluding featured)
    # Since we don't know which one was selected by Bedrock, we'll include all posts
    # but mark the featured one differently in the template
    other_blogs = []
    for post in aws_posts:
        # Skip if this is the featured post (by URL matching)
        if featured_blog and post['link'] == featured_blog.get('url'):
            continue
        
        other_blogs.append({
            'title': post['title'],
            'url': post['link'],
            'author': post['author'],
            'published_date': post['published_date'].strftime('%Y-%m-%d'),
        })
    
    return {
        "featured_blog": featured_blog,
        "other_blogs": other_blogs  # Limit to 5 other blogs
    }


def generate_the_quarry(cutoff_date: datetime) -> str:
    """
    Generate the quarry section content.
    
    Args:
        cutoff_date: The cutoff date for the newsletter as a datetime object with UTC timezone
        
    Returns:
        Generated quarry section text
        
    Raises:
        Exception: If content generation fails
    """
    # Validate cutoff_date is a datetime object with UTC timezone
    if not isinstance(cutoff_date, datetime):
        raise ValueError("cutoff_date must be a datetime object")
    
    # Get the content
    quarry_content = get_the_quarry_content(cutoff_date)
    
    # Load and render the template
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("the_quarry.md")
    
    return template.render(
        featured_blog=quarry_content.get("featured_blog"),
        other_blogs=quarry_content.get("other_blogs", [])
    )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate quarry section for the Bedrock Brief newsletter
    """
    try:
        # Extract and validate cutoff_date from event parameters
        if 'parameters' not in event:
            raise ValueError("parameters are required but not provided")
        
        # Handle parameters as array of objects with name/value properties
        cutoff_date_str = None
        for param in event['parameters']:
            if param.get('name') == 'cutoff_date':
                cutoff_date_str = param.get('value')
                break
        
        if not cutoff_date_str:
            raise ValueError("cutoff_date parameter is required but not provided")
        
        # Convert string to datetime object with UTC timezone
        try:
            cutoff_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"cutoff_date must be in format 'YYYY-MM-DD HH:MM:SS', got: {cutoff_date_str}")
        
        # Generate the quarry content
        response_text = generate_the_quarry(cutoff_date)
        # response_text = "test"
        
        # Save content to S3 instead of returning it
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate filename based on template name and date
        date_str = cutoff_date.strftime("%Y-%m-%d")
        filename = f"the_quarry_{date_str}.md"
        
        # Upload content to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=response_text,
            ContentType='text/markdown'
        )
        
        print(f"Successfully saved the quarry content to S3: s3://{bucket_name}/{filename}")
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': f"The quarry content successfully saved to S3: s3://{bucket_name}/{filename}"
            }
        }
        
        function_response = {
            'actionGroup': event.get('actionGroup', ''),
            'function': event.get('function', ''),
            'functionResponse': {
                'responseBody': response_body
            }
        }
        
        # Get session attributes from event
        session_attributes = event.get("sessionAttributes", {})
        prompt_session_attributes = event.get("promptSessionAttributes", {})
        
        # Create full response
        full_response = {
            'messageVersion': '1.0',
            'response': function_response,
            'sessionAttributes': session_attributes,
            'promptSessionAttributes': prompt_session_attributes
        }
        
        # Debug: Print formatted full response
        # print("=== GENERATE THE QUARRY FUNCTION RESPONSE ===")
        # print(json.dumps(full_response, indent=2, default=str))
        # print("=============================================")
        
        # Return proper Bedrock agent response format
        return full_response
        
    except Exception as e:
        # Error response in same format
        error_text = f"Error occurred while generating quarry: {str(e)}"
        
        response_body = {
            'TEXT': {
                'body': error_text
            }
        }
        
        function_response = {
            'actionGroup': event.get('actionGroup', ''),
            'function': event.get('function', ''),
            'functionResponse': {
                'responseBody': response_body
            }
        }
        
        session_attributes = event.get("sessionAttributes", {})
        prompt_session_attributes = event.get("promptSessionAttributes", {})
        
        full_response = {
            'messageVersion': '1.0',
            'response': function_response,
            'sessionAttributes': session_attributes,
            'promptSessionAttributes': prompt_session_attributes
        }
        
        return full_response 