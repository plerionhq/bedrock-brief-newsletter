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

# Feature-image model. The former Titan image generator (amazon.titan-image-
# generator-v2:0) reached end-of-life, and Nova Canvas is legacy/blocked. The
# Stability text-to-image models are only available in us-west-2, so the
# introduction Lambda invokes Bedrock cross-region for image generation.
IMAGE_MODEL_ID = "stability.stable-image-core-v1:1"
IMAGE_MODEL_REGION = "us-west-2"

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

# SSM Parameter Store prefix for runtime secrets (SecureString params).
# Secrets (search/YouTube API keys, Ghost URL + admin key) are stored here as
# SecureString parameters and read by the Lambdas at runtime, rather than being
# baked into Lambda environment variables at synth time.
SSM_PARAM_PREFIX = "/bedrock-brief" 