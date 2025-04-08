#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Simple Test Script for Minimal MCP Server

This script starts the minimal MCP server as a subprocess and
interacts with it directly using standard I/O to verify basic functionality.
"""

import json
import subprocess
import sys
import time
import argparse


def main():
    """Main test function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the minimal MCP server.")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                        default="2024-11-05", help="Protocol version to use")
    parser.add_argument("--full", action="store_true", 
                        help="Run all tests including optional ones")
    args = parser.parse_args()
    
    print(f"Starting minimal MCP server test with protocol version {args.protocol_version}...")
    
    # Start the server process
    server_cmd = "./minimal_mcp_server.py"  # Server is in the same directory
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
    
    # Test 1: Initialize
    print("\nTest 1: Initialize")
    # Build capabilities based on protocol version
    if args.protocol_version == "2024-11-05":
        capabilities = {
            "supports": {
                "filesystem": True,
                "resources": True,
                "utilities": True,
                "prompt": True
            }
        }
    else:  # 2025-03-26
        capabilities = {
            "tools": {
                "listChanged": True
            },
            "resources": True,
            "prompt": {
                "streaming": True
            },
            "utilities": True
        }
    
    initialize_request = {
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": args.protocol_version,
            "capabilities": capabilities,
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
        shutdown_server(server_process)
        return 1
        
    if "protocolVersion" not in init_response["result"]:
        print("ERROR: Initialize response missing 'protocolVersion'")
        shutdown_server(server_process)
        return 1
    
    # Test 2: Send tools/list request
    print("\nTest 2: Tools List")
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
        shutdown_server(server_process)
        return 1
        
    if "tools" not in tools_response["result"]:
        print("ERROR: Tools list response missing 'tools'")
        shutdown_server(server_process)
        return 1
    
    # Test 3: Call a tool
    print("\nTest 3: Call Tool")
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": "test-tool-call",
        "method": "tools/call",
        "params": {
            "name": "echo",
            "arguments": {
                "text": "Hello, MCP!"
            }
        }
    }
    
    tool_call_response = send_request(server_process, tool_call_request)
    print(f"Tool call response: {json.dumps(tool_call_response, indent=2)}")
    
    # Verify tool call response
    if "result" not in tool_call_response:
        print("ERROR: Tool call response missing 'result'")
        shutdown_server(server_process)
        return 1
        
    if "content" not in tool_call_response["result"]:
        print("ERROR: Tool call response missing 'content'")
        shutdown_server(server_process)
        return 1
    
    # Test 4: Batch Requests
    if args.full:
        print("\nTest 4: Batch Requests")
        batch_request = [
            {
                "jsonrpc": "2.0",
                "id": "batch-1",
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {
                        "text": "Batch request 1"
                    }
                }
            },
            {
                "jsonrpc": "2.0",
                "id": "batch-2",
                "method": "tools/call",
                "params": {
                    "name": "add",
                    "arguments": {
                        "a": 5,
                        "b": 7
                    }
                }
            }
        ]
        
        batch_response = send_request(server_process, batch_request)
        print(f"Batch response: {json.dumps(batch_response, indent=2)}")
        
        # Verify batch response
        if not isinstance(batch_response, list):
            print("ERROR: Batch response is not a list")
            shutdown_server(server_process)
            return 1
            
        if len(batch_response) != 2:
            print(f"ERROR: Expected 2 responses in batch, got {len(batch_response)}")
            shutdown_server(server_process)
            return 1
    
    # Test 5: Resources (if using 2025-03-26)
    if args.protocol_version == "2025-03-26" or args.full:
        print("\nTest 5: Resources")
        
        # Create a resource
        create_resource_request = {
            "jsonrpc": "2.0",
            "id": "test-resource-create",
            "method": "resources/create",
            "params": {
                "type": "test-resource",
                "data": {
                    "name": "Test Resource",
                    "value": 123
                }
            }
        }
        
        create_resource_response = send_request(server_process, create_resource_request)
        print(f"Create resource response: {json.dumps(create_resource_response, indent=2)}")
        
        # Verify resource creation
        if "result" not in create_resource_response:
            print("ERROR: Create resource response missing 'result'")
            shutdown_server(server_process)
            return 1
            
        if "id" not in create_resource_response["result"]:
            print("ERROR: Create resource response missing 'id'")
            shutdown_server(server_process)
            return 1
            
        resource_id = create_resource_response["result"]["id"]
        
        # List resources
        list_resources_request = {
            "jsonrpc": "2.0",
            "id": "test-resource-list",
            "method": "resources/list",
            "params": {}
        }
        
        list_resources_response = send_request(server_process, list_resources_request)
        print(f"List resources response: {json.dumps(list_resources_response, indent=2)}")
        
        # Verify resource list
        if "result" not in list_resources_response:
            print("ERROR: List resources response missing 'result'")
            shutdown_server(server_process)
            return 1
            
        if "resources" not in list_resources_response["result"]:
            print("ERROR: List resources response missing 'resources'")
            shutdown_server(server_process)
            return 1
            
        # Get resource
        get_resource_request = {
            "jsonrpc": "2.0",
            "id": "test-resource-get",
            "method": "resources/get",
            "params": {
                "id": resource_id
            }
        }
        
        get_resource_response = send_request(server_process, get_resource_request)
        print(f"Get resource response: {json.dumps(get_resource_response, indent=2)}")
        
        # Verify get resource
        if "result" not in get_resource_response:
            print("ERROR: Get resource response missing 'result'")
            shutdown_server(server_process)
            return 1
            
        if "id" not in get_resource_response["result"]:
            print("ERROR: Get resource response missing 'id'")
            shutdown_server(server_process)
            return 1
    
    # Test 6: Server Info
    if args.full:
        print("\nTest 6: Server Info")
        server_info_request = {
            "jsonrpc": "2.0",
            "id": "test-server-info",
            "method": "server/info",
            "params": {}
        }
        
        server_info_response = send_request(server_process, server_info_request)
        print(f"Server info response: {json.dumps(server_info_response, indent=2)}")
        
        # Verify server info
        if "result" not in server_info_response:
            print("ERROR: Server info response missing 'result'")
            shutdown_server(server_process)
            return 1
            
        if "name" not in server_info_response["result"]:
            print("ERROR: Server info response missing 'name'")
            shutdown_server(server_process)
            return 1
    
    # Test 7: Error Handling
    if args.full:
        print("\nTest 7: Error Handling")
        
        # Test method not found
        method_not_found_request = {
            "jsonrpc": "2.0",
            "id": "test-method-not-found",
            "method": "non_existent_method",
            "params": {}
        }
        
        method_not_found_response = send_request(server_process, method_not_found_request)
        print(f"Method not found response: {json.dumps(method_not_found_response, indent=2)}")
        
        # Verify error
        if "error" not in method_not_found_response:
            print("ERROR: Method not found response missing 'error'")
            shutdown_server(server_process)
            return 1
            
        if method_not_found_response["error"]["code"] != -32601:
            print(f"ERROR: Expected error code -32601, got {method_not_found_response['error']['code']}")
            shutdown_server(server_process)
            return 1
        
        # Test invalid params
        invalid_params_request = {
            "jsonrpc": "2.0",
            "id": "test-invalid-params",
            "method": "tools/call",
            "params": {
                # Missing required 'name' parameter
            }
        }
        
        invalid_params_response = send_request(server_process, invalid_params_request)
        print(f"Invalid params response: {json.dumps(invalid_params_response, indent=2)}")
        
        # Verify error
        if "error" not in invalid_params_response:
            print("ERROR: Invalid params response missing 'error'")
            shutdown_server(server_process)
            return 1
            
        if invalid_params_response["error"]["code"] != -32602:
            print(f"ERROR: Expected error code -32602, got {invalid_params_response['error']['code']}")
            shutdown_server(server_process)
            return 1
    
    # Final Test: Shutdown
    print("\nFinal Test: Shutdown")
    shutdown_request = {
        "jsonrpc": "2.0",
        "id": "test-shutdown",
        "method": "shutdown",
        "params": {}
    }
    
    shutdown_response = send_request(server_process, shutdown_request)
    print(f"Shutdown response: {json.dumps(shutdown_response, indent=2)}")
    
    # Send exit notification
    exit_notification = {
        "jsonrpc": "2.0",
        "method": "exit"
    }
    
    # No response expected for notifications
    send_request(server_process, exit_notification, wait_for_response=False)
    print("Sent exit notification")
    
    # Wait for the process to terminate
    try:
        server_process.wait(timeout=2.0)
        print(f"Server exited with code: {server_process.returncode}")
    except subprocess.TimeoutExpired:
        print("Server did not exit, force terminating...")
        server_process.terminate()
        try:
            server_process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()
    
    print("\nAll tests completed!")
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


def shutdown_server(process):
    """
    Shutdown the server gracefully.
    
    Args:
        process: The server subprocess
    """
    try:
        # Send shutdown request
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "shutdown",
            "method": "shutdown",
            "params": {}
        }
        send_request(process, shutdown_request)
        
        # Send exit notification
        exit_notification = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        send_request(process, exit_notification, wait_for_response=False)
        
        # Wait for the process to terminate
        process.wait(timeout=2.0)
    except Exception as e:
        print(f"Error shutting down server: {e}")
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    sys.exit(main()) 