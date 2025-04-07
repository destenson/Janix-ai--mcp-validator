#!/usr/bin/env python3

"""
Direct Test Script for Minimal MCP Server

This script directly uses the STDIOTransport to test the minimal_mcp_server
without relying on the full test framework.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from transport.stdio_client import STDIOTransport

# Configuration
DEBUG = True
SERVER_COMMAND = "./minimal_mcp_server/minimal_mcp_server.py"
PROTOCOL_VERSION = "2025-03-26"  # Changed to test newer version

def log(message):
    """Simple logging function."""
    if DEBUG:
        print(f"[TEST] {message}")

def main():
    """Main test function."""
    log(f"Starting direct test of minimal_mcp_server with protocol version {PROTOCOL_VERSION}")
    
    # Create and start the transport
    transport = STDIOTransport(
        command=SERVER_COMMAND,
        debug=DEBUG,
        timeout=30
    )
    
    try:
        # Start the transport
        log("Starting STDIO transport...")
        if not transport.start():
            log("Failed to start transport")
            return 1
        
        # Test 1: Initialize with capabilities appropriate for 2025-03-26
        log("\nTest 1: Initialize")
        init_capabilities = {
            "tools": {
                "listChanged": True
            },
            "resources": True,
            "prompt": {
                "streaming": True
            },
            "utilities": True
        }
        
        init_request = {
            "jsonrpc": "2.0",
            "id": "test-init",
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": init_capabilities,
                "clientInfo": {
                    "name": "TestClient",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = transport.send_request(init_request)
        log(f"Initialize response: {json.dumps(init_response, indent=2)}")
        
        # Verify initialize response
        if "result" not in init_response:
            log("ERROR: Initialize response missing 'result'")
            return 1
            
        if "protocolVersion" not in init_response["result"]:
            log("ERROR: Initialize response missing 'protocolVersion'")
            return 1
        
        # Send initialized notification
        transport.send_notification({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Test 2: Send tools/list request
        log("\nTest 2: Tools List")
        tools_list_request = {
            "jsonrpc": "2.0",
            "id": "test-tools-list",
            "method": "tools/list",
            "params": {}
        }
        
        tools_response = transport.send_request(tools_list_request)
        log(f"Tools list response: {json.dumps(tools_response, indent=2)}")
        
        # Verify tools list response
        if "result" not in tools_response:
            log("ERROR: Tools list response missing 'result'")
            return 1
            
        if "tools" not in tools_response["result"]:
            log("ERROR: Tools list response missing 'tools'")
            return 1
        
        # Test 3: Call a tool
        log("\nTest 3: Call Tool")
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
        
        tool_call_response = transport.send_request(tool_call_request)
        log(f"Tool call response: {json.dumps(tool_call_response, indent=2)}")
        
        # Verify tool call response
        if "result" not in tool_call_response:
            log("ERROR: Tool call response missing 'result'")
            return 1
            
        if "content" not in tool_call_response["result"]:
            log("ERROR: Tool call response missing 'content'")
            return 1
            
        # Test 4: Resources (new in 2025-03-26)
        log("\nTest 4: Resources")
        
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
        
        create_resource_response = transport.send_request(create_resource_request)
        log(f"Create resource response: {json.dumps(create_resource_response, indent=2)}")
        
        # Verify create resource response
        if "result" not in create_resource_response:
            log("ERROR: Create resource response missing 'result'")
            return 1
            
        if "id" not in create_resource_response["result"]:
            log("ERROR: Create resource response missing 'id'")
            return 1
        
        # Get the resource ID
        resource_id = create_resource_response["result"]["id"]
        
        # List resources
        list_resources_request = {
            "jsonrpc": "2.0",
            "id": "test-resource-list",
            "method": "resources/list",
            "params": {}
        }
        
        list_resources_response = transport.send_request(list_resources_request)
        log(f"List resources response: {json.dumps(list_resources_response, indent=2)}")
        
        # Get resource
        get_resource_request = {
            "jsonrpc": "2.0",
            "id": "test-resource-get",
            "method": "resources/get",
            "params": {
                "id": resource_id
            }
        }
        
        get_resource_response = transport.send_request(get_resource_request)
        log(f"Get resource response: {json.dumps(get_resource_response, indent=2)}")
        
        # Final Test: Shutdown
        log("\nFinal Test: Shutdown")
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "test-shutdown",
            "method": "shutdown",
            "params": {}
        }
        
        shutdown_response = transport.send_request(shutdown_request)
        log(f"Shutdown response: {json.dumps(shutdown_response, indent=2)}")
        
        # Send exit notification
        log("Sending exit notification")
        transport.send_notification({
            "jsonrpc": "2.0",
            "method": "exit"
        })
        
        # Wait a moment for the server to exit
        time.sleep(1.0)
        
        # Check if server exited
        exit_code = transport.get_exit_code()
        log(f"Server exited with code: {exit_code}")
        
        log("\nAll tests completed!")
        return 0
        
    except Exception as e:
        import traceback
        log(f"Test failed with exception: {e}")
        log(traceback.format_exc())
        return 1
    finally:
        # Always stop the transport
        transport.stop()

if __name__ == "__main__":
    sys.exit(main()) 