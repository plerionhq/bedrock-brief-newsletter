"""
Main CDK stack for Bedrock Brief project
"""

import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
)
from constructs import Construct
from config import OWNER_EMAIL, SERVICE_OWNER_EMAIL, STAGE, BEDROCK_MODEL_ID, BEDROCK_FOUNDATION_MODEL_ID, BEDROCK_AGENT_ID, DAYS
from bedrock.agent_config import create_bedrock_agent_config


class BedrockBriefStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add default tags to all resources in this stack
        cdk.Tags.of(self).add("Owner", OWNER_EMAIL)
        cdk.Tags.of(self).add("ServiceOwner", SERVICE_OWNER_EMAIL)
        cdk.Tags.of(self).add("Stage", STAGE)

        # Create IAM role for Lambda functions
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ]
        )

        # Add Bedrock permissions to Lambda role
        bedrock_policy = iam.Policy(
            self, "LambdaBedrockPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    resources=[
                        "*"
                    ]
                )
            ]
        )
        
        # Attach the Bedrock policy to the Lambda role
        bedrock_policy.attach_to_role(lambda_role)

        # Add Bedrock Agent permissions to Lambda role
        bedrock_agent_policy = iam.Policy(
            self, "LambdaBedrockAgentPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:PrepareAgent",
                        "bedrock:GetAgent",
                        "bedrock:InvokeAgent"
                    ],
                    resources=[
                        "*"
                    ]
                )
            ]
        )
        
        # Attach the Bedrock Agent policy to the Lambda role
        bedrock_agent_policy.attach_to_role(lambda_role)

        # Create an S3 bucket
        content_bucket = s3.Bucket(
            self, "NewsletterBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter14Days",
                    expiration=cdk.Duration.days(14)
                )
            ]
        )

        # Add S3 permissions to Lambda role
        s3_policy = iam.Policy(
            self, "LambdaS3Policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    resources=[
                        content_bucket.bucket_arn,
                        f"{content_bucket.bucket_arn}/*"
                    ]
                )
            ]
        )
        
        # Attach the S3 policy to the Lambda role
        s3_policy.attach_to_role(lambda_role)

        # Current time Lambda function
        current_time_lambda = _lambda.Function(
            self, "CurrentTimeFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/current_time"),
            role=lambda_role,
            memory_size=128,  # Minimum memory (128 MB)
            timeout=cdk.Duration.seconds(3),  # Minimum timeout (3 seconds)
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                "DAYS": str(DAYS),
            }
        )

        # Create Lambda layer for dependencies
        dependencies_layer = _lambda.LayerVersion(
            self, "GenerateFunctionsDependenciesLayer",
            code=_lambda.Code.from_asset("lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            description="Dependencies for generate functions (requests, newspaper3k, etc.)"
        )

        # Generate introduction Lambda function
        generate_introduction_lambda = _lambda.Function(
            self, "GenerateIntroductionFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/generate_introduction"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                "SEARCH_API_KEY": os.environ.get("SEARCH_API_KEY", ""),
                "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )

        # Generate fresh cut Lambda function
        generate_fresh_cut_lambda = _lambda.Function(
            self, "GenerateFreshCutFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/generate_fresh_cut"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                "SEARCH_API_KEY": os.environ.get("SEARCH_API_KEY", ""),
                "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )

        # Generate the quarry Lambda function
        generate_the_quarry_lambda = _lambda.Function(
            self, "GenerateTheQuarryFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/generate_the_quarry"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                "SEARCH_API_KEY": os.environ.get("SEARCH_API_KEY", ""),
                "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )

        # Generate core sample Lambda function
        generate_core_sample_lambda = _lambda.Function(
            self, "GenerateCoreSampleFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/generate_core_sample"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
                "SEARCH_API_KEY": os.environ.get("SEARCH_API_KEY", ""),
                "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )

        # Assemble newsletter Lambda function
        assemble_newsletter_lambda = _lambda.Function(
            self, "AssembleNewsletterFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/assemble_newsletter"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )



        # Publish Ghost post Lambda function
        publish_ghost_post_lambda = _lambda.Function(
            self, "PublishGhostPostFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/publish_ghost_post"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "GHOST_URL": os.environ.get("GHOST_URL", ""),
                "GHOST_ADMIN_API_KEY": os.environ.get("GHOST_ADMIN_API_KEY", ""),
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
            }
        )

        # Scheduled newsletter generator Lambda function
        make_scheduled_issue_lambda = _lambda.Function(
            self, "MakeScheduledIssueFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/make_scheduled_issue"),
            role=lambda_role,
            memory_size=512,
            timeout=cdk.Duration.seconds(300),  # 5 minutes for agent preparation
            layers=[dependencies_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "bedrock-brief",
                "BEDROCK_AGENT_ID": BEDROCK_AGENT_ID,
            }
        )

        # Create EventBridge rule to run every Tuesday at 10 PM ET (3 AM UTC next day)
        # Tuesday = 2 (0=Monday, 1=Tuesday, 2=Wednesday, etc.)
        # 10 PM ET = 3 AM UTC (next day)
        scheduled_newsletter_rule = events.Rule(
            self, "ScheduledNewsletterRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="3",  # 3 AM UTC = 10 PM ET (previous day)
                week_day="WED",  # Wednesday UTC = Tuesday ET
                month="*",
                year="*"
            ),
            description="Triggers newsletter generation every Tuesday evening at 10 PM ET"
        )

        # Add the Lambda function as a target for the EventBridge rule
        scheduled_newsletter_rule.add_target(
            targets.LambdaFunction(make_scheduled_issue_lambda)
        )

        # --- Failure alerting --------------------------------------------------
        # SNS topic that emails on scheduled-newsletter failures. The scheduled
        # Lambda raises on failure (see lambda/make_scheduled_issue/index.py) so
        # the Lambda Errors metric increments and the alarm below fires.
        alerts_topic = sns.Topic(
            self, "NewsletterAlertsTopic",
            display_name="Bedrock Brief newsletter alerts",
        )
        alerts_topic.add_subscription(
            subscriptions.EmailSubscription("security.digest@plerion.com")
        )

        # Alarm on any error from the scheduled newsletter Lambda. It runs weekly,
        # so evaluate over a 1-hour window and don't alarm on the (expected) gaps.
        scheduled_failure_alarm = cloudwatch.Alarm(
            self, "ScheduledNewsletterFailureAlarm",
            alarm_name="BedrockBrief-ScheduledNewsletter-Failure",
            alarm_description=(
                "The scheduled Bedrock Brief newsletter run failed "
                "(MakeScheduledIssue Lambda reported an error)."
            ),
            metric=make_scheduled_issue_lambda.metric_errors(
                period=cdk.Duration.hours(1),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        scheduled_failure_alarm.add_alarm_action(cw_actions.SnsAction(alerts_topic))

        # Create IAM role for Bedrock agent
        agent_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        # Create custom policy for Bedrock agent
        bedrock_agent_policy = iam.Policy(
            self, "BedrockAgentPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    resources=[
                        # The cross-region inference profile the agent invokes...
                        f"arn:aws:bedrock:*:{cdk.Stack.of(self).account}:inference-profile/{BEDROCK_MODEL_ID}",
                        # ...and the underlying foundation model in every member region
                        # the profile may route to (us-* profiles span multiple regions).
                        f"arn:aws:bedrock:*::foundation-model/{BEDROCK_FOUNDATION_MODEL_ID}"
                    ]
                )
            ]
        )
        
        # Attach the policy to the role
        bedrock_agent_policy.attach_to_role(agent_role)

        # Grant the agent permission to invoke all Lambda functions
        current_time_lambda.grant_invoke(agent_role)
        generate_introduction_lambda.grant_invoke(agent_role)
        generate_fresh_cut_lambda.grant_invoke(agent_role)
        generate_the_quarry_lambda.grant_invoke(agent_role)
        generate_core_sample_lambda.grant_invoke(agent_role)
        assemble_newsletter_lambda.grant_invoke(agent_role)

        publish_ghost_post_lambda.grant_invoke(agent_role)

        # Create the Bedrock agent
        bedrock_agent = create_bedrock_agent_config(
            self, 
            current_time_lambda.function_arn,
            generate_introduction_lambda.function_arn,
            generate_fresh_cut_lambda.function_arn,
            generate_the_quarry_lambda.function_arn,
            generate_core_sample_lambda.function_arn,
            assemble_newsletter_lambda.function_arn,

            publish_ghost_post_lambda.function_arn
        )

        # Add resource-based policy to allow invocation by Bedrock agents with proper conditions
        current_time_lambda.add_permission(
            "AllowBedrockAgentInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )

        # Add resource-based policies for all newsletter generation functions
        generate_introduction_lambda.add_permission(
            "AllowBedrockAgentInvokeIntroduction",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )

        generate_fresh_cut_lambda.add_permission(
            "AllowBedrockAgentInvokeFreshCut",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )

        generate_the_quarry_lambda.add_permission(
            "AllowBedrockAgentInvokeQuarry",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )

        generate_core_sample_lambda.add_permission(
            "AllowBedrockAgentInvokeCoreSample",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )

        assemble_newsletter_lambda.add_permission(
            "AllowBedrockAgentInvokeAssembleNewsletter",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )



        publish_ghost_post_lambda.add_permission(
            "AllowBedrockAgentInvokeGhostPost",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=cdk.Stack.of(self).account,
            source_arn=bedrock_agent.attr_agent_arn
        )
        
        # Set the agent resource role ARN
        bedrock_agent.agent_resource_role_arn = agent_role.role_arn

        # Output the Lambda function ARNs
        cdk.CfnOutput(
            self, "CurrentTimeLambdaArn",
            value=current_time_lambda.function_arn,
            description="ARN of the current time Lambda function"
        )

        cdk.CfnOutput(
            self, "GenerateIntroductionLambdaArn",
            value=generate_introduction_lambda.function_arn,
            description="ARN of the generate introduction Lambda function"
        )

        cdk.CfnOutput(
            self, "GenerateFreshCutLambdaArn",
            value=generate_fresh_cut_lambda.function_arn,
            description="ARN of the generate fresh cut Lambda function"
        )

        cdk.CfnOutput(
            self, "GenerateTheQuarryLambdaArn",
            value=generate_the_quarry_lambda.function_arn,
            description="ARN of the generate the quarry Lambda function"
        )

        cdk.CfnOutput(
            self, "GenerateCoreSampleLambdaArn",
            value=generate_core_sample_lambda.function_arn,
            description="ARN of the generate core sample Lambda function"
        )

        cdk.CfnOutput(
            self, "AssembleNewsletterLambdaArn",
            value=assemble_newsletter_lambda.function_arn,
            description="ARN of the assemble newsletter Lambda function"
        )

        cdk.CfnOutput(
            self, "PublishGhostPostLambdaArn",
            value=publish_ghost_post_lambda.function_arn,
            description="ARN of the publish Ghost post Lambda function"
        )

        cdk.CfnOutput(
            self, "MakeScheduledIssueLambdaArn",
            value=make_scheduled_issue_lambda.function_arn,
            description="ARN of the scheduled newsletter generator Lambda function"
        )

        # Output the Bedrock agent ARN
        cdk.CfnOutput(
            self, "BedrockAgentArn",
            value=bedrock_agent.attr_agent_arn,
            description="ARN of the Bedrock agent"
        )

        # Output the Bedrock agent ID
        cdk.CfnOutput(
            self, "BedrockAgentId",
            value=bedrock_agent.attr_agent_id,
            description="ID of the Bedrock agent"
        )

        # Output the S3 bucket name
        cdk.CfnOutput(
            self, "ContentBucketName",
            value=content_bucket.bucket_name,
            description="Name of the S3 bucket for content storage"
        )

