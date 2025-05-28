import threading
import time
from datetime import timedelta

from mcp import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from strands.models import BedrockModel
from mcp.server import FastMCP
from strands import Agent
from strands.tools.mcp import MCPClient
import os

# NETKSOP ERROR HERE WE NEED THE FULL CHAIN

#os.environ["REQUESTS_CA_BUNDLE"] = "/Users/sean/Desktop/NetskopeCertChain/caCert-root_ca-rootcaCert.pem"
os.environ["REQUESTS_CA_BUNDLE"] = "/Users/sean/Desktop/certadmin.pem"
#os.environ["REQUESTS_CA_BUNDLE"]="/Users/sean/Git/smurphnturf/agents-test/samples/01-getting-started/02-integration-mcp-tools/.venv/lib/python3.12/site-packages/certifi/cacert.pem"

#os.environ["SSL_CERT_FILE"]="/Users/sean/Git/smurphnturf/agents-test/samples/01-getting-started/02-integration-mcp-tools/.venv/lib/python3.12/site-packages/certifi/cacert.pem"
#os.environ["SSL_CERT_FILE"] = "/Users/sean/Desktop/NetskopeCertChain/caCert-root_ca-rootcaCert.pem"
#os.environ["SSL_CERT_FILE"] = "/Users/sean/Desktop/certadmin.pem"
#os.environ["PYTHONHTTPSVERIFY"] = "0"

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

# Connect to an MCP server using stdio transport
stdio_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-documentation-mcp-server@latest"]
        )
    )
)

# Create an agent with MCP tools
with stdio_mcp_client:
    # Get the tools from the MCP server
    tools = stdio_mcp_client.list_tools_sync()

    # Create an agent with these tools
    agent = Agent(model=model, tools=tools)

    response = agent("What is Amazon Bedrock pricing model. Be concise.")


# Create an MCP server
mcp = FastMCP("Calculator Server")

# Define a tool


@mcp.tool(description="Calculator tool which performs calculations")
def calculator(x: int, y: int) -> int:
    return x + y


@mcp.tool(description="This is a long running tool")
def long_running_tool(name: str) -> str:
    time.sleep(25)
    return f"Hello {name}"


def main():
    mcp.run(transport="streamable-http", mount_path="mcp")

#thread = threading.Thread(target=main)
#thread.start()