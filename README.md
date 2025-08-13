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
├── build_layer.sh                  # Script to build Lambda dependency layers
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
│   ├── publish_ghost_post/         # Publishes newsletter to Ghost.org
│   │   ├── index.py                # Lambda handler
│   └── make_scheduled_issue/       # Scheduled newsletter generator (runs every Tuesday 10 PM ET)
│       ├── index.py                # Lambda handler
├── bedrock/                        # Bedrock agent configurations
│   └── agent_config.py             # Agent configuration and action groups
└── templates/                      # Jinja2 templates for newsletter sections (symlinked into all agent functions)
    ├── introduction.md             # Introduction section template
    ├── fresh_cut.md                # Fresh content section template
    ├── the_quarry.md               # Curated content section template
    └── core_sample.md              # Video content section template
```

## Setup

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set required environment variables:**
   ```bash
   export YOUTUBE_API_KEY="your_youtube_api_key"
   export SEARCH_API_KEY="your_search_api_key"
   export GHOST_URL="your_ghost_site_url"
   export GHOST_ADMIN_API_KEY="your_ghost_admin_api_key"
   ```

4. **Bootstrap CDK (first time only):**
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

## Usage

### Deploy the stack:
```bash
cdk deploy
```

### Destroy the stack:
```bash
cdk destroy
```

### View stack differences:
```bash
cdk diff
```

## Features

- **AI-Powered Content Generation**: Uses Amazon Bedrock to generate newsletter sections
- **Modular Newsletter Sections**: Introduction, fresh content, curated content, and video content
- **Automated Assembly**: Combines individual sections into a complete newsletter
- **S3 Content Storage**: Stores generated content in S3 with date-based naming
- **Ghost.org Integration**: Publishes newsletters with automated scheduling
- **Smart Scheduling**: Automatically schedules posts for the next Wednesday at 8 AM ET
- **Email Newsletter Support**: Configures Ghost to send emails via the default newsletter
- **Bedrock Agent Orchestration**: Coordinates all Lambda functions through a Bedrock agent

## How It Works

### 1. Content Generation
Each Lambda function generates a specific newsletter section:
- **Introduction**: Sets the tone and previews upcoming content
- **Fresh Cut**: Latest news and fresh content
- **The Quarry**: Curated content and analysis
- **Core Sample**: Featured videos and multimedia content

### 2. Content Assembly
The `assemble_newsletter` function combines all sections into a single newsletter file stored in S3.

### 3. Publication
The `publish_ghost_post` function:
- Reads the assembled newsletter from S3
- Creates a draft post in Ghost.org
- Schedules it for the next Wednesday at 8 AM ET
- Configures email newsletter delivery

## Usage

### Generate a test newsletter issue
```bash
python generate_newsletter.py
```

This will:
1. Prepare the Bedrock agent
2. Generate all newsletter sections
3. Assemble them into a complete newsletter
4. Store everything in S3
5. Publish to Ghost.org with scheduling

### Deploy the Infrastructure
```bash
# Build Lambda layers first
./build_layer.sh

# Deploy the stack
cdk deploy
```

### Destroy the Infrastructure
```bash
cdk destroy
```

## Development

- The virtual environment is already activated (you should see `(venv)` in your prompt)
- All dependencies are installed
- Ready to start developing!

## Architecture

- **AWS CDK**: Infrastructure as code for AWS resources
- **Lambda Functions**: Serverless compute for content generation and processing
- **Amazon S3**: Content storage with date-based file naming
- **Amazon Bedrock**: AI service for content generation and orchestration
- **Bedrock Agent**: Coordinates Lambda function execution
- **Ghost.org API**: External publishing platform integration 