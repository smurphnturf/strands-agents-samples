import asyncio

import httpx
import nest_asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent, tool
from strands_tools import calculator
from strands.models import BedrockModel



model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    max_tokens=8000,
    additional_request_fields={},
)

agent = Agent(
    model=model,
    tools=[calculator],
    callback_handler=None
)

# Initialize our agent without a callback handler
#agent = Agent(tools=[calculator], callback_handler=None)

# Async function that iterators over streamed agent events


async def process_streaming_response():
    agent_stream = agent.stream_async("Calculate 2+2")
    async for event in agent_stream:
        print(event)


# Run the agent
#asyncio.run(process_streaming_response())


async def process_streaming_response():
    agent_stream = agent.stream_async("What is the capital of France and what is 42+7?")
    async for event in agent_stream:
        # Track event loop lifecycle
        if event.get("init_event_loop", False):
            print("🔄 Event loop initialized")
        elif event.get("start_event_loop", False):
            print("▶️ Event loop cycle starting")
        elif event.get("start", False):
            print("📝 New cycle started")
        elif "message" in event:
            print(f"📬 New message created: {event['message']['role']}")
        elif event.get("complete", False):
            print("✅ Cycle completed")
        elif event.get("force_stop", False):
            print(
                f"🛑 Event loop force-stopped: {event.get('force_stop_reason', 'unknown reason')}"
            )

        # Track tool usage
        if "current_tool_use" in event and event["current_tool_use"].get("name"):
            tool_name = event["current_tool_use"]["name"]
            print(f"🔧 Using tool: {tool_name}")

        # Show only a snippet of text to keep output clean
        if "data" in event:
            # Only show first 20 chars of each chunk for demo purposes
            data_snippet = event["data"][:20] + (
                "..." if len(event["data"]) > 20 else ""
            )
            print(f"📟 Text: {data_snippet}")


# Run the agent
#asyncio.run(process_streaming_response())



@tool
def weather_forecast(city: str, days: int = 3) -> str:
    return f"Weather forecast for {city} for the next {days} days..."


# FastAPI app
app = FastAPI()


class PromptRequest(BaseModel):
    prompt: str


@app.post("/stream")
async def stream_response(request: PromptRequest):
    async def generate():
        #agent = Agent(tools=[calculator, weather_forecast], callback_handler=None)
        agent = Agent(
            model=model,
            tools=[calculator, weather_forecast],
            callback_handler=None
        )
        try:
            async for event in agent.stream_async(request.prompt):
                if "data" in event:
                    yield event["data"]
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


# Function to start server without blocking
async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


# # Run server as background task
# if "server_task" not in globals():
#     server_task = asyncio.create_task(start_server())
#     await asyncio.sleep(0.1)  # Give server time to start

# print("✅ Server is running at http://0.0.0.0:8001")

import nest_asyncio
nest_asyncio.apply()

import threading

def run_server():
    import asyncio
    asyncio.run(start_server())

if "server_thread" not in globals():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    import time
    time.sleep(1)  # Give server time to start

print("✅ Server is running at http://0.0.0.0:8001")

async def fetch_stream():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://0.0.0.0:8001/stream",
            json={"prompt": "What is weather in NYC?"},
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():  # Skip empty lines
                    print("Received:", line)


# asyncio.run(fetch_stream())

def custom_callback_handler(**kwargs):
    # Process stream data
    if "data" in kwargs:
        print(f"MODEL OUTPUT: {kwargs['data']}")
    elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        print(f"\nUSING TOOL: {kwargs['current_tool_use']['name']}")


# Create an agent with custom callback handler
agent = Agent(
            model=model,
            tools=[calculator],
            callback_handler=custom_callback_handler
        )
#agent = Agent(tools=[calculator], callback_handler=custom_callback_handler)

agent("Calculate 2+2")