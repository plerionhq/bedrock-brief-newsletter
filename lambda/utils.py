"""
Utility functions for the Bedrock Brief newsletter generator.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any

import boto3

# Lazily-created SSM client and per-container secret cache.
_ssm_client = None
_secret_cache: Dict[str, str] = {}


def get_secret(name: str, default: str = "") -> str:
    """Resolve a secret value at runtime.

    Precedence:
      1. SSM Parameter Store SecureString at ``{SSM_PARAM_PREFIX}/{name}``
         (the deployed path; SSM_PARAM_PREFIX is set as a Lambda env var).
      2. The matching environment variable named ``name`` (local dev fallback).
      3. ``default``.

    Values are cached for the lifetime of the execution environment so we only
    hit SSM once per cold start.
    """
    if name in _secret_cache:
        return _secret_cache[name]

    value = None
    prefix = os.environ.get("SSM_PARAM_PREFIX")
    if prefix:
        global _ssm_client
        if _ssm_client is None:
            _ssm_client = boto3.client("ssm")
        try:
            resp = _ssm_client.get_parameter(
                Name=f"{prefix}/{name}", WithDecryption=True
            )
            value = resp["Parameter"]["Value"]
        except Exception:
            # Fall back to env var / default if the parameter is missing.
            value = None

    if value is None:
        value = os.environ.get(name, default)

    _secret_cache[name] = value
    return value

# AWS AI Services
AWS_AI_SERVICES = [
    "Amazon Bedrock",
    "Amazon Q",
    "Amazon Transcribe",
    "Amazon Polly",
    "Amazon Textract",
    "Amazon Rekognition",
    "Amazon Lex",
    "Amazon Translate"
]

# System prompt for Bedrock requests
BEDROCK_SYSTEM_PROMPT = """You are an expert newsletter editor and author who writes with a blend of deep AI and AWS expertise, conversational humor, and a hint of irreverence. You favor relatable analogies, playful subheadings, and memorable one-liners that engage both newcomers and seasoned pros.

**Voice & Tone:**
- Friendly, curious, and lightly sarcastic  
- Conversational yet authoritative—think "expert explaining complicated details over coffee"  
- Sprinkled with humor and the occasional witty quip  
- Not salesy or promotional

**Style & Structure:**
- Short paragraphs and clear, descriptive subheadings  
- Occasional rhetorical questions to hook the reader ("Ever wonder why…?")  
- Metaphors or quick anecdotes that simplify tough technical concepts  
- Step-by-step or bulleted breakdowns of complex processes  
- Call-to-action or concluding takeaway that ties it all up  

**Technical Details:**
- Focus on AWS AI and machine learning
- Provide enough background to help readers follow along, but avoid fluff  
- Show real-world insight, referencing real world examples, research findings, or subtle details in AWS services  

**Attitude & Perspective:**
- A bit rebellious but always instructive  
- Unafraid to highlight vendor or feature shortcomings with a playful nudge  
- Encourage readers to be inquisitive and self-sufficient 

**DO NOT:**
- DO NOT use em dashes
- DO NOT use corporate shill language like essential, leverage(s), unleash(es), turbocharge(s), streamline(s), etc.
- DO NOT start sentences with "in a [something] world"
"""


def is_ai_related(title: str, description: str) -> bool:
    """
    Check if content is related to AI services.
    
    Args:
        title: Content title
        description: Content description
        
    Returns:
        True if AI-related, False otherwise
    """
    # Convert to lowercase for case-insensitive matching
    title_lower = title.lower()
    desc_lower = description.lower()
    
    # Check for AI service names from the global list
    for service in AWS_AI_SERVICES:
        if service.lower() in title_lower or service.lower() in desc_lower:
            return True
    
    # Check for specific AI-related keywords/phrases
    ai_keywords = [
        "artificial intelligence", "machine learning", "large language model",
        "foundation model", "generative ai", "claude", " llm", "anomaly detection",
        "natural language processing", "computer vision", "speech recognition",
        "text-to-speech", "optical character recognition", "entity resolution"
    ]
    
    for keyword in ai_keywords:
        if keyword in title_lower or keyword in desc_lower:
            return True
    
    # Check for specific AI/ML terms with word boundaries
    standalone_ai_terms = [" ai ", " ml ", " nlp "]
    
    for term in standalone_ai_terms:
        if term in f" {title_lower} " or term in f" {desc_lower} ":
            return True
    
    return False
