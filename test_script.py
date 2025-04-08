#!/usr/bin/env python3
import requests
import json

# Server URL
server_url = "http://localhost:8080/mcp"

# 1. Initialize the server
print("Initializing server...")
init_payload = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "clientInfo": {
            "name": "Python Test Client",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {"asyncSupported": True},
            "resources": True
        }
    },
    "id": 1
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

response = requests.post(server_url, headers=headers, json=init_payload)
print(f"Status code: {response.status_code}")
print(f"Response headers: {dict(response.headers)}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

# Get the session ID
session_id = response.headers.get("Mcp-Session-Id")
if not session_id:
    print("ERROR: No session ID received")
    exit(1)

print(f"\nSession ID: {session_id}\n")

# 2. Get server info
print("\nGetting server info...")
server_info_payload = {
    "jsonrpc": "2.0",
    "method": "server/info",
    "id": 2
}

headers["Mcp-Session-Id"] = session_id
response = requests.post(server_url, headers=headers, json=server_info_payload)
print(f"Status code: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

# 3. List tools
print("\nListing tools...")
tools_list_payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 3
}

response = requests.post(server_url, headers=headers, json=tools_list_payload)
print(f"Status code: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

# 4. Call the echo tool
print("\nCalling echo tool...")
echo_payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "echo",
        "parameters": {
            "message": "Hello, MCP!"
        }
    },
    "id": 4
}

response = requests.post(server_url, headers=headers, json=echo_payload)
print(f"Status code: {response.status_code}")
print(f"Response body: {json.dumps(response.json(), indent=2)}")

print("\nTest completed successfully!") 