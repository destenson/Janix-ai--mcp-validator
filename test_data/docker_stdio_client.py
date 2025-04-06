#!/usr/bin/env python3
"""
Modified MCP stdio client for testing the Docker filesystem server.

This script launches the Docker filesystem server as a subprocess and communicates with it using
the stdio transport mechanism, sending various requests to test against the MCP specification.
"""

import json
import subprocess
import time
import sys
import os

def main():
    # Determine the absolute path to the test directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_files_dir = os.path.join(script_dir, "files")
    
    # Ensure the test directory exists
    os.makedirs(test_files_dir, exist_ok=True)
    
    # Launch the Docker filesystem server in stdio mode
    server_process = subprocess.Popen(
        ["docker", "run", "-i", "--rm", "--network", "mcp-test-network",
         "--mount", f"type=bind,src={test_files_dir},dst=/projects/files",
         "mcp/filesystem", "/projects"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Define the test requests
    test_requests = [
        # 1. Initialize request - updated with required parameters
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "supports": {
                        "filesystem": True
                    }
                },
                "clientInfo": {
                    "name": "mcp-test-client",
                    "version": "0.1.0"
                }
            }
        },
        
        # 2. Initialized notification - to be sent after successful initialize
        {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        },
        
        # 3. Get available tools
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        },
        
        # 4. List allowed directories
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_allowed_directories",
                "arguments": {}
            }
        },
        
        # 5. List files in projects directory
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "list_directory",
                "arguments": {
                    "path": "/projects"
                }
            }
        },
        
        # 6. List files in the test directory
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_directory",
                "arguments": {
                    "path": "/projects/files"
                }
            }
        },
        
        # 7. Create a new test file
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "write_file",
                "arguments": {
                    "path": "/projects/files/created_by_mcp.txt",
                    "content": "This file was created by the MCP stdio client test!"
                }
            }
        },
        
        # 8. Read the test file
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "path": "/projects/files/test.txt"
                }
            }
        },
        
        # 9. Read the newly created file
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "path": "/projects/files/created_by_mcp.txt"
                }
            }
        }
    ]
    
    # Process to handle stderr in a non-blocking way
    import threading
    
    def print_stderr():
        for line in server_process.stderr:
            print(f"[SERVER] {line.strip()}", file=sys.stderr)
    
    stderr_thread = threading.Thread(target=print_stderr, daemon=True)
    stderr_thread.start()
    
    # Give the server a moment to start up
    print("Waiting for server to initialize...")
    time.sleep(2)
    
    # Send each request and print the response
    notification_sent = False
    server_capabilities = {}
    
    for i, request in enumerate(test_requests):
        # Skip sending the initialized notification if initialize failed
        if i == 1 and not notification_sent:
            continue
            
        is_notification = "id" not in request
        request_type = "NOTIFICATION" if is_notification else "REQUEST"
        
        print(f"\n--- TEST {request_type} {i+1} ---")
        print(f"Sending: {json.dumps(request)}")
        
        # Send the request
        try:
            server_process.stdin.write(json.dumps(request) + "\n")
            server_process.stdin.flush()
        except BrokenPipeError:
            print("❌ Broken pipe error - server may have terminated")
            break
        
        # For notifications, don't expect a response
        if is_notification:
            print("✅ Notification sent (no response expected)")
            if request["method"] == "initialized":
                notification_sent = True
            time.sleep(0.5)
            continue
        
        # Wait for and get the response for requests
        response = server_process.stdout.readline()
        
        if not response:
            print("❌ No response received - server may have terminated")
            break
        
        try:
            response_json = json.loads(response)
            print(f"Response: {json.dumps(response_json, indent=2)}")
            
            # Store capabilities from initialize response
            if i == 0 and "result" in response_json:
                if "capabilities" in response_json["result"]:
                    server_capabilities = response_json["result"]["capabilities"]
                    print(f"Server capabilities: {json.dumps(server_capabilities, indent=2)}")
            
            # Validate the response
            if "result" in response_json:
                print("✅ Request successful")
                # If this was the initialize request, mark to send initialized notification
                if i == 0:
                    notification_sent = True
            elif "error" in response_json:
                print(f"❌ Request failed: {response_json['error']['message']}")
            else:
                print("❓ Unknown response format")
                
        except json.JSONDecodeError:
            print(f"❌ Failed to parse response: {response}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Clean up
    print("\nTerminating server...")
    try:
        server_process.stdin.close()
    except:
        pass
    
    server_process.terminate()
    
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Server process not responding, forcing kill...")
        server_process.kill()
    
    print("Test completed")

if __name__ == "__main__":
    main() 