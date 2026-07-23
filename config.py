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
# NOTE: Modern Claude models on Bedrock are INFERENCE_PROFILE-only; they cannot be
# invoked by bare "anthropic.*" model IDs. Use a cross-region inference profile ID.
# The previous model (anthropic.claude-3-5-sonnet-20240620-v1:0) was retired by AWS
# and now returns 404 resourceNotFoundException on InvokeAgent.
BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
# Underlying foundation model behind the inference profile (used for IAM scoping).
BEDROCK_FOUNDATION_MODEL_ID = "anthropic.claude-sonnet-4-5-20250929-v1:0"
BEDROCK_AGENT_ID = "O7URHZNJJK"

# Newsletter Configuration
DAYS = 7 