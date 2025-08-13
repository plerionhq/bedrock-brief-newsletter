# Bedrock Agent Configuration

This directory contains the configuration for the BedrockBriefAgent, a Bedrock agent that can provide current time information.

## Files

- `agent_config.py` - Contains the Bedrock agent configuration and creation logic
- `__init__.py` - Python package initialization

## Agent Configuration

The `BedrockBriefAgent` is configured with:

- **Foundation Model**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Action Group**: `CurrentTimeActionGroup` - Executes the current time Lambda function
- **Session TTL**: 1 hour (3600 seconds)
- **Orchestration Type**: `AGENT_BASED`

## Integration

The agent is integrated into the main CDK stack (`stacks/bedrock_brief_stack.py`) and includes:

1. IAM role for the agent with necessary permissions
2. Lambda function integration for the current time functionality
3. Proper resource permissions and outputs

## Usage

After deployment, the agent will be available in the AWS Bedrock console and can be invoked via the Bedrock API. The agent can:

- Respond to user queries about the current time
- Use the integrated Lambda function to get accurate UTC time
- Provide time information in a user-friendly format

## Outputs

The CDK stack provides the following outputs:

- `BedrockAgentArn` - The ARN of the Bedrock agent
- `BedrockAgentId` - The ID of the Bedrock agent
- `CurrentTimeLambdaArn` - The ARN of the Lambda function used by the agent 