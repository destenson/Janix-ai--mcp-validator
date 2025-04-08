#!/usr/bin/env python3
"""
A simple script to verify that the fetch server works properly.
This is a quick test to confirm our environment setup is working.
"""

import json
import subprocess
import sys
import time

def main():
    print("\n=== FETCH SERVER VERIFICATION TEST ===\n")
    
    # Start the server process
    print("Starting the fetch server...")
    process = subprocess.Popen(
        ["python", "-m", "mcp_server_fetch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give it a moment to start
    time.sleep(1)
    
    # Check if the process is still running
    if process.poll() is not None:
        print("❌ ERROR: Server process failed to start")
        stderr = process.stderr.read()
        print(f"Error output: {stderr}")
        return 1
    else:
        print("✅ Server process started successfully")
    
    # Send initialization request
    print("\nInitializing the server...")
    init_request = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "FetchVerificationTest", "version": "1.0.0"}
        }
    }
    
    # Send the request
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()
    
    # Read the response
    response_str = process.stdout.readline().strip()
    
    if not response_str:
        print("❌ ERROR: No initialization response received")
        process.terminate()
        return 1
    
    try:
        response = json.loads(response_str)
        if "result" in response:
            print("✅ Server initialized successfully")
            print(f"   Server info: {response['result'].get('serverInfo', {})}")
        else:
            print(f"❌ ERROR: Initialization failed: {response.get('error', {})}")
            process.terminate()
            return 1
    except json.JSONDecodeError:
        print(f"❌ ERROR: Invalid JSON response: {response_str}")
        process.terminate()
        return 1
    
    # Send initialized notification
    print("\nSending initialized notification...")
    init_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    process.stdin.write(json.dumps(init_notification) + "\n")
    process.stdin.flush()
    print("✅ Initialized notification sent")
    
    # List tools
    print("\nListing available tools...")
    tools_request = {
        "jsonrpc": "2.0",
        "id": "tools",
        "method": "tools/list",
        "params": {}
    }
    
    process.stdin.write(json.dumps(tools_request) + "\n")
    process.stdin.flush()
    
    # Read the response
    response_str = process.stdout.readline().strip()
    
    if not response_str:
        print("❌ ERROR: No tools list response received")
        process.terminate()
        return 1
    
    try:
        response = json.loads(response_str)
        if "result" in response:
            tools = response["result"]
            print(f"✅ Successfully retrieved {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
        else:
            print(f"❌ ERROR: Tools listing failed: {response.get('error', {})}")
            process.terminate()
            return 1
    except json.JSONDecodeError:
        print(f"❌ ERROR: Invalid JSON response: {response_str}")
        process.terminate()
        return 1
    
    # Try fetching a URL
    print("\nTesting fetch functionality...")
    fetch_request = {
        "jsonrpc": "2.0",
        "id": "fetch",
        "method": "tools/call",
        "params": {
            "name": "fetch",
            "parameters": {
                "url": "https://example.com",
                "max_length": 500
            }
        }
    }
    
    process.stdin.write(json.dumps(fetch_request) + "\n")
    process.stdin.flush()
    
    # Read the response
    response_str = process.stdout.readline().strip()
    
    if not response_str:
        print("❌ ERROR: No fetch response received")
        process.terminate()
        return 1
    
    try:
        response = json.loads(response_str)
        if "result" in response:
            content = response["result"]
            content_length = len(content)
            print(f"✅ Successfully fetched content ({content_length} characters)")
            print(f"   Content preview: {content[:100]}...")
        else:
            print(f"❌ ERROR: Fetch operation failed: {response.get('error', {})}")
            process.terminate()
            return 1
    except json.JSONDecodeError:
        print(f"❌ ERROR: Invalid JSON response: {response_str}")
        process.terminate()
        return 1
    
    # Clean up
    print("\nTerminating server process...")
    process.terminate()
    
    print("\n=== TEST COMPLETED SUCCESSFULLY ===\n")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 