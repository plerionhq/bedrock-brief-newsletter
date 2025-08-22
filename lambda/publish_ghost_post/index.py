"""
Lambda function to publish posts to Ghost.org
"""

import json
import os
import requests
import time
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

# Import PyJWT for JWT token creation
try:
    import jwt as PyJWT
except ImportError:
    print("Error: PyJWT package not found. Install it with: pip install PyJWT")
    raise ImportError("PyJWT is required for Ghost integration")

# Get environment variables
GHOST_URL = os.environ.get("GHOST_URL")
GHOST_API_KEY = os.environ.get("GHOST_ADMIN_API_KEY")


def create_jwt_token(admin_api_key: str) -> str:
    """
    Create a JWT token for Ghost Admin API authentication.
    
    Args:
        admin_api_key: The Ghost admin API key
        
    Returns:
        JWT token string
    """
    # Split key into ID and secret
    key_id, secret = admin_api_key.split(':')
    
    # Create JWT payload
    iat = int(time.time())
    exp = iat + 5 * 60  # 5 minute expiry
    
    payload = {
        'iat': iat,
        'exp': exp,
        'aud': '/admin/'
    }
    
    # Create JWT header
    header = {
        'alg': 'HS256',
        'kid': key_id,
        'typ': 'JWT'
    }
    
    # Encode JWT token using PyJWT
    token = PyJWT.encode(
        payload, 
        bytes.fromhex(secret), 
        algorithm='HS256', 
        headers=header
    )
    
    return token


def create_and_schedule_post(title: str, content: str, ghost_url: str, admin_api_key: str, feature_image_url: Optional[str] = None) -> Optional[dict]:
    """
    Create and schedule a post in Ghost.org for publication and email.
    
    Args:
        title: Post title
        content: Post content (markdown)
        ghost_url: Ghost site URL
        admin_api_key: Ghost admin API key
        
    Returns:
        Dictionary with post details if successful, None if failed
    """
    try:
        # Create JWT token
        jwt_token = create_jwt_token(admin_api_key)
        
        # Set up API headers
        headers = {
            'Authorization': f'Ghost {jwt_token}',
            'Content-Type': 'application/json',
            'Accept-Version': 'v5.0'
        }
        
        # Create lexical structure with markdown element
        lexical_content = {
            "root": {
                "children": [
                    {
                        "children": [],
                        "direction": None,
                        "format": "",
                        "indent": 0,
                        "type": "paragraph",
                        "version": 1
                    }
                ],
                "direction": None,
                "format": "",
                "indent": 0,
                "type": "root",
                "version": 1
            }
        }
        
        # Add markdown element to the lexical structure
        markdown_element = {
            "type": "markdown",
            "version": 1,
            "markdown": content
        }
        
        # Insert markdown element as the first child
        lexical_content["root"]["children"].insert(0, markdown_element)

        # Create post data using Lexical format - start as draft
        post_data = {
            "posts": [{
                "title": title,
                "lexical": json.dumps(lexical_content),
                "status": "draft",
                "featured": True,
                "visibility": "public"
            }]
        }
        
        # Step 1: Create the draft post
        create_url = f"{ghost_url}/ghost/api/admin/posts/"
        response = requests.post(create_url, headers=headers, json=post_data)
        
        if response.status_code != 201:
            print(f"Failed to create Ghost post. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        post_response = response.json()
        post = post_response['posts'][0]
        post_id = post['id']
        post_updated_at = post['updated_at']  # Get the actual updated_at from the created post
        


        # Optional: Update post with feature image before scheduling
        if feature_image_url:
            update_headers = {
                'Authorization': f'Ghost {jwt_token}',
                'Content-Type': 'application/json',
                'Accept-Version': 'v5.0'
            }
            update_data = {
                "posts": [{
                    "id": post_id,
                    "updated_at": post_updated_at,
                    "feature_image": feature_image_url,
                    "feature_image_alt": None,
                    "feature_image_caption": None,
                    "featured": True
                }]
            }
            update_url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/"
            update_response = requests.put(update_url, headers=update_headers, json=update_data)
            if update_response.status_code != 200:
                print(f"Failed to update Ghost post with feature image. Status: {update_response.status_code}")
                print(f"Response: {update_response.text}")
            else:
                updated = update_response.json()
                post_updated_at = updated['posts'][0]['updated_at']
        
        # Step 2: Calculate the next available Wednesday at 8 AM Eastern Time
        
        # Get current time in UTC
        current_utc = datetime.now(timezone.utc)
        
        # Calculate days until next Wednesday (0 = Monday, 1 = Tuesday, 2 = Wednesday, etc.)
        days_until_wednesday = (2 - current_utc.weekday()) % 7
        
        # If today is Wednesday, check if we can schedule for today or need to wait for next week
        if days_until_wednesday == 0:  # Today is Wednesday
            # Check if it's before 8 AM ET (13:00 UTC) - if so, schedule for today
            # If it's after 8 AM ET, schedule for next Wednesday
            current_hour_utc = current_utc.hour
            if current_hour_utc < 13:  # Before 1 PM UTC = before 8 AM ET
                days_until_wednesday = 0  # Schedule for today
            else:
                days_until_wednesday = 7  # Schedule for next Wednesday
        else:
            # Not Wednesday, schedule for next Wednesday
            pass
        
        # Calculate the target Wednesday at 8 AM Eastern Time
        # Eastern Time is UTC-5 (EST) or UTC-4 (EDT), so 8 AM ET = 13:00 UTC (EST) or 12:00 UTC (EDT)
        # For simplicity, we'll use 13:00 UTC which covers both cases
        target_wednesday = current_utc + timedelta(days=days_until_wednesday)
        scheduled_time_utc = target_wednesday.replace(hour=13, minute=0, second=0, microsecond=0)
        
        # Convert back to Eastern Time for display (approximate)
        eastern_offset = timedelta(hours=5)  # EST offset
        scheduled_time_eastern = scheduled_time_utc - eastern_offset
        

        
        # Step 3: Schedule the post using PUT request
        schedule_data = {
            "posts": [{
                "updated_at": post_updated_at,  # Use the actual updated_at from the created post
                "status": "scheduled",
                "published_at": scheduled_time_utc.isoformat().replace('+00:00', 'Z')
            }]
        }
        
        # Schedule the post using PUT with newsletter parameters for email sending
        schedule_url = f"{ghost_url}/ghost/api/admin/posts/{post_id}/?newsletter=default-newsletter&email_segment=all"
        schedule_response = requests.put(schedule_url, headers=headers, json=schedule_data)
        
        if schedule_response.status_code != 200:
            print(f"Failed to schedule Ghost post. Status code: {schedule_response.status_code}")
            print(f"Response: {schedule_response.text}")
            return {
                'id': post_id,
                'title': post['title'],
                'url': post.get('url'),
                'status': 'draft',
                'error': 'Failed to schedule post',
                'scheduled_at': None,
                'scheduled_at_eastern': None
            }
        
        # Step 4: Configure email newsletter sending
        # The newsletter parameter is added to the URL when scheduling
        # Ghost will automatically send emails when the post is published
        
        return {
            'id': post_id,
            'title': post['title'],
            'url': post.get('url'),
            'status': 'scheduled',
            'scheduled_at': scheduled_time_utc.isoformat().replace('+00:00', 'Z'),
            'scheduled_at_eastern': scheduled_time_eastern.strftime('%Y-%m-%d %I:%M %p ET'),
            'email_configured': True
        }
        
    except Exception as e:
        print(f"Error creating and scheduling Ghost post: {e}")
        return None



def publish_ghost_post(title: str, content: str) -> Dict[str, Any]:
    """
    Publish a post to Ghost.org.
    
    Args:
        title: Post title
        content: Post content (markdown)
        
    Returns:
        Dictionary with result information
    """
    if not GHOST_URL or not GHOST_API_KEY:
        raise ValueError("GHOST_URL and GHOST_ADMIN_API_KEY environment variables are required")
    
    # Create and schedule post (no image handling here; done with cutoff date in publish_newsletter_to_ghost)
    post_result = create_and_schedule_post(title, content, GHOST_URL, GHOST_API_KEY, None)
    
    if not post_result:
        return {
            'success': False,
            'error': 'Failed to create and schedule post'
        }
    
    return {
        'success': True,
        'post_id': post_result['id'],
        'title': post_result['title'],
        'url': post_result.get('url'),
        'status': post_result['status'],
        'scheduled_at': post_result.get('scheduled_at'),
        'email_configured': post_result.get('email_configured', False)
    }


def read_newsletter_from_s3(bucket_name: str, date_str: str) -> str:
    """
    Read the newsletter content from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket containing the newsletter
        date_str: Date string in format 'YYYY-MM-DD'
        
    Returns:
        Newsletter content as string
        
    Raises:
        Exception: If newsletter content cannot be read from S3
    """
    try:
        s3_client = boto3.client('s3')
        
        # Look for newsletter_{date}.md in the bucket
        filename = f"newsletter_{date_str}.md"
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=filename
        )
        
        newsletter_content = response['Body'].read().decode('utf-8')
        
        return newsletter_content
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise Exception(f"Newsletter file '{filename}' not found in S3 bucket: {bucket_name}")
        else:
            raise Exception(f"Error reading from S3: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error reading from S3: {e}")


def publish_newsletter_to_ghost(title: str, cutoff_date: datetime) -> Dict[str, Any]:
    """
    Publish a newsletter post to Ghost.org by reading content from S3.
    
    Args:
        title: Post title
        cutoff_date: The cutoff date for the newsletter
        
    Returns:
        Dictionary with result information
    """
    if not GHOST_URL or not GHOST_API_KEY:
        raise ValueError("GHOST_URL and GHOST_ADMIN_API_KEY environment variables are required")
    
    # Get bucket name from environment
    bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
    
    # Format date for filename
    date_str = cutoff_date.strftime("%Y-%m-%d")
    
    # Read newsletter content from S3
    newsletter_content = read_newsletter_from_s3(bucket_name, date_str)

    # Upload today's feature image first (assume PNG) — required
    s3 = boto3.client('s3')
    image_key = f"introduction_{date_str}_feature.png"
    # Ensure it exists in S3
    try:
        s3.head_object(Bucket=bucket_name, Key=image_key)
    except Exception:
        raise Exception(f"Required feature image not found in S3: s3://{bucket_name}/{image_key}")

    # Download and upload to Ghost Images API
    obj = s3.get_object(Bucket=bucket_name, Key=image_key)
    data = obj['Body'].read()
    jwt_token = create_jwt_token(GHOST_API_KEY)
    upload_headers = {
        'Authorization': f'Ghost {jwt_token}',
        'Accept-Version': 'v5.0'
    }
    files = {
        'file': (image_key, data, 'image/png')
    }
    upload_url = f"{GHOST_URL}/ghost/api/admin/images/upload/"
    upload_resp = requests.post(upload_url, headers=upload_headers, files=files)
    if upload_resp.status_code != 201:
        raise Exception(f"Ghost feature image upload failed: {upload_resp.status_code} {upload_resp.text}")

    img_json = upload_resp.json()
    feature_image_url = img_json.get('images', [{}])[0].get('url')
    if not feature_image_url:
        raise Exception("Ghost did not return an image URL for the uploaded feature image")
    print(f"Uploaded feature image to Ghost: {feature_image_url}")

    # Publish the post with required feature image URL
    return create_and_schedule_post(title, newsletter_content, GHOST_URL, GHOST_API_KEY, feature_image_url)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Publish a newsletter post to Ghost.org by reading content from S3
    """
    try:
        # Extract and validate parameters from event
        if 'parameters' not in event:
            raise ValueError("parameters are required but not provided")
        
        # Handle parameters as array of objects with name/value properties
        title = None
        cutoff_date_str = None
        
        for param in event['parameters']:
            if param.get('name') == 'title':
                title = param.get('value')
            elif param.get('name') == 'cutoff_date':
                cutoff_date_str = param.get('value')
        
        if not title:
            raise ValueError("title parameter is required but not provided")
        
        if not cutoff_date_str:
            raise ValueError("cutoff_date parameter is required but not provided")
        
        # Convert string to datetime object with UTC timezone
        try:
            cutoff_date = datetime.strptime(cutoff_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"cutoff_date must be in format 'YYYY-MM-DD HH:MM:SS', got: {cutoff_date_str}")
        
        # Publish the newsletter post by reading content from S3
        result = publish_newsletter_to_ghost(title, cutoff_date)
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': json.dumps(result, indent=2)
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
        error_text = f"Error occurred while publishing Ghost post: {str(e)}"
        
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