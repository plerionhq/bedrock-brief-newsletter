"""
Configuration settings for the Bedrock Brief CDK project
"""

# AWS Region
AWS_REGION = "us-east-1"

# Resource Tags
OWNER_EMAIL = "daniel.grzelak@plerion.com"
SERVICE_OWNER_EMAIL = "daniel.grzelak@plerion.com"
STAGE = "prod"

# Stack Configuration
STACK_NAME = "BedrockBriefStack"

# Bedrock Configuration
# BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
BEDROCK_AGENT_ID = "O7URHZNJJK"

# Newsletter Configuration
DAYS = 7 