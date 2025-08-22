"""
Lambda function to generate the core sample section of the Bedrock Brief newsletter
"""

import json
import boto3
import os
import requests
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from youtube_transcript_api import YouTubeTranscriptApi
import re

from utils import BEDROCK_SYSTEM_PROMPT, is_ai_related

# Get Bedrock model ID from environment variable
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Get API keys from environment variables
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def fetch_channel_videos(channel_id: str, api_key: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch recent videos from a YouTube channel using the YouTube Data API.
    
    Args:
        channel_id: YouTube channel ID
        api_key: YouTube Data API key
        max_results: Maximum number of videos to fetch
        
    Returns:
        List of video dictionaries
    """
    try:
        # Get channel info to find uploads playlist
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        channel_params = {
            'key': api_key,
            'part': 'contentDetails',
            'id': channel_id
        }
        
        response = requests.get(channel_url, params=channel_params)
        response.raise_for_status()
        channel_data = response.json()
        
        if not channel_data.get('items'):
            print(f"No channel data found for channel ID: {channel_id}")
            return []
        
        uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos from uploads playlist
        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        playlist_params = {
            'key': api_key,
            'part': 'snippet',
            'playlistId': uploads_playlist_id,
            'maxResults': max_results
        }
        
        response = requests.get(playlist_url, params=playlist_params)
        response.raise_for_status()
        playlist_data = response.json()
        
        # Extract video IDs from playlist
        video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_data.get('items', [])]
        
        if not video_ids:
            return []
        
        # Get detailed video information
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            'key': api_key,
            'part': 'snippet,contentDetails,statistics',
            'id': ','.join(video_ids)
        }
        
        response = requests.get(videos_url, params=videos_params)
        response.raise_for_status()
        
        videos_data = response.json()
        videos = []
        
        for item in videos_data.get('items', []):
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            
            # Parse published date
            published_date = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
            
            video = {
                'id': item['id'],
                'title': snippet['title'].replace(' | Amazon Web Services', ''),
                'description': snippet['description'],
                'url': f"https://www.youtube.com/watch?v={item['id']}",
                'published_date': published_date,
                'channel_title': snippet['channelTitle'],
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'duration': item['contentDetails']['duration'],
                'thumbnail': snippet['thumbnails']['high']['url']
            }
            videos.append(video)
        
        return videos
        
    except Exception as e:
        print(f"Error fetching videos for channel {channel_id}: {e}")
        return []


def fetch_transcript(video_id: str) -> str:
    """
    Fetch transcript for a given YouTube video ID.
    
    Args:
        video_id: The YouTube video ID
        
    Returns:
        Transcript text or empty string if error
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        
        # Combine all transcript segments into one text
        full_text = ' '.join([snippet.text for snippet in transcript])
        return full_text
        
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return ""


def analyze_videos_with_bedrock(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use Bedrock to analyze videos and select the best one.
    
    Args:
        videos: List of video dictionaries
        
    Returns:
        Dictionary with the best video information
    """
    if not videos:
        return {}
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Format videos for analysis
        formatted_videos = []
        for i, video in enumerate(videos, 1):
            formatted_video = f"""
Number {i}:
Title: {video['title']}
Views: {video['view_count']}
Likes: {video['like_count']}
Description: {video['description']}...
===============================================
"""
            formatted_videos.append(formatted_video)
        
        formatted_videos_str = "\n".join(formatted_videos)
        
        # Create the analysis prompt
        analysis_prompt = f"""
You are an expert content analyst specializing in AWS Machine Learning and AI technologies. 
You have been given a list of recent videos from AWS YouTube channels.

Please analyze the following {len(videos)} videos and determine which one is the BEST overall.
Consider the following criteria:
1. Technical depth and educational value
2. Innovation and cutting-edge content
3. Quality of content and presentation
4. Exclusion of sales pitches
5. Uniqueness and originality of the content
6. Applicability to largest audience
7. Number of views and likes

Here are the videos to analyze:

{formatted_videos_str}

Please provide your analysis in the following JSON format:
{{
    "best_video_number": <integer>
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
            best_video_number = result.get('best_video_number', -1)
            best_video = videos[best_video_number - 1]

            return best_video
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Bedrock analysis response: {e}")
            return {}
            
    except Exception as e:
        print(f"Error analyzing videos with Bedrock: {e}")
        return {}


def generate_video_summary(best_video: Dict[str, Any]) -> str:
    """
    Generate an engaging summary of the best video using Bedrock.
    
    Args:
        best_video: Dictionary containing the best video information
        
    Returns:
        Engaging summary string
    """
    if not best_video:
        return "No featured video available."
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Fetch transcript for the video
        video_id = best_video['id']
        transcript = fetch_transcript(video_id)
        
        # Create the summary prompt
        summary_prompt = f"""{BEDROCK_SYSTEM_PROMPT}

Based on the following AWS video, write a 3 sentence, 1 paragraph summary that captures the essence and value of the video. Include at least one technical detail that an engineer would find interesting.
RETURN ONLY THE SUMMARY, NO OTHER TEXT.
Do not include any intro, explanation, or preamble.

Title: {best_video['title']}
Description: {best_video['description']}
Transcript: {transcript}
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
        print(f"Error generating video summary with Bedrock: {e}")
        return f"{best_video.get('title', 'Featured Video')} - Check out this informative AWS video for technical insights and best practices."


def fetch_youtube_videos(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch YouTube videos from AWS channels.
    
    Args:
        cutoff_date: Only fetch videos after this date
        
    Returns:
        List of video dictionaries
    """
    api_key = YOUTUBE_API_KEY
    if not api_key:
        print("Warning: YOUTUBE_API_KEY environment variable not set")
        return []
    
    all_videos = []
    
    # Channel IDs for the AWS channels
    channel_ids = [
        "UCd6MoB9NC6uYN2grvUNT-Zg",  # @amazonwebservices
        "UCu1x04CVbnXgW5FmVPUKGuA",  # @AWSEventsChannel
        "UC-oTsx0SVTqlXVu0IecntUQ"   # @awsdevelopers
    ]
    
    channel_names = ["@amazonwebservices", "@AWSEventsChannel", "@awsdevelopers"]
    
    for i, channel_id in enumerate(channel_ids):
        videos = fetch_channel_videos(channel_id, api_key, max_results=20)
        
        # Filter by cutoff date if provided
        if cutoff_date:
            videos = [v for v in videos if v['published_date'] >= cutoff_date]
        
        # Filter for AI-related videos only
        ai_videos = [v for v in videos if is_ai_related(v['title'], v['description'])]
        
        all_videos.extend(ai_videos)
    
    # Sort by published date (newest first)
    all_videos.sort(key=lambda x: x['published_date'], reverse=True)
    
    return all_videos


def get_featured_video(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the most relevant video as the featured video using Bedrock analysis.
    
    Args:
        videos: List of videos
        
    Returns:
        Featured video dictionary with summary
    """
    if not videos:
        return {}
    
    # Use Bedrock to analyze and select the best video
    best_video = analyze_videos_with_bedrock(videos)
    
    if not best_video:
        # Fallback to first video if analysis fails
        if videos:
            first_video = videos[0]
            best_video = first_video
    
    # Generate engaging summary for the best video
    summary = generate_video_summary(best_video)
    best_video['summary'] = summary
    
    return best_video


def get_other_videos(videos: List[Dict[str, Any]], featured_video: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get other videos excluding the featured one.
    
    Args:
        videos: List of all videos
        featured_video: The featured video
        
    Returns:
        List of other videos
    """
    if not featured_video:
        return videos
    
    # Filter out the featured video
    other_videos = []
    for video in videos:
        if video['url'] == featured_video.get('url'):
            continue
        
        other_videos.append({
            'title': video['title'],
            'url': video['url'],
            'published_date': video['published_date'].strftime('%Y-%m-%d'),
            'channel_title': video['channel_title'],
            'view_count': video['view_count']
        })
    
    return other_videos[:5]  # Limit to 5 other videos


def get_core_sample_content(cutoff_date: datetime) -> Dict[str, Any]:
    """
    Get all Core Sample content (videos and tutorials).
    
    Args:
        cutoff_date: Cutoff date for filtering content
        
    Returns:
        Dictionary with featured_video and other_videos
    """
    # Fetch YouTube videos
    youtube_videos = fetch_youtube_videos(cutoff_date)
    
    if not youtube_videos:
        return {
            "featured_video": {},
            "other_videos": []
        }
    
    # Select featured video
    featured_video = get_featured_video(youtube_videos)
    
    # Get other videos
    other_videos = get_other_videos(youtube_videos, featured_video)
    
    return {
        "featured_video": featured_video,
        "other_videos": other_videos
    }


def generate_core_sample(cutoff_date: datetime) -> str:
    """
    Generate the core sample section content.
    
    Args:
        cutoff_date: The cutoff date for the newsletter as a datetime object with UTC timezone
        
    Returns:
        Generated core sample section text
        
    Raises:
        Exception: If content generation fails
    """
    # Validate cutoff_date is a datetime object with UTC timezone
    if not isinstance(cutoff_date, datetime):
        raise ValueError("cutoff_date must be a datetime object")
    
    # Get the content
    video_content = get_core_sample_content(cutoff_date)
    
    # Load and render the template
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("core_sample.md")
    
    return template.render(
        featured_video=video_content.get("featured_video"),
        other_videos=video_content.get("other_videos", [])
    )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate core sample section for the Bedrock Brief newsletter
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
        
        # Generate the core sample content
        response_text = generate_core_sample(cutoff_date)
        # response_text = "test"
        
        # Save content to S3 instead of returning it
        bucket_name = os.environ.get("CONTENT_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("CONTENT_BUCKET_NAME environment variable is required")
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate filename based on template name and date
        date_str = cutoff_date.strftime("%Y-%m-%d")
        filename = f"core_sample_{date_str}.md"
        
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
                'body': f"Core sample content successfully saved to S3: s3://{bucket_name}/{filename}"
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
        error_text = f"Error occurred while generating core sample: {str(e)}"
        
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