"""
Lambda function to generate the introduction section of the Bedrock Brief newsletter
"""

import json
import boto3
import os
import requests
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from newspaper import Article
import sys

from utils import BEDROCK_SYSTEM_PROMPT

# Get Bedrock model ID from environment variable
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Get API keys from environment variables
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def fetch_aws_ai_news(api_key: str, num_results: int = 5) -> Optional[Dict]:
    """
    Fetch the latest Google News results about "aws ai".
    
    Args:
        api_key: The SearchAPI key
        num_results: Number of results to return (default: 5)
        
    Returns:
        Dictionary containing the API response or None if error
    """
    url = "https://www.searchapi.io/api/v1/search"
    params = {
        "engine": "google_news",
        "q": "aws ai -site:amazon.com -site:wsj.com -site:bloomberg.com -site:youtube.com, -site:investors.com",
        "time_period": "last_week",
        "num": num_results,
        "api_key": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None


def extract_article_with_newspaper(url: str) -> Optional[Dict]:
    """
    Extract article content using newspaper3k library.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Dictionary with 'title' and 'text' keys, or None if failed
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        return {
            'title': article.title,
            'text': article.text
        }
    except Exception as e:
        print(f"Error extracting article with newspaper3k: {e}")
        return None


def send_to_bedrock(articles: List[Dict], model_id: str = BEDROCK_MODEL_ID) -> Optional[str]:
    """
    Send articles to Bedrock to generate a newsletter introduction.
    
    Args:
        articles: List of article dictionaries with 'title' and 'text' keys
        model_id: Bedrock model ID to use
        
    Returns:
        Generated newsletter introduction text or None if failed
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Prepare the articles content for the prompt
        articles_content = ""
        for i, article in enumerate(articles, 1):
            articles_content += f"\nArticle {i}: {article['title']}\n"
            articles_content += f"Link: {article['link']}\n"
            articles_content += f"Content: {article['text'][:3000]}...\n"  # Truncate to avoid token limits
        
        # Combine system prompt with user prompt
        full_prompt = f"""{BEDROCK_SYSTEM_PROMPT}

You are an AI assistant tasked with writing a 3-paragraph introduction for "The Bedrock Brief" newsletter, which is a weekly newsletter about AI on AWS.

Based on the following recent AWS AI news articles, write an engaging 3-paragraph introduction that:
1. Summarizes the key trends and developments in AWS AI from the past week
2. Highlights the most important news and their implications
3. Includes at least one markdown link to a news article
4. Doesn't assume anything about the contents of the rest of the newsletter

DO NOT ADD HEADINGS
RESPOND WITH ONLY THE INTRODUCTION CONTENT, NO OTHER TEXT. DO NOT INCLUDE ANYTHING ELSE LIKE "Here is a 3-paragraph introduction"
Do not include any intro, explanation, or preamble.

Articles:
{articles_content}
"""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        })
        
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
        
    except ClientError as e:
        print(f"Error calling Bedrock: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error with Bedrock: {e}")
        return None


def get_news_articles() -> List[Dict]:
    """
    Fetch and process news articles for introduction generation.
    
    Returns:
        List of processed article dictionaries
    """
    # Get API key from environment variable
    api_key = SEARCH_API_KEY
    
    if not api_key:
        print("Warning: SEARCH_API_KEY environment variable not set. Using fallback introduction.")
        return []
    
    # Fetch the news data
    data = fetch_aws_ai_news(api_key)
    
    if not data or "organic_results" not in data:
        print("No news results found. Using fallback introduction.")
        return []
    
    organic_results = data["organic_results"]
    downloaded_articles = []
    
    for result in organic_results[:5]:  # Process top 5 results
        if result.get('link'):
            article_data = extract_article_with_newspaper(result['link'])
            
            if article_data and article_data.get('text'):
                downloaded_articles.append({
                    'title': article_data.get('title', result.get('title', 'No title')),
                    'text': article_data.get('text', ''),
                    'link': result.get('link', '')
                })
    
    return downloaded_articles


def generate_introduction(cutoff_date: datetime) -> str:
    """
    Generate an introduction based on recent AWS AI news.
    
    Args:
        cutoff_date: The cutoff date for the newsletter as a datetime object with UTC timezone
        
    Returns:
        Generated introduction text
        
    Raises:
        Exception: If news fetching fails or Bedrock generation fails
    """
    # Validate cutoff_date is a datetime object with UTC timezone
    if not isinstance(cutoff_date, datetime):
        raise ValueError("cutoff_date must be a datetime object")
    
    # Get news articles
    articles = get_news_articles()
    
    if not articles:
        raise Exception("Failed to fetch news articles for introduction generation")
    
    # Generate AI-powered introduction using Bedrock
    ai_introduction = send_to_bedrock(articles)
    
    if not ai_introduction:
        raise Exception("Failed to generate introduction using Bedrock")
    
    return ai_introduction


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate introduction section for the Bedrock Brief newsletter
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
        
        # Generate the introduction
        response_text = generate_introduction(cutoff_date)
        
        # Save content to S3 instead of returning it
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate filename based on template name and date
        date_str = cutoff_date.strftime("%Y-%m-%d")
        filename = f"introduction_{date_str}.md"
        
        # Upload content to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=response_text,
            ContentType='text/markdown'
        )
        
        print(f"Successfully saved introduction content to S3: s3://{bucket_name}/{filename}")
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': f"Introduction content successfully saved to S3: s3://{bucket_name}/{filename}"
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
        # print("=== GENERATE INTRODUCTION FUNCTION RESPONSE ===")
        # print(json.dumps(full_response, indent=2, default=str))
        # print("===============================================")
        
        # Return proper Bedrock agent response format
        return full_response
        
    except Exception as e:
        # Error response in same format
        error_text = f"Error occurred while generating introduction: {str(e)}"
        
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