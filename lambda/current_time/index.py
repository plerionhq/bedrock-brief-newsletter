"""
Example Lambda function with Bedrock integration
"""

import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Get Bedrock model ID from environment variable
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Get DAYS from environment variable
DAYS = int(os.environ.get("DAYS", "7"))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda handler that returns current UTC date and time
    """
    try:
        
        # Get current UTC date and time
        current_time = datetime.now(timezone.utc)
        
        # Calculate cutoff date
        cutoff_date = current_time - timedelta(days=DAYS)
        
        # Format dates using strftime
        current_time_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S")
        cutoff_date_formatted = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the response text
        response_text = f"Current UTC date and time: {current_time_formatted}\nNewsletter cutoff UTC date and time: {cutoff_date_formatted}"
        
        # Format response body for Bedrock agent
        response_body = {
            'TEXT': {
                'body': response_text
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
        error_text = f"Error occurred while getting current time: {str(e)}"
        
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


 