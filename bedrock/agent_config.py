"""
Bedrock Agent Configuration for BedrockBriefAgent
"""

import os
from aws_cdk import aws_bedrock as bedrock
from config import BEDROCK_MODEL_ID


def create_bedrock_agent_config(self, current_time_lambda_arn: str, generate_introduction_arn: str, 
                               generate_fresh_cut_arn: str, generate_the_quarry_arn: str, 
                               generate_core_sample_arn: str, assemble_newsletter_arn: str, 
                               publish_ghost_post_arn: str) -> bedrock.CfnAgent:
    """
    Create the BedrockBriefAgent configuration
    
    Args:
        self: The CDK construct scope
        current_time_lambda_arn: ARN of the current time Lambda function
        generate_introduction_arn: ARN of the generate introduction Lambda function
        generate_fresh_cut_arn: ARN of the generate fresh cut Lambda function
        generate_the_quarry_arn: ARN of the generate the quarry Lambda function
        generate_core_sample_arn: ARN of the generate core sample Lambda function
                assemble_newsletter_arn: ARN of the assemble newsletter Lambda function

        publish_ghost_post_arn: ARN of the publish Ghost post Lambda function
    
    Returns:
        CfnAgent: The configured Bedrock agent
    """
    
    # Create action group for the current time function
    current_time_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="CurrentTimeActionGroup",
        description="Action group for getting current time",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=current_time_lambda_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="getCurrentTime",
                    description="Get the current UTC date and time",
                    parameters={}
                )
            ]
        )
    )
    
    # Create action group for generate introduction function
    generate_introduction_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="GenerateIntroductionActionGroup",
        description="Action group for generating newsletter introduction",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=generate_introduction_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="generateIntroduction",
                    description="Generate the introduction section of the newsletter",
                    parameters={
                        "cutoff_date": {
                            "type": "string",
                            "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                            "required": True
                        }
                    }
                )
            ]
        )
    )
    
    # Create action group for generate fresh cut function
    generate_fresh_cut_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="GenerateFreshCutActionGroup",
        description="Action group for generating fresh cut section",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=generate_fresh_cut_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="generateFreshCut",
                    description="Generate the fresh cut section of the newsletter",
                    parameters={
                        "cutoff_date": {
                            "type": "string",
                            "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                            "required": True
                        }
                    }
                )
            ]
        )
    )
    
    # Create action group for generate the quarry function
    generate_the_quarry_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="GenerateTheQuarryActionGroup",
        description="Action group for generating the quarry section",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=generate_the_quarry_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="generateTheQuarry",
                    description="Generate the quarry section of the newsletter",
                    parameters={
                        "cutoff_date": {
                            "type": "string",
                            "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                            "required": True
                        }
                    }
                )
            ]
        )
    )
    
    # Create action group for generate core sample function
    generate_core_sample_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="GenerateCoreSampleActionGroup",
        description="Action group for generating core sample section",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=generate_core_sample_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="generateCoreSample",
                    description="Generate the core sample section of the newsletter",
                    parameters={
                        "cutoff_date": {
                            "type": "string",
                            "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                            "required": True
                        }
                    }
                )
            ]
        )
    )
    
    # Create action group for assemble newsletter function
    assemble_newsletter_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="AssembleNewsletterActionGroup",
        description="Action group for assembling the complete newsletter from sections",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=assemble_newsletter_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
            functions=[
                bedrock.CfnAgent.FunctionProperty(
                    name="assembleNewsletter",
                    description="Assemble the complete newsletter from individual sections",
                    parameters={
                        "cutoff_date": {
                            "type": "string",
                            "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                            "required": True
                        }
                    }
                )
            ]
        )
    )
    

    
    # Create action group for publish Ghost post function
    publish_ghost_post_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
        action_group_name="PublishGhostPostActionGroup",
        description="Action group for publishing posts to Ghost.org",
        action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
            lambda_=publish_ghost_post_arn
        ),
        action_group_state="ENABLED",
        function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                                functions=[
                        bedrock.CfnAgent.FunctionProperty(
                            name="publishGhostPost",
                            description="Publish a post to Ghost.org by reading content from S3",
                            parameters={
                                "title": {
                                    "type": "string",
                                    "description": "The title of the post to publish",
                                    "required": True
                                },
                                "cutoff_date": {
                                    "type": "string",
                                    "description": "The cutoff date for the newsletter in YYYY-MM-DD HH:MM:SS format",
                                    "required": True
                                }
                            }
                        )
                    ]
        )
    )
    
    # Read the newsletter template at runtime
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "newsletter.md")
    with open(template_path, 'r') as f:
        newsletter_template = f.read()
    
    # Create the agent
    agent = bedrock.CfnAgent(
        self, "BedrockBriefAgent",
        agent_name="BedrockBriefAgent",
        description="A Bedrock agent for the Bedrock Brief project",
        instruction=f"""You are an expert author and editor of the Bedrock Brief newsletter, dedicated to 
builders of artificial intelligence services on top of AWS.

- Generate all the newsletter sections
- Assemble the newsletter from the sections
- Publish the newsletter to Ghost.org, with the title "Bedrock Brief [pubication date as %d %b %Y]"
""",
        foundation_model=BEDROCK_MODEL_ID,
        action_groups=[
            current_time_action_group,
            generate_introduction_action_group,
            generate_fresh_cut_action_group,
            generate_the_quarry_action_group,
            generate_core_sample_action_group,
            assemble_newsletter_action_group,
            publish_ghost_post_action_group
        ],
        agent_resource_role_arn="",  # Will be set by CDK
        idle_session_ttl_in_seconds=3600,  # 1 hour
        orchestration_type="DEFAULT"
    )
    
    return agent 