import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv
from anthropic import AnthropicBedrock
from claude_agent_sdk import Agent, AgentOptions
from claude_agent_sdk.tools import BashTool, WriteFileTool

# Load credentials and region
load_dotenv()

async def run_bedrock_k8s_audit():
    # Initialize the Bedrock Client for us-east-1
    client = AnthropicBedrock(aws_region="us-east-1")

    # Define the System Prompt
    system_prompt = """
    You are a Senior K8s Security Auditor running in AWS Bedrock (us-east-1).
    You excel at finding misconfigurations using the 'k8s_audit' skill.
    Always output findings in a clear, actionable format.
    """

    # Options for Claude 4.6 Sonnet
    options = AgentOptions(
        model="anthropic.claude-sonnet-4-6", 
        client=client,
        system_prompt=system_prompt,
        permission_mode="bypass_permissions",
        skills_path="./.claude/skills",
        tools=[BashTool(), WriteFileTool()]
    )

    agent = Agent(options)
    logger.info("Initializing Agent on Bedrock (us-east-1)...")

    try:
        user_request = "Conduct a full security audit of my current K8s context and save the report."
        
        async for message in agent.run(user_request):
            if hasattr(message, 'text') and message.text:
                print(f"\n[Claude]: {message.text}")
    except Exception as e:
        logger.error(f"Audit Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_bedrock_k8s_audit())