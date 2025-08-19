"""
Lambda function to generate the introduction section of the Bedrock Brief newsletter
"""

import json
import boto3
import os
import requests
import base64
import random
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
        "q": "aws ai -site:amazon.com -site:wsj.com -site:bloomberg.com -site:youtube.com, -site:investors.com -site:reuters.com -site:crn.com",
        # "q": "aws ai -site:amazon.com -site:youtube.com",
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


def generate_image_prompt_from_introduction(introduction_text: str, model_id: str = BEDROCK_MODEL_ID) -> Optional[str]:
    """
    Use the primary LLM to generate a single high-quality image prompt for Titan based on the introduction.
    The prompt should describe a horizontal, text-free, creative feature image capturing the introduction's themes.
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

        prompt = (
            "Create a single creative prompt for an AI image model (Amazon Titan Image Generator) based on the newsletter introduction below.\n"
            "Requirements:\n"
            "- Abstract, cartoony imagery only (no people, no faces)\n"
            "- Include at least one rock element\n"
            "- No text, lettering, watermarks, logos, trademarks, or brand names\n"
            "- Do not depict specific products, UIs, or copyrighted characters\n"
            "- Horizontal/wide aspect composition suitable for a feature banner\n"
            "- Keep under 30 words.\n\n"
            "Respond with ONLY the image prompt text, no quotes or extra narration.\n\n"
            f"Introduction:\n{introduction_text}\n"
        )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
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
        return response_body['content'][0]['text'].strip()
    except Exception as e:
        print(f"Error generating image prompt: {e}")
        return None


def generate_feature_image_and_upload(prompt: str, bucket_name: str, base_key: str) -> Optional[str]:
    """
    Generate a horizontal feature image using Titan v2 and upload to S3.

    Returns the S3 key of the uploaded image on success, otherwise None.
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        s3_client = boto3.client('s3')

        seed = random.randint(0, 2_147_483_647)

        # Build safe attempt prompts: original with safety prefix plus abstract fallbacks
        safety_prefix = (
            "Abstract, text-free, no people or faces, no logos or trademarks, no brand names. "
        )
        attempts: List[str] = []
        if prompt:
            attempts.append((safety_prefix + (prompt or "")).strip())

        fallback_prompts = [
            "Abstract cartoony waves and circuit traces in deep blue and teal, clean minimal tech banner, no text or logos",
            "Isometric circuit board patterns and network nodes, monochrome line art, modern wide banner, no text or branding",
            "Gradient mesh with polygonal network lines and subtle glows, futuristic technology vibe, wide banner, no text or logos",
        ]
        attempts.extend(fallback_prompts)

        for idx, attempt_prompt in enumerate(attempts):
            try:
                safe_prompt = attempt_prompt.strip()[:512]
                cfg = 8.0 if idx == 0 else (6.5 if idx == 1 else 5.5)
                native_request = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": safe_prompt
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "height": 768,
                        "width": 1408,
                        "cfgScale": cfg,
                        "seed": seed + idx
                    }
                }

                request = json.dumps(native_request)
                response = bedrock.invoke_model(
                    modelId="amazon.titan-image-generator-v2:0",
                    body=request,
                    accept="application/json",
                    contentType="application/json",
                )
                model_response = json.loads(response["body"].read())
                base64_image_data = model_response["images"][0]
                image_bytes = base64.b64decode(base64_image_data)
                key = f"{base_key}.png"
                s3_client.put_object(Bucket=bucket_name, Key=key, Body=image_bytes, ContentType="image/png")
                return key
            except Exception as e:
                err_text = str(e)
                print(f"Image generation attempt {idx+1} failed: {err_text}")
                # Try next attempt if content was blocked or request malformed
                if "blocked" in err_text.lower() or "validationexception" in err_text.lower() or "malformed" in err_text.lower():
                    continue
                # Otherwise still continue to try fallbacks
                continue
    except Exception as e:
        print(f"Error generating or uploading feature image: {e}")
        return None


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
        
        # Generate a feature image prompt using the LLM and create a Titan image
        image_prompt = generate_image_prompt_from_introduction(response_text)
        image_key = None
        if image_prompt:
            base_key = f"introduction_{date_str}_feature"
            image_key = generate_feature_image_and_upload(image_prompt, bucket_name, base_key)
            if image_key:
                print(f"Successfully saved feature image to S3: s3://{bucket_name}/{image_key}")
            else:
                print("Feature image generation returned no key")
        else:
            print("Image prompt generation failed; skipping image generation")

        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': (
                    f"Introduction saved: s3://{bucket_name}/{filename}" +
                    (f" | Feature image: s3://{bucket_name}/{image_key}" if image_key else "")
                )
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