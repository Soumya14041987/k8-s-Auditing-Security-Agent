"""
FILE: main.py
DESCRIPTION: K8s Security Audit Agent using Claude Agent SDK & AWS Bedrock.
OFFICIAL DOCS: https://platform.claude.com/docs/en/agent-sdk/python
"""

import asyncio
import os
import sys
from loguru import logger
from dotenv import load_dotenv

# 1. OFFICIAL SDK IMPORTS (v0.1.38+)
# We use query() for the agent loop and ClaudeAgentOptions for configuration.
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock

# Load AWS credentials and regional settings
load_dotenv()

# 2. AUDIT LOGGING SETUP
logger.remove()
logger.add(sys.stderr, format="<blue>{time:HH:mm:ss}</blue> | <level>{level: <8}</level> | {message}", level="INFO")
logger.add("audit_trace.log", rotation="10 MB")

async def run_k8s_security_audit():
    """
    Initializes and executes the autonomous Kubernetes security audit.
    """
    
    # 3. AGENT CONFIGURATION & BEDROCK INTEGRATION
    # The 'env' dictionary tells the SDK to use Bedrock instead of local models.
    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a Senior K8s Security Auditor. Your goal is to find risks "
            "like privileged containers, wide-open RBAC, and missing network policies. "
            "Use the 'k8s_audit' skill found in ./.claude/skills/."
        ),
        # 'bypassPermissions' allows the agent to run kubectl without manual approval.
        permission_mode="bypassPermissions",
        cwd=os.getcwd(),
        env={
            "CLAUDE_CODE_USE_BEDROCK": "1",
            "AWS_REGION": "us-east-1",
            "ANTHROPIC_MODEL": "us.anthropic.claude-sonnet-4-6"
        },
        # Explicitly whitelist the tools Claude needs for terminal interaction.
        allowed_tools=["Bash", "Read", "Write", "Grep"]
    )

    logger.info("🚀 Starting Security Audit via Amazon Bedrock (us-east-1)...")

    # 4. EXECUTION LOOP
    # The agent will automatically call kubectl, analyze YAML, and write the report.
    prompt = "Run the k8s_audit skill and generate a detailed report in k8s_audit_report.md"
    
    try:
        # query() is the entry point that manages the entire 'Plan-Act-Report' cycle.
        async for message in query(prompt=prompt, options=options):
            # We filter for AssistantMessages to see Claude's reasoning in the terminal.
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"\n[Claude Auditor]: {block.text}")
                        
        logger.success("✅ Audit process finished successfully.")

    except Exception as e:
        logger.error(f"❌ Audit interrupted by error: {e}")

# 5. ENTRY POINT
if __name__ == "__main__":
    asyncio.run(run_k8s_security_audit())