#!/usr/bin/env python3

"""
Test script for Brave Search MCP server.
Based on the test_minimal_server.py script.
"""

import json
import subprocess
import sys
import time
import os

def main():
    """Test the Brave Search MCP server."""
    print("Starting Brave Search MCP server test...")
    
    # Set up environment variables
    env = os.environ.copy()
    brave_api_key = env.get("BRAVE_API_KEY")
    if not brave_api_key:
        print("ERROR: BRAVE_API_KEY environment variable is not set")
        return 1
    
    # Start the server process
    server_cmd = "npx -y @modelcontextprotocol/server-brave-search"
    server_process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        env=env,
        shell=True
    )
    
    # Give the server a moment to start
    time.sleep(0.5)
    
    # Check if the process started successfully
    if server_process.poll() is not None:
        print(f"ERROR: Server failed to start. Exit code: {server_process.returncode}")
        stderr = server_process.stderr.read()
        print(f"Server error output: {stderr}")
        return 1
    
    # Test 1: Initialize
    print("\nTest 1: Initialize")
    initialize_request = {
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "TestClient",
                "version": "1.0.0"
            }
        }
    }
    
    init_response = send_request(server_process, initialize_request)
    print(f"Initialize response: {json.dumps(init_response, indent=2)}")
    
    # Verify initialize response
    if "result" not in init_response:
        print("ERROR: Initialize response missing 'result'")
        cleanup_server(server_process)
        return 1
    
    # Test 2: Send initialized notification
    print("\nTest 2: Sending initialized notification")
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    send_request(server_process, initialized_notification, wait_for_response=False)
    print("Initialized notification sent")
    
    # Test 3: Send tools/list request
    print("\nTest 3: Tools List")
    tools_list_request = {
        "jsonrpc": "2.0",
        "id": "test-tools-list",
        "method": "tools/list",
        "params": {}
    }
    
    tools_response = send_request(server_process, tools_list_request)
    print(f"Tools list response: {json.dumps(tools_response, indent=2)}")
    
    # Verify tools list response
    if "result" not in tools_response:
        print("ERROR: Tools list response missing 'result'")
        cleanup_server(server_process)
        return 1
        
    if "tools" not in tools_response["result"]:
        print("ERROR: Tools list response missing 'tools'")
        cleanup_server(server_process)
        return 1
    
    # Test 4: Call brave_web_search tool
    print("\nTest 4: Call brave_web_search Tool")
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": "test-tool-call",
        "method": "tools/call",
        "params": {
            "name": "brave_web_search",
            "arguments": {
                "query": "What is MCP protocol?",
                "count": 3
            }
        }
    }
    
    tool_call_response = send_request(server_process, tool_call_request)
    print(f"Tool call response: {json.dumps(tool_call_response, indent=2)}")
    
    # Verify tool call response
    if "result" not in tool_call_response:
        print("ERROR: Tool call response missing 'result'")
        cleanup_server(server_process)
        return 1
    
    # Clean up and exit
    print("\nAll tests completed successfully!")
    cleanup_server(server_process)
    return 0


def send_request(process, request, wait_for_response=True):
    """
    Send a request to the server and get the response.
    
    Args:
        process: The server subprocess
        request: The JSON-RPC request object
        wait_for_response: Whether to wait for a response
        
    Returns:
        The JSON-RPC response object, or None if wait_for_response is False
    """
    # Convert request to JSON and add newline
    request_str = json.dumps(request) + "\n"
    
    # Send the request
    process.stdin.write(request_str)
    process.stdin.flush()
    
    # Return immediately for notifications
    if not wait_for_response:
        return None
    
    # Read the response
    response_str = process.stdout.readline().strip()
    
    # Parse and return the response
    if response_str:
        return json.loads(response_str)
    else:
        return {"error": {"code": -32000, "message": "No response received"}}


def cleanup_server(process):
    """
    Clean up the server process (no graceful shutdown since it's not supported).
    
    Args:
        process: The server subprocess
    """
    try:
        # Try to send exit notification (might not be supported)
        exit_notification = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        send_request(process, exit_notification, wait_for_response=False)
        
        # Force terminate after a short wait
        time.sleep(0.5)
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    except Exception as e:
        print(f"Error cleaning up server: {e}")
        process.kill()
        process.wait()


if __name__ == "__main__":
    sys.exit(main()) 