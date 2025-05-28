import os
import sqlite3
import uuid
from datetime import datetime

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, current_time
import list_appointments
import create_appointment
import update_appointment

# Define a naming-focused system prompt
system_prompt = """You are a helpful personal assistant that specializes in managing my appointments and calendar. 
You have access to appointment management tools, a calculator, and can check the current time to help me organize my schedule effectively. 
Always provide the appointment id so that I can update it if required"""

model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    max_tokens=8000,
    # boto_client_config=Config(
    #    read_timeout=900,
    #    connect_timeout=900,
    #    retries=dict(max_attempts=3, mode="adaptive"),
    # ),
    additional_request_fields={
        #"thinking": {
            #"type": "disabled",
            # "budget_tokens": 2048,
       # }
    },
)

agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[
        current_time,
        calculator,
        create_appointment,
        list_appointments,
        update_appointment,
    ],
)

results = agent("How much is 2+2?")
print("\n")

# Print the agent's messages
print("\nAgent Messages:")
for msg in agent.messages:
    print(msg)

# Print the results metrics
print("\nResults Metrics:")
print(results.metrics)

results = agent(
    "Book 'Agent fun' for tomorrow 3pm in NYC. This meeting will discuss all the fun things that an agent can do"
)
print("\n")

for m in agent.messages:
    for content in m["content"]:
        if "toolUse" in content:
            print("Tool Use:")
            tool_use = content["toolUse"]
            print("\tToolUseId: ", tool_use["toolUseId"])
            print("\tname: ", tool_use["name"])
            print("\tinput: ", tool_use["input"])
        if "toolResult" in content:
            print("Tool Result:")
            tool_result = m["content"][0]["toolResult"]
            print("\tToolUseId: ", tool_result["toolUseId"])
            print("\tStatus: ", tool_result["status"])
            print("\tContent: ", tool_result["content"])
            print("=======================")