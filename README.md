# Bedrock Brief CDK

An automated newsletter generation system built with AWS CDK, Lambda functions, and Amazon Bedrock Agents. The system generates AI-powered newsletters with multiple sections, assembles them into a complete newsletter, and publishes them to Ghost.org with automated scheduling.

## Project Structure

```
.
├── app.py                          # Main CDK app entry point
├── cdk.json                        # CDK configuration
├── requirements.txt                # Python dependencies
├── config.py                       # Configuration settings (Bedrock model, owner email, etc.)
├── generate_newsletter.py          # Script to generate newsletters using the Bedrock agent
├── build_layer.py                  # Script to build Lambda dependency layers
├── lambda_requirements.txt         # Lambda function dependencies
├── stacks/                         # CDK stacks
│   └── bedrock_brief_stack.py      # Main stack with Lambda and Bedrock resources
├── lambda/                         # Lambda functions
│   ├── utils.py                    # Shared utilities (symlinked into all agent functions)
│   ├── generate_introduction/      # Generates newsletter introduction section
│   │   ├── index.py                # Lambda handler
│   ├── generate_fresh_cut/         # Generates fresh content section
│   │   ├── index.py                # Lambda handler
│   ├── generate_the_quarry/        # Generates curated content section
│   │   ├── index.py                # Lambda handler
│   ├── generate_core_sample/       # Generates video content section
│   │   ├── index.py                # Lambda handler
│   ├── assemble_newsletter/        # Combines sections into complete newsletter
│   │   ├── index.py                # Lambda handler
│   ├── current_time/               # Provides current time for scheduling
│   │   └── index.py                # Lambda handler
│   ├── publish_ghost_post/         # Publishes newsletter to Ghost.org
│   │   └── index.py                # Lambda handler
│   └── make_scheduled_issue/       # Scheduled newsletter generator (runs every Tuesday 10 PM ET)
│       └── index.py                # Lambda handler
├── bedrock/                        # Bedrock agent configurations
│   └── agent_config.py             # Agent configuration and action groups
└── templates/                      # Jinja2 templates for newsletter sections
    ├── introduction.md             # Introduction section template
    ├── fresh_cut.md                # Fresh content section template
    ├── the_quarry.md               # Curated content section template
    ├── core_sample.md              # Video content section template
    └── newsletter.md               # Complete newsletter assembly template
```

## Prerequisites

- **AWS CLI**: Configured with appropriate credentials and permissions
- **Python 3.9+**: Required for CDK and Lambda functions
- **Node.js 18+**: Required for AWS CDK
- **AWS CDK**: Installed globally (`npm install -g aws-cdk`)
- **Bedrock Model Access**: The specified Bedrock model must be enabled in your AWS account

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd bedrock-brief-cdk
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set required local environment variables:**
   ```bash
   export YOUTUBE_API_KEY="your_youtube_api_key"
   export SEARCH_API_KEY="your_search_api_key"
   export GHOST_URL="your_ghost_site_url"
   export GHOST_ADMIN_API_KEY="your_ghost_admin_api_key"
   ```

5. **Bootstrap CDK (first time only):**
   ```bash
   cdk bootstrap
   ```

## Bedrock Model Access

**Important**: The Bedrock model specified in `config.py` (currently `anthropic.claude-3-sonnet-20240229-v1:0`) must be enabled in your AWS account and region before deployment.

### To enable the model:
1. Go to the AWS Bedrock console in your target region
2. Navigate to "Model access" in the left sidebar
3. Find the model and click "Request model access"
4. Wait for approval (usually instant for public models)
5. Ensure the model shows as "Access granted"

### Alternative models:
You can change the model in `config.py` to any other available Bedrock model, but ensure it's enabled in your account first.

## Deployment

### 1. Build Lambda Layers
First, build the Lambda dependency layers:
```bash
python build_layer.py
```

### 2. Deploy the Stack
```bash
cdk deploy
```

### 3. Verify Deployment
Check the AWS console to ensure all resources are created:
- Lambda functions
- S3 bucket
- Bedrock agent
- IAM roles and policies

## Usage

### Generate a Test Newsletter Issue
```bash
python generate_newsletter.py
```

This will:
1. Prepare the Bedrock agent
2. Generate all newsletter sections
3. Assemble them into a complete newsletter
4. Store everything in S3
5. Publish to Ghost.org with scheduling

### Scheduled Newsletter Generation
The system automatically generates newsletters every Tuesday at 10 PM ET using the `make_scheduled_issue` Lambda function.

### Manual Newsletter Generation
You can manually trigger newsletter generation through the Bedrock agent or by invoking Lambda functions directly.

## Features

- **AI-Powered Content Generation**: Uses Amazon Bedrock to generate newsletter sections
- **Modular Newsletter Sections**: Introduction, fresh content, curated content, and video content
- **Automated Assembly**: Combines individual sections into a complete newsletter
- **Content Finalization**: Uses Bedrock to polish and finalize newsletter content
- **S3 Content Storage**: Stores generated content in S3 with date-based naming
- **Ghost.org Integration**: Publishes newsletters with automated scheduling
- **Smart Scheduling**: Automatically schedules posts for the next Wednesday at 8 AM ET
- **Email Newsletter Support**: Configures Ghost to send emails via the default newsletter
- **Bedrock Agent Orchestration**: Coordinates all Lambda functions through a Bedrock agent
- **YouTube Integration**: Fetches and analyzes AWS YouTube content for video sections
- **News Aggregation**: Collects and summarizes AI-related news and announcements

## How It Works

### 1. Content Generation
Each Lambda function generates a specific newsletter section:
- **Introduction**: Sets the tone, previews upcoming content, and generates feature images
- **Fresh Cut**: Latest AWS announcements and news related to AI services
- **The Quarry**: Curated blog posts and analysis from AWS ML blog
- **Core Sample**: Featured videos from AWS YouTube channels with AI content

### 2. Content Assembly
The `assemble_newsletter` function combines all sections into a single newsletter file stored in S3.


### 3. Publication
The `publish_ghost_post` function:
- Reads the finalized newsletter from S3
- Creates a draft post in Ghost.org
- Schedules it for the next Wednesday at 8 AM ET
- Configures email newsletter delivery

## Architecture

- **AWS CDK**: Infrastructure as code for AWS resources
- **Lambda Functions**: Serverless compute for content generation and processing
- **Amazon S3**: Content storage with date-based file naming
- **Amazon Bedrock**: AI service for content generation and orchestration
- **Bedrock Agent**: Coordinates Lambda function execution through action groups
- **Ghost.org API**: External publishing platform integration
- **YouTube Data API**: Fetches video content from AWS channels
- **RSS Feeds**: Collects AWS announcements and news

## Configuration

### CDK Configuration
- `config.py`: Contains AWS region and stack name configuration
- `cdk.json`: CDK app configuration and context

## Development

### Local Development
1. Ensure your virtual environment is activated
2. Set all required environment variables
3. Use `cdk synth` to validate your CDK code
4. Use `cdk diff` to see changes before deployment

### Testing
- Test individual Lambda functions locally
- Use the `generate_newsletter.py` script for end-to-end testing
- Monitor CloudWatch logs for debugging

## Troubleshooting

### Common Issues
1. **Bedrock Model Not Enabled**: Ensure the specified model is enabled in your AWS account
2. **Missing Environment Variables**: Check that all required environment variables are set
3. **IAM Permissions**: Ensure your AWS credentials have sufficient permissions for all services
4. **API Rate Limits**: Be aware of YouTube API and Search API rate limits

### Debugging
- Check CloudWatch logs for Lambda function execution
- Monitor Bedrock agent execution logs
- Verify S3 bucket contents and permissions
- Check Ghost.org API responses for publishing issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for error details
3. Open an issue in the repository
4. Check AWS service status pages 