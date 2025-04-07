#!/usr/bin/env python3
"""
Debug script to directly test interactions with the minimal MCP STDIO server.
"""

import subprocess
import json
import time
import sys
import os
import os.path

# Get the path to the root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PATH = os.path.join(ROOT_DIR, "minimal_mcp_stdio_server", "minimal_mcp_stdio_server.py")

def main():
    print("Starting minimal MCP STDIO server debug session")
    
    # Start the server process
    server_process = subprocess.Popen(
        SERVER_PATH,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # Use binary mode for better control
        bufsize=0    # Unbuffered
    )
    
    # Check if process started successfully
    if server_process.poll() is not None:
        stderr = server_process.stderr.read().decode('utf-8')
        print(f"Process failed to start. Exit code: {server_process.returncode}")
        print(f"Error output: {stderr}")
        return 1
    
    try:
        # Create an initialize request with the EXACT same format as the validator test
        init_request = {
            "jsonrpc": "2.0",
            "id": "test_initialization",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "supports": {
                        "tools": True,
                        "resources": True,
                        "prompt": True,
                        "utilities": True
                    }
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        }
        
        # Convert the request to JSON and add a newline
        request_bytes = (json.dumps(init_request) + "\n").encode('utf-8')
        
        # Send the request
        print(f"Sending initialize request: {json.dumps(init_request)}")
        server_process.stdin.write(request_bytes)
        server_process.stdin.flush()
        
        # Read the response
        response_line = server_process.stdout.readline()
        
        # Check for empty response
        if not response_line:
            if server_process.poll() is not None:
                stderr = server_process.stderr.read().decode('utf-8')
                print(f"Process terminated unexpectedly with exit code {server_process.returncode}")
                print(f"Error output: {stderr}")
                return 1
            else:
                print("Empty response received")
                return 1
        
        # Parse and print the response
        response_str = response_line.decode('utf-8').strip()
        print(f"Received initialize response: {response_str}")
        
        try:
            response = json.loads(response_str)
        except json.JSONDecodeError as e:
            print(f"Failed to parse response as JSON: {str(e)}")
            return 1
        
        # Send initialized notification
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
        notification_bytes = (json.dumps(init_notification) + "\n").encode('utf-8')
        
        print(f"Sending initialized notification: {json.dumps(init_notification)}")
        server_process.stdin.write(notification_bytes)
        server_process.stdin.flush()
        
        # Wait a moment for processing
        time.sleep(0.5)
        
        # Send a tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "test_tools_list",
            "method": "tools/list",
            "params": {}
        }
        tools_request_bytes = (json.dumps(tools_request) + "\n").encode('utf-8')
        
        print(f"Sending tools/list request: {json.dumps(tools_request)}")
        server_process.stdin.write(tools_request_bytes)
        server_process.stdin.flush()
        
        # Read the response
        response_line = server_process.stdout.readline()
        
        # Check for empty response
        if not response_line:
            if server_process.poll() is not None:
                stderr = server_process.stderr.read().decode('utf-8')
                print(f"Process terminated unexpectedly with exit code {server_process.returncode}")
                print(f"Error output: {stderr}")
                return 1
            else:
                print("Empty response received")
                return 1
        
        # Parse and print the response
        response_str = response_line.decode('utf-8').strip()
        print(f"Received tools/list response: {response_str}")
        
        # Send shutdown request
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "test_shutdown",
            "method": "shutdown",
            "params": {}
        }
        shutdown_request_bytes = (json.dumps(shutdown_request) + "\n").encode('utf-8')
        
        print(f"Sending shutdown request: {json.dumps(shutdown_request)}")
        server_process.stdin.write(shutdown_request_bytes)
        server_process.stdin.flush()
        
        # Read the response
        response_line = server_process.stdout.readline()
        
        # Check for empty response
        if not response_line:
            if server_process.poll() is not None:
                stderr = server_process.stderr.read().decode('utf-8')
                print(f"Process terminated unexpectedly with exit code {server_process.returncode}")
                print(f"Error output: {stderr}")
                return 1
            else:
                print("Empty response received")
                return 1
        
        # Parse and print the response
        response_str = response_line.decode('utf-8').strip()
        print(f"Received shutdown response: {response_str}")
        
        # Send exit notification
        exit_notification = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        exit_notification_bytes = (json.dumps(exit_notification) + "\n").encode('utf-8')
        
        print(f"Sending exit notification: {json.dumps(exit_notification)}")
        server_process.stdin.write(exit_notification_bytes)
        server_process.stdin.flush()
        
        # Wait for the process to terminate
        timeout = 5
        start_time = time.time()
        while server_process.poll() is None and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if server_process.poll() is None:
            print("Server process did not terminate, killing it")
            server_process.terminate()
            server_process.wait(timeout=1.0)
        
        # Check exit code
        exit_code = server_process.returncode
        print(f"Server process terminated with exit code: {exit_code}")
        
        # Read any remaining stderr output
        stderr = server_process.stderr.read().decode('utf-8')
        if stderr:
            print(f"Server stderr output: {stderr}")
        
        return 0
        
    except Exception as e:
        print(f"Error during debug session: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # Make sure to terminate the server process
        if server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=1.0)
        
        return 1
    
if __name__ == "__main__":
    sys.exit(main()) 