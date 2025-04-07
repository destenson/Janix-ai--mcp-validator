#!/usr/bin/env python3

"""
Quick test for the minimal MCP server
"""

import subprocess
import json
import time

def main():
    print("Starting minimal MCP server test...")
    
    # Start the server process
    server_cmd = "./minimal_mcp_server/minimal_mcp_server.py"
    server_process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Give the server a moment to start
    time.sleep(0.5)
    
    # Check if the process started successfully
    if server_process.poll() is not None:
        print(f"ERROR: Server failed to start. Exit code: {server_process.returncode}")
        stderr = server_process.stderr.read()
        print(f"Server error output: {stderr}")
        return 1
    
    # Test initialization
    print("\nSending initialize request...")
    initialize_request = {
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "supports": {
                    "filesystem": True
                }
            },
            "clientInfo": {
                "name": "TestClient",
                "version": "1.0.0"
            }
        }
    }
    
    # Convert request to JSON and add newline
    request_str = json.dumps(initialize_request) + "\n"
    
    # Send the request
    server_process.stdin.write(request_str)
    server_process.stdin.flush()
    
    # Read the response
    response_str = server_process.stdout.readline().strip()
    print(f"Server response: {response_str}")
    
    # Parse the response
    try:
        response = json.loads(response_str)
        if "result" in response and "protocolVersion" in response["result"]:
            print(f"SUCCESS: Received valid initialize response with protocol version: {response['result']['protocolVersion']}")
        else:
            print("ERROR: Invalid initialize response")
            print(f"Response: {response}")
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON response: {response_str}")
    
    # Send shutdown request
    print("\nSending shutdown request...")
    shutdown_request = {
        "jsonrpc": "2.0",
        "id": "test-shutdown",
        "method": "shutdown",
        "params": {}
    }
    
    # Convert request to JSON and add newline
    request_str = json.dumps(shutdown_request) + "\n"
    
    # Send the request
    server_process.stdin.write(request_str)
    server_process.stdin.flush()
    
    # Read the response
    response_str = server_process.stdout.readline().strip()
    print(f"Server response: {response_str}")
    
    # Send exit notification
    print("\nSending exit notification...")
    exit_notification = {
        "jsonrpc": "2.0",
        "method": "exit"
    }
    
    # Convert request to JSON and add newline
    request_str = json.dumps(exit_notification) + "\n"
    
    # Send the request
    server_process.stdin.write(request_str)
    server_process.stdin.flush()
    
    # Wait for the process to exit
    try:
        server_process.wait(timeout=2.0)
        print(f"Server exited with code: {server_process.returncode}")
        if server_process.returncode == 0:
            print("SUCCESS: Server shut down gracefully")
            return 0
        else:
            print(f"ERROR: Server exited with non-zero code: {server_process.returncode}")
            return 1
    except subprocess.TimeoutExpired:
        print("ERROR: Server did not exit within timeout period")
        server_process.terminate()
        return 1

if __name__ == "__main__":
    exit(main()) 