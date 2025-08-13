# Bedrock Brief CDK

A bare minimum Python CDK boilerplate with support for Lambda functions and Bedrock agents.

## Project Structure

```
.
├── app.py                          # Main CDK app entry point
├── cdk.json                        # CDK configuration
├── requirements.txt                 # Python dependencies
├── stacks/                         # CDK stacks
│   ├── __init__.py
│   └── bedrock_brief_stack.py      # Main stack with Lambda and Bedrock resources
├── lambda/                         # Lambda functions
│   ├── __init__.py
│   └── example/                    # Example Lambda function
│       ├── __init__.py
│       ├── index.py                # Lambda handler
│       └── requirements.txt        # Lambda dependencies
└── bedrock/                        # Bedrock agent configurations
    ├── __init__.py
    └── agent_config.py             # Agent configuration classes
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

3. **Bootstrap CDK (first time only):**
   ```bash
   cdk bootstrap
   ```

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

- **Lambda Functions**: Ready-to-use Lambda functions with Bedrock integration
- **Bedrock Agents**: Configuration structure for Bedrock agents
- **IAM Roles**: Proper IAM roles with Bedrock permissions
- **Modular Structure**: Easy to extend with additional functions and agents

## Adding Lambda Functions

1. Create a new directory in `lambda/`
2. Add your handler code and requirements.txt
3. Update the stack in `stacks/bedrock_brief_stack.py`

## Adding Bedrock Agents

1. Configure agent settings in `bedrock/agent_config.py`
2. Update the stack to create agent resources
3. Deploy with `cdk deploy`

## Development

- The virtual environment is already activated (you should see `(venv)` in your prompt)
- All dependencies are installed
- Ready to start developing! 