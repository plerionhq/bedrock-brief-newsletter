#!/usr/bin/env python3

import boto3

# Create a Bedrock client
client = boto3.client('bedrock', region_name='us-east-1')

# List foundation models, filtering by 'ON_DEMAND' inference type
response = client.list_foundation_models(
    byInferenceType="ON_DEMAND"
)

# Extract the model summaries
models = response['modelSummaries']

# Print the IDs of models that support on-demand inference
print(f'Found {len(models)} available models supporting on-demand inference:')
for model in models:
    print(f'- {model["modelId"]}')