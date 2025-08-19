#!/usr/bin/env python3
"""
Bedrock Brief Newsletter Generator
Simple script to generate newsletter using Bedrock agent
"""

import boto3
import json
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent configuration
AGENT_ID = "O7URHZNJJK"
ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"
SESSION_ID = f"newsletter-{int(datetime.now().timestamp())}"

def prepare_agent(client, agent_id):
    """Prepare the latest version of the agent before running it"""
    
    print("Preparing agent...")
    print(f"Agent ID: {agent_id}")
    print(f"Region: {REGION}")
    print()
    
    try:
        # Create a DRAFT version of the agent
        response = client.prepare_agent(
            agentId=agent_id
        )
        
        agent_status = response.get('agentStatus')
        agent_version = response.get('agentVersion')
        prepared_at = response.get('preparedAt')
        
        print(f"Agent preparation initiated:")
        print(f"  Status: {agent_status}")
        print(f"  Version: {agent_version}")
        print(f"  Prepared at: {prepared_at}")
        print()
        
        # Wait for agent to be prepared
        if agent_status == 'PREPARING':
            print("Waiting for agent to be prepared...")
            max_wait_time = 300  # 5 minutes
            wait_time = 0
            check_interval = 10  # Check every 10 seconds
            
            while wait_time < max_wait_time:
                time.sleep(check_interval)
                wait_time += check_interval
                
                # Check agent status
                agent_response = client.get_agent(agentId=agent_id)
                current_status = agent_response.get('agent', {}).get('agentStatus')
                
                print(f"  Current status: {current_status} (waited {wait_time}s)")
                
                if current_status == 'PREPARED':
                    print("Agent is now prepared and ready to use!")
                    return True
                elif current_status in ['FAILED', 'NOT_PREPARED']:
                    print(f"Agent preparation failed with status: {current_status}")
                    return False
                elif current_status == 'PREPARING':
                    continue
                else:
                    print(f"Unexpected agent status: {current_status}")
                    return False
            
            print("Timeout waiting for agent preparation")
            return False
            
        elif agent_status == 'PREPARED':
            print("Agent is already prepared and ready to use!")
            return True
        else:
            print(f"Agent preparation resulted in unexpected status: {agent_status}")
            return False
            
    except ClientError as e:
        print(f"Client error during agent preparation: {str(e)}")
        logger.error("Client error during agent preparation: %s", str(e))
        return False
    except Exception as e:
        print(f"Unexpected error during agent preparation: {e}")
        logger.error("Unexpected error during agent preparation: %s", str(e))
        return False

def invoke_agent(client, agent_id, alias_id, prompt, session_id):
    """Invoke the Bedrock agent and handle streaming response"""
    
    print("Generating newsletter...")
    print(f"Agent ID: {agent_id}")
    print(f"Alias ID: {alias_id}")
    print(f"Session ID: {session_id}")
    print(f"Region: {REGION}")
    print()
    
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
        print("Newsletter Content:")
        print("=" * 50)
        
        for event in response.get("completion"):
            # Collect agent output
            if 'chunk' in event:
                chunk = event["chunk"]
                text_chunk = chunk["bytes"].decode()
                completion += text_chunk
                print(text_chunk, end='', flush=True)
            
            # Log trace output
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event['trace']
                for key, value in trace.items():
                    logger.info("%s: %s", key, value)
        
        print("\n" + "=" * 50)
        print(f"\nAgent response completed. Total length: {len(completion)} characters")
        
        return completion
        
    except ClientError as e:
        print(f"Client error: {str(e)}")
        logger.error("Client error: %s", str(e))
        return None

def main():
    """Main function to generate newsletter"""
    
    try:
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
            print("Failed to prepare agent. Exiting.")
            return 1
        
        print("Agent preparation completed successfully!")
        print()
        
        # Generate newsletter
        result = invoke_agent(client, AGENT_ID, ALIAS_ID, "Generate a newsletter", SESSION_ID)
        
        if result:
            print("Newsletter generated successfully!")
        else:
            print("Failed to generate newsletter")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error("Unexpected error: %s", str(e))
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 