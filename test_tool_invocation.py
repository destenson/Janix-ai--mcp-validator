#!/usr/bin/env python3
"""
Test tool invocation patterns for MCP servers.

This script attempts to invoke tools using different naming formats to identify
which format a server expects. It helps diagnose non-compliant MCP servers.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from transport.stdio_client import STDIOTransport
from transport.docker_client import DockerSTDIOTransport

REQUEST_ID = 1000

def print_tool_details(tools: List[Dict[str, Any]]) -> None:
    """Print the list of available tools."""
    print(f"\nServer supports {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description'][:100]}...")

def try_invoke_with_format(transport, tool_name: str, format_template: str, params: Dict[str, Any] = {}) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Try to invoke a tool with the given format template.
    
    Args:
        transport: Transport layer to use for communication
        tool_name: Name of the tool to invoke
        format_template: Format string for the method name (e.g., "{}", "tools/{}")
        params: Parameters to pass to the tool
        
    Returns:
        Tuple of (success, response)
    """
    global REQUEST_ID
    REQUEST_ID += 1
    
    method = format_template.format(tool_name)
    request_id = f"invoke_{REQUEST_ID}"
    
    print(f"\nTrying format '{method}':")
    
    try:
        response = transport.send_request(method, params, request_id)
        print(f"Response: {json.dumps(response)}")
        
        if "error" in response:
            return False, response
        return True, response
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, None

def test_tool_invocation_patterns(transport, tool_name: str, params: Dict[str, Any] = {}) -> None:
    """
    Test different patterns for tool invocation.
    
    Args:
        transport: Transport layer to use for communication
        tool_name: Name of the tool to invoke
        params: Parameters to pass to the tool
    """
    formats = [
        "{}",                    # Direct tool name (MCP spec compliant)
        "tools/{}",              # Tools namespace
        "filesystem/{}",         # Filesystem namespace
        "fs/{}",                 # Short filesystem namespace
        "tool/{}",               # Singular tool namespace
        "mcp/{}",                # MCP namespace
        "{}/invoke",             # Tool with invoke suffix
        "invoke/{}",             # Invoke prefix
    ]
    
    success = False
    for fmt in formats:
        ok, response = try_invoke_with_format(transport, tool_name, fmt, params)
        if ok:
            print(f"\n✅ SUCCESS: Format '{fmt.format(tool_name)}' works!")
            success = True
            break
    
    if not success:
        print("\n❌ All invocation formats failed.")

def initialize_server(transport, protocol_version: str) -> bool:
    """Initialize the server and return whether it was successful."""
    init_params = {
        "protocolVersion": protocol_version,
        "capabilities": {},
        "clientInfo": {"name": "MCPProtocolValidator", "version": "1.0.0"}
    }
    
    print(f"Initializing connection with server using {protocol_version}...")
    try:
        # Send initialize request
        response = transport.send_request("initialize", init_params, "init")
        print(f"Received initialize response: {json.dumps(response, indent=2)}")
        
        if "result" not in response:
            print(f"Error initializing server: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
            
        server_version = response["result"]["protocolVersion"]
        if server_version != protocol_version:
            print(f"Warning: Server supports {server_version}, requested {protocol_version}")
        
        server_info = response["result"].get("serverInfo", {})
        print(f"Server info: {json.dumps(server_info, indent=2)}")
        
        capabilities = response["result"].get("capabilities", {})
        print(f"Server capabilities: {json.dumps(capabilities, indent=2)}")
        
        # Send initialized notification
        print("Sending initialized notification...")
        transport.send_notification("initialized", {})
        
        return True
    except Exception as e:
        print(f"Error during initialization: {str(e)}")
        return False

def get_tools_list(transport) -> Optional[List[Dict[str, Any]]]:
    """Get the list of tools from the server."""
    print("Getting tools list...")
    try:
        response = transport.send_request("tools/list", {}, "tools_list")
        print(f"Received response: {json.dumps(response, indent=2)}")
        
        if "result" not in response or "tools" not in response["result"]:
            print(f"Error getting tools list: {response.get('error', {}).get('message', 'Unknown error')}")
            return None
            
        tools = response["result"]["tools"]
        print_tool_details(tools)
        return tools
    except Exception as e:
        print(f"Error getting tools list: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test tool invocation patterns for MCP servers')
    parser.add_argument('--transport', choices=['http', 'stdio', 'docker'], required=True,
                        help='Transport type to use')
    parser.add_argument('--protocol-version', default='2024-11-05',
                        help='Protocol version to use for the test')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--docker-image', help='Docker image to use (required for docker transport)')
    parser.add_argument('--network-name', default='mcp-test-network',
                        help='Docker network name (for docker transport)')
    parser.add_argument('--tool', default='list_allowed_directories',
                        help='Tool name to test invocation formats for')
    parser.add_argument('--params', default='{}',
                        help='JSON string of parameters to pass to the tool')
    
    args = parser.parse_args()
    
    if args.transport == 'docker' and not args.docker_image:
        parser.error("--docker-image is required when using docker transport")
    
    transport = None
    
    try:
        if args.transport == 'docker':
            transport = DockerSTDIOTransport(
                docker_image=args.docker_image,
                mount_path=os.path.expanduser("~/AI/PROTOCOL_STRATEGY/mcp/tools/test_data/files"),
                container_path="/projects",
                network_name=args.network_name,
                protocol_version=args.protocol_version,
                debug=args.debug
            )
        else:
            parser.error(f"Transport type {args.transport} not implemented in this test script")
        
        # Start the transport
        if not transport.start():
            print(f"Failed to start {args.transport} transport")
            return 1
        
        # Initialize the server
        if not initialize_server(transport, args.protocol_version):
            return 1
        
        # Get tools list
        tools = get_tools_list(transport)
        if not tools:
            return 1
        
        # Find the target tool
        target_tool = next((t for t in tools if t["name"] == args.tool), None)
        if not target_tool:
            print(f"Tool '{args.tool}' not found in the server's tool list")
            return 1
        
        # Parse params
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            print(f"Error parsing params JSON: {args.params}")
            return 1
        
        # Test tool invocation patterns
        test_tool_invocation_patterns(transport, args.tool, params)
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    finally:
        if transport:
            transport.stop()

if __name__ == "__main__":
    sys.exit(main()) 