"""
Lambda function to assemble the complete newsletter from individual sections
"""

import json
import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional


def read_section_from_s3(bucket_name: str, section_name: str) -> Optional[str]:
    """
    Read a newsletter section from S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        section_name: Name of the section file (e.g., 'introduction_2024-01-15.md')
        
    Returns:
        Section content as string, or None if not found
    """
    try:
        s3_client = boto3.client('s3')
        
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=section_name
        )
        
        content = response['Body'].read().decode('utf-8')
        return content
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"Section not found: {section_name}")
            return None
        else:
            print(f"Error reading section {section_name}: {e}")
            return None
    except Exception as e:
        print(f"Unexpected error reading section {section_name}: {e}")
        return None


def list_section_files(bucket_name: str, date_str: str) -> List[str]:
    """
    List all section files for a specific date.
    
    Args:
        bucket_name: Name of the S3 bucket
        date_str: Date string in format 'YYYY-MM-DD'
        
    Returns:
        List of section filenames
    """
    try:
        s3_client = boto3.client('s3')
        
        # List objects with the date prefix
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=date_str
        )
        
        if 'Contents' not in response:
            return []
        
        # Filter for markdown files and extract just the filenames
        section_files = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.md') and key != f"{date_str}/newsletter.md":
                section_files.append(key)
        
        return sorted(section_files)
        
    except Exception as e:
        print(f"Error listing section files: {e}")
        return []


def assemble_newsletter(bucket_name: str, date_str: str) -> str:
    """
    Assemble the complete newsletter from individual sections.
    
    Args:
        bucket_name: Name of the S3 bucket
        date_str: Date string in format 'YYYY-MM-DD'
        
    Returns:
        Complete newsletter content as string
    """
    # Define the order of sections
    section_order = [
        'introduction',
        'fresh_cut', 
        'the_quarry',
        'core_sample'
    ]
    
    newsletter_parts = []
    
    # Read and add each section in order
    for section in section_order:
        # Look for the section file with the date
        section_filename = f"{section}_{date_str}.md"
        
        content = read_section_from_s3(bucket_name, section_filename)
        if content:
            newsletter_parts.append(content)
    
    # Combine all parts
    complete_newsletter = "\n".join(newsletter_parts)
    
    return complete_newsletter


def save_newsletter_to_s3(bucket_name: str, date_str: str, newsletter_content: str) -> bool:
    """
    Save the assembled newsletter to S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        date_str: Date string in format 'YYYY-MM-DD'
        newsletter_content: Complete newsletter content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client = boto3.client('s3')
        
        # Save as newsletter_{date}.md
        filename = f"newsletter_{date_str}.md"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=newsletter_content,
            ContentType='text/markdown'
        )
        
        return True
        
    except Exception as e:
        print(f"Error saving newsletter to S3: {e}")
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Assemble the complete newsletter from individual sections
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
        
        # Get bucket name from environment
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Format date for filename
        date_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Assemble the newsletter
        newsletter_content = assemble_newsletter(bucket_name, date_str)
        
        # Save the complete newsletter to S3
        success = save_newsletter_to_s3(bucket_name, date_str, newsletter_content)
        
        if not success:
            raise Exception("Failed to save newsletter to S3")
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': f"Newsletter for {date_str} successfully assembled and saved to S3: s3://{bucket_name}/newsletter_{date_str}.md"
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
        error_text = f"Error occurred while assembling newsletter: {str(e)}"
        
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