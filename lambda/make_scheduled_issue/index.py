"""
Lambda function to automatically generate newsletters every Tuesday evening at 10 PM ET
"""

import boto3
import json
import logging
import time
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Agent configuration
AGENT_ID = os.environ.get("BEDROCK_AGENT_ID")
ALIAS_ID = "TSTALIASID"
REGION = "ap-southeast-2"

def prepare_agent(client, agent_id):
    """Prepare the latest version of the agent before running it"""
    
    logger.info("Preparing agent...")
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"Region: {REGION}")
    
    try:
        # Create a DRAFT version of the agent
        response = client.prepare_agent(
            agentId=agent_id
        )
        
        agent_status = response.get('agentStatus')
        agent_version = response.get('agentVersion')
        prepared_at = response.get('preparedAt')
        
        logger.info(f"Agent preparation initiated:")
        logger.info(f"  Status: {agent_status}")
        logger.info(f"  Version: {agent_version}")
        logger.info(f"  Prepared at: {prepared_at}")
        
        # Wait for agent to be prepared
        if agent_status == 'PREPARING':
            logger.info("Waiting for agent to be prepared...")
            max_wait_time = 300  # 5 minutes
            wait_time = 0
            check_interval = 10  # Check every 10 seconds
            
            while wait_time < max_wait_time:
                time.sleep(check_interval)
                wait_time += check_interval
                
                # Check agent status
                agent_response = client.get_agent(agentId=agent_id)
                current_status = agent_response.get('agent', {}).get('agentStatus')
                
                logger.info(f"  Current status: {current_status} (waited {wait_time}s)")
                
                if current_status == 'PREPARED':
                    logger.info("Agent is now prepared and ready to use!")
                    return True
                elif current_status in ['FAILED', 'NOT_PREPARED']:
                    logger.error(f"Agent preparation failed with status: {current_status}")
                    return False
                elif current_status == 'PREPARING':
                    continue
                else:
                    logger.error(f"Unexpected agent status: {current_status}")
                    return False
            
            logger.error("Timeout waiting for agent preparation")
            return False
            
        elif agent_status == 'PREPARED':
            logger.info("Agent is already prepared and ready to use!")
            return True
        else:
            logger.error(f"Agent preparation resulted in unexpected status: {agent_status}")
            return False
            
    except ClientError as e:
        logger.error(f"Client error during agent preparation: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during agent preparation: {e}")
        return False

def invoke_agent(client, agent_id, alias_id, prompt, session_id):
    """Invoke the Bedrock agent and handle streaming response"""
    
    logger.info("Generating newsletter...")
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"Alias ID: {alias_id}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Region: {REGION}")
    
    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            enableTrace=True,
            sessionId=session_id,
            inputText=prompt,
            streamingConfigurations={
                "applyGuardrailInterval": 20,
                "streamFinalResponse": False
            }
        )
        
        completion = ""
        logger.info("Newsletter generation started...")
        
        for event in response.get("completion"):
            # Collect agent output
            if 'chunk' in event:
                chunk = event["chunk"]
                text_chunk = chunk["bytes"].decode()
                completion += text_chunk
            
            # Log trace output
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event['trace']
                for key, value in trace.items():
                    logger.info("%s: %s", key, value)
        
        logger.info(f"Newsletter generation completed. Total length: {len(completion)} characters")
        
        return completion
        
    except ClientError as e:
        logger.error(f"Client error: {str(e)}")
        return None

def handler(event, context):
    """Lambda handler function"""
    
    try:
        # Generate a unique session ID
        session_id = f"scheduled-newsletter-{int(datetime.now().timestamp())}"
        
        logger.info(f"Starting scheduled newsletter generation. Session ID: {session_id}")
        
        # Create Bedrock agent runtime client
        client = boto3.client(
            service_name="bedrock-agent-runtime",
            region_name=REGION
        )
        
        # Create Bedrock agent client for preparation
        agent_client = boto3.client(
            service_name="bedrock-agent",
            region_name=REGION
        )
        
        # Prepare the latest version of the agent before running it
        if not prepare_agent(agent_client, AGENT_ID):
            logger.error("Failed to prepare agent. Exiting.")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to prepare Bedrock agent',
                    'session_id': session_id
                })
            }
        
        logger.info("Agent preparation completed successfully!")
        
        # Generate newsletter
        result = invoke_agent(client, AGENT_ID, ALIAS_ID, "Generate a newsletter", session_id)
        
        if result:
            logger.info("Newsletter generated successfully!")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Newsletter generated successfully',
                    'session_id': session_id,
                    'content_length': len(result),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
        else:
            logger.error("Failed to generate newsletter")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to generate newsletter',
                    'session_id': session_id
                })
            }
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Unexpected error: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }
