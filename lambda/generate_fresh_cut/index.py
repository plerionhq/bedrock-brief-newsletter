"""
Lambda function to generate the fresh cut section of the Bedrock Brief newsletter
"""

import json
import boto3
import os
import requests
import feedparser
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from utils import is_ai_related, BEDROCK_SYSTEM_PROMPT, get_secret

# Get Bedrock model ID from environment variable
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Get API keys from environment variables
SEARCH_API_KEY = get_secret("SEARCH_API_KEY")
YOUTUBE_API_KEY = get_secret("YOUTUBE_API_KEY")





def fetch_aws_announcements(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch AWS announcements related to Bedrock and AI services.
    
    Args:
        cutoff_date: Only fetch announcements after this date
        
    Returns:
        List of announcement dictionaries
    """
    # AWS RSS feed for recent announcements
    rss_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(rss_url)
        announcements = []
        
        for entry in feed.entries:
            # Parse the publication date and make it timezone-aware
            if hasattr(entry, 'published_parsed'):
                # Create naive datetime from parsed tuple
                pub_date = datetime(*entry.published_parsed[:6])
                # Assume UTC timezone for RSS feed dates
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            else:
                pub_date = None
            
            # Filter by cutoff date if provided
            if cutoff_date and pub_date and pub_date < cutoff_date:
                continue
            
            # Check if the announcement is related to AI services
            if is_ai_related(entry.title, entry.description):
                # Generate summary using Claude
                summary = generate_announcement_summary(entry.title, entry.description)
                
                announcement = {
                    "title": entry.title,
                    "content": summary,
                    "url": entry.link,
                    "published_date": pub_date.isoformat() if pub_date else None
                }
                announcements.append(announcement)
        
        return announcements[:10]  # Limit to 10 most recent AI-related announcements
        
    except Exception as e:
        print(f"Error fetching AWS announcements: {e}")
        return []


def generate_announcement_summary(title: str, description: str) -> str:
    """
    Generate a summary of an AWS announcement using Claude.
    
    Args:
        title: Announcement title
        description: Announcement description
        
    Returns:
        Generated summary
    """
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Prepare the user prompt
        user_prompt = f"""Write a one sentence summary of this news item. Make sure you include the most important technical detail. Make it enticing to click and clear why someone should click. Ensure it's clear why the reader should care without using marketing/corporate speak. Avoid jargon and make it understandable by an entry level developer. Avoid "now supports" and "has added" language. Do not sound like an AWS salesperson.
Do not include any intro, explanation, or preamble.

Title: {title}
Description: {description}

Summary:"""
        
        # Prepare the request body
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 150,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        })
        
        # Make the API call
        response = bedrock.invoke_model(
            body=body,
            modelId=BEDROCK_MODEL_ID
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        summary = response_body['content'][0]['text'].strip()
        
        return summary
        
    except Exception as e:
        print(f"Error generating summary with Claude: {e}")
        # Fallback to a simple summary
        return f"{title} - {description[:200]}..."


def generate_fresh_cut(cutoff_date: datetime) -> str:
    """
    Generate the fresh cut section content.
    
    Args:
        cutoff_date: The cutoff date for the newsletter as a datetime object with UTC timezone
        
    Returns:
        Generated fresh cut section text
        
    Raises:
        Exception: If content generation fails
    """
    # Validate cutoff_date is a datetime object with UTC timezone
    if not isinstance(cutoff_date, datetime):
        raise ValueError("cutoff_date must be a datetime object")
    
    # Get AWS announcements
    announcements = fetch_aws_announcements(cutoff_date)
    
    # Load and render the template
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("fresh_cut.md")
    
    return template.render(announcements=announcements)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate fresh cut section for the Bedrock Brief newsletter
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
        
        # Generate the fresh cut content
        response_text = generate_fresh_cut(cutoff_date)
        # response_text = "test"

        # Save content to S3 instead of returning it
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate filename based on template name and date
        date_str = cutoff_date.strftime("%Y-%m-%d")
        filename = f"fresh_cut_{date_str}.md"
        
        # Upload content to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=response_text,
            ContentType='text/markdown'
        )
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': f"Fresh cut content successfully saved to S3: s3://{bucket_name}/{filename}"
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
        
        # Return proper Bedrock agent response format
        return full_response
        
    except Exception as e:
        # Error response in same format
        error_text = f"Error occurred while generating fresh cut: {str(e)}"
        
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