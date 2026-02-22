from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, StreamEvent
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Serve static files (HTML/JS) from a folder named 'static'
if not os.path.exists("static"): os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return FileResponse("static/index.html")

@app.websocket("/ws/audit")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for the user to trigger an audit via the UI
            data = await websocket.receive_text()
            
            options = ClaudeAgentOptions(
                permission_mode="bypassPermissions",
                cwd=os.getcwd(),
                env={
                    "CLAUDE_CODE_USE_BEDROCK": "1",
                    "AWS_REGION": "us-east-1",
                    "ANTHROPIC_MODEL": "us.anthropic.claude-sonnet-4-6"
                },
                allowed_tools=["Bash", "Read", "Write"]
            )

            # Use the SDK to stream events to the frontend
            async for message in query(prompt=data, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await websocket.send_json({"type": "text", "content": block.text})
                
                # Check for tool calls (e.g., Claude running kubectl)
                elif hasattr(message, 'event') and message.event.get("type") == "tool_use":
                    tool_name = message.event.get("name")
                    await websocket.send_json({"type": "tool", "content": f"Executing: {tool_name}"})

    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)