import json
import os
import subprocess
import sys

def send_request(request):
    # Convert the request to JSON
    request_json = json.dumps(request)
    # Print the request
    print(f"Sending request: {request_json}")
    # Send the request to the server
    proc = subprocess.Popen(
        ["node", "/Users/scott/AI/MCP/servers/src/brave-search/dist/index.js"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ, BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM")
    )
    
    stdout, stderr = proc.communicate(input=request_json + "\n")
    
    if stderr:
        print(f"Error: {stderr}")
        
    # Parse and return the response
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse response: {stdout}")
        return None

# Initialize the server
init_request = {
    "jsonrpc": "2.0",
    "id": "init",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05"
    }
}

response = send_request(init_request)
print(f"Initialization response: {json.dumps(response, indent=2)}")

# Send initialized notification
initialized_notification = {
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {}
}

send_request(initialized_notification)

# Use the brave_web_search tool
web_search_request = {
    "jsonrpc": "2.0",
    "id": "web_search",
    "method": "generate",
    "params": {
        "input": "",
        "toolInput": {
            "name": "brave_web_search",
            "parameters": {
                "query": "What is MCP protocol?",
                "count": 3
            }
        }
    }
}

response = send_request(web_search_request)
print(f"Web search response: {json.dumps(response, indent=2)}") 