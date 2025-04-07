#!/usr/bin/env python3
"""
Debug script to run a complete test against the minimal MCP STDIO server.
This runs the test directly, not through the validator framework,
to better trace interactions and responses.
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

def send_request(server_process, request, description=None):
    """Send a JSON-RPC request to the server and get the response."""
    if description:
        print(f"\n{description}:")
    
    # Convert request to JSON string
    request_str = json.dumps(request)
    print(f"Sending: {request_str}")
    
    # Add newline and convert to bytes
    request_bytes = (request_str + "\n").encode('utf-8')
    
    # Send the request
    server_process.stdin.write(request_bytes)
    server_process.stdin.flush()
    
    # For notifications (no id), just return
    if isinstance(request, dict) and "id" not in request:
        print("No response expected (notification)")
        return None
        
    # Read response
    response_line = server_process.stdout.readline()
    
    # Check for empty response
    if not response_line:
        if server_process.poll() is not None:
            stderr = server_process.stderr.read().decode('utf-8')
            print(f"Process terminated unexpectedly with exit code {server_process.returncode}")
            print(f"Error output: {stderr}")
            return None
        else:
            print("Empty response received")
            return None
    
    # Parse and print the response
    response_str = response_line.decode('utf-8').strip()
    print(f"Received: {response_str}")
    
    try:
        return json.loads(response_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse response as JSON: {str(e)}")
        return None

def run_initialization_test():
    """Run the initialization test against the minimal MCP STDIO server."""
    print("\n=== Running Initialization Test ===\n")
    
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
        # 1. Send initialize request
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
        
        init_response = send_request(server_process, init_request, "Initialize request")
        
        if not init_response:
            print("Initialization failed")
            return 1
            
        # Verify the response structure
        if "result" not in init_response:
            print("Error: Invalid initialize response - missing 'result'")
            return 1
            
        result = init_response["result"]
        
        for required_field in ["protocolVersion", "capabilities", "serverInfo"]:
            if required_field not in result:
                print(f"Error: Invalid initialize response - missing '{required_field}'")
                return 1
                
        print("\nInitialization response verification:")
        print(f"Protocol version: {result['protocolVersion']}")
        print(f"Server info: {json.dumps(result['serverInfo'], indent=2)}")
        print(f"Capabilities: {json.dumps(result['capabilities'], indent=2)}")
        
        # 2. Send initialized notification
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
        
        send_request(server_process, init_notification, "Initialized notification")
        
        # 3. Send tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "test_tools_list",
            "method": "tools/list",
            "params": {}
        }
        
        tools_response = send_request(server_process, tools_request, "Tools list request")
        
        if not tools_response or "result" not in tools_response:
            print("Error: Tools list request failed")
            return 1
            
        if "tools" not in tools_response["result"]:
            print("Error: Invalid tools/list response - missing 'tools'")
            return 1
            
        tools = tools_response["result"]["tools"]
        print(f"\nReceived {len(tools)} tools")
        
        # 4. Try a basic tool call
        if tools and len(tools) > 0:
            echo_tool = None
            for tool in tools:
                if tool.get("name") == "echo":
                    echo_tool = tool
                    break
                    
            if echo_tool:
                call_request = {
                    "jsonrpc": "2.0",
                    "id": "test_tools_call",
                    "method": "tools/call",
                    "params": {
                        "name": "echo",
                        "arguments": {
                            "text": "Hello, MCP!"
                        }
                    }
                }
                
                call_response = send_request(server_process, call_request, "Tool call request (echo)")
                
                if not call_response or "result" not in call_response:
                    print("Error: Tool call failed")
                    return 1
                    
                print(f"\nTool call result: {json.dumps(call_response['result'], indent=2)}")
        
        # 5. Send a batch request
        batch_request = [
            {
                "jsonrpc": "2.0",
                "id": "batch_1",
                "method": "server/info",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": "batch_2",
                "method": "tools/list",
                "params": {}
            }
        ]
        
        batch_response = send_request(server_process, batch_request, "Batch request")
        
        if not batch_response or not isinstance(batch_response, list):
            print("Error: Batch request failed or response is not a list")
            return 1
            
        print(f"\nBatch response contains {len(batch_response)} responses")
        
        # 6. Send shutdown request
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "test_shutdown",
            "method": "shutdown",
            "params": {}
        }
        
        shutdown_response = send_request(server_process, shutdown_request, "Shutdown request")
        
        if not shutdown_response:
            print("Error: Shutdown request failed")
            return 1
            
        # 7. Send exit notification
        exit_notification = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        
        send_request(server_process, exit_notification, "Exit notification")
        
        # Wait for the process to terminate
        timeout = 5
        start_time = time.time()
        while server_process.poll() is None and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if server_process.poll() is None:
            print("\nServer process did not terminate, killing it")
            server_process.terminate()
            server_process.wait(timeout=1.0)
        
        # Check exit code
        exit_code = server_process.returncode
        print(f"\nServer process terminated with exit code: {exit_code}")
        
        # Read any remaining stderr output
        stderr = server_process.stderr.read().decode('utf-8')
        if stderr:
            print(f"\nServer stderr output:\n{stderr}")
        
        print("\n=== Initialization Test Completed Successfully ===")
        return 0
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # Make sure to terminate the server process
        if server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=1.0)
        
        return 1

def main():
    """Run all the tests."""
    # Run the initialization test
    return run_initialization_test()

if __name__ == "__main__":
    sys.exit(main()) 