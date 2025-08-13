#!/usr/bin/env python3
"""
Main CDK app entry point
"""

import aws_cdk as cdk
from stacks.bedrock_brief_stack import BedrockBriefStack
from config import AWS_REGION, STACK_NAME

app = cdk.App()

BedrockBriefStack(app, STACK_NAME, env=cdk.Environment(
    region=AWS_REGION
))

app.synth() 