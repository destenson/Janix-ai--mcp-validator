#!/usr/bin/env python3
"""
Simple MCP stdio client for testing the MCP test server.

This script launches the test server as a subprocess and communicates with it using
the stdio transport mechanism, sending various requests to test against the 2025-03-26 specification.
"""

import json
import subprocess
import time
import sys

def main():
    # Launch the test server in stdio mode with debug output
    server_process = subprocess.Popen(
        ["python", "test_server.py", "--debug"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Define the test requests based on 2025-03-26 specification
    test_requests = [
        # 1. Initialize request
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        },
        
        # 2. Filesystem ls request
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "filesystem.ls",
            "params": {
                "path": "/"
            }
        },
        
        # 3. Filesystem stat request
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "filesystem.stat",
            "params": {
                "path": "/file1.txt"
            }
        },
        
        # 4. Filesystem read request
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "filesystem.read",
            "params": {
                "path": "/file1.txt"
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
    
    # Send each request and print the response
    for i, request in enumerate(test_requests):
        print(f"\n--- TEST REQUEST {i+1} ---")
        print(f"Sending: {json.dumps(request)}")
        
        # Send the request
        server_process.stdin.write(json.dumps(request) + "\n")
        server_process.stdin.flush()
        
        # Wait for and get the response
        response = server_process.stdout.readline()
        
        try:
            response_json = json.loads(response)
            print(f"Response: {json.dumps(response_json, indent=2)}")
            
            # Validate the response against 2025-03-26 specification
            if "result" in response_json:
                print("✅ Request successful")
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
    server_process.stdin.close()
    server_process.terminate()
    
    try:
        server_process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        server_process.kill()
        print("Server process killed")
    
    print("Test completed")

if __name__ == "__main__":
    main() 