"""
Lambda function to finalize and clean up newsletter content before publishing
"""

import json
import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional


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
            raise Exception(f"Newsletter file 'newsletter_{date_str}.md' not found in S3 bucket: {bucket_name}")
        else:
            raise Exception(f"Error reading from S3: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error reading from S3: {e}")


def finalize_newsletter_with_bedrock(newsletter_content: str, model_id: str) -> str:
    """
    Use Bedrock to clean up and finalize the newsletter content.
    
    Args:
        newsletter_content: Raw newsletter content to clean up
        model_id: Bedrock model ID to use
        
    Returns:
        Cleaned and finalized newsletter content
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Create the prompt for cleaning up the newsletter
        prompt = f"""You are the final reviewer of the Bedrock Brief newsletter. Your job is do minor cleanup for publication. All the text you output will be published

Your task:
1. Remove any AI-generated first-person answer boilertplate like "Here is a 3-paragraph summary you asked for", "I have summarized the best of the week for you", etc.
3. Add hints to what else is in the newsletter to the introduction (mention the other sections)
4. Fix any formatting issues or inconsistencies
6. Keep all the actual content and links intact

DO NOT add or remove any headings.
DO NOT make major changes to the content.
DO NOT remove content paragraphs.

Return ONLY the final Markdown content of the newsletter, no explanations or meta-commentary.

------
{newsletter_content}"""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 5000,
            "temperature": 0.0,
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
        finalized_content = response_body['content'][0]['text']
        
        return finalized_content
        
    except ClientError as e:
        print(f"Error calling Bedrock: {e}")
        raise Exception(f"Failed to finalize newsletter using Bedrock: {e}")
    except Exception as e:
        print(f"Unexpected error with Bedrock: {e}")
        raise Exception(f"Unexpected error finalizing newsletter: {e}")


def save_finalized_newsletter(bucket_name: str, date_str: str, finalized_content: str) -> bool:
    """
    Save the finalized newsletter back to S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        date_str: Date string in format 'YYYY-MM-DD'
        finalized_content: Cleaned newsletter content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = boto3.client('s3')
        
        # Save as newsletter_{date}.md (overwriting the original)
        filename = f"newsletter_final_{date_str}.md"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=finalized_content,
            ContentType='text/markdown'
        )
        
        return True
        
    except Exception as e:
        print(f"Error saving finalized newsletter to S3: {e}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Finalize and clean up newsletter content before publishing
    """
    try:
        # Extract and validate parameters from event
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
        
        # Get bucket name and model ID from environment
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Use default Bedrock model
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        # Format date for filename
        date_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Read the newsletter content from S3
        newsletter_content = read_newsletter_from_s3(bucket_name, date_str)
        
        # Finalize the newsletter using Bedrock
        finalized_content = finalize_newsletter_with_bedrock(newsletter_content, model_id)
        
        # Save the finalized newsletter back to S3
        success = save_finalized_newsletter(bucket_name, date_str, finalized_content)
        
        if not success:
            raise Exception("Failed to save finalized newsletter to S3")
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': f"Newsletter for {date_str} successfully finalized and saved to S3: s3://{bucket_name}/newsletter_{date_str}.md"
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
        # Return proper Bedrock agent response format
        return full_response
        
    except Exception as e:
        # Error response in same format
        error_text = f"Error occurred while finalizing newsletter: {str(e)}"
        
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