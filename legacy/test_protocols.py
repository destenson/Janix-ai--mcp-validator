#!/usr/bin/env python3

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.

"""
Test script for validating the protocol adapters.

This script provides a simple way to test the protocol adapters with
different transports and server types.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import from the packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from protocols import get_protocol_adapter
from transport.http_client import HTTPTransport
from transport.stdio_client import STDIOTransport
from transport.docker_client import DockerSTDIOTransport


async def test_protocol_adapter(
    transport_type: str,
    protocol_version: str,
    url: Optional[str] = None,
    server_command: Optional[str] = None,
    docker_image: Optional[str] = None,
    mount_path: Optional[str] = None,
    container_path: Optional[str] = None,
    network_name: Optional[str] = None,
    debug: bool = False
) -> bool:
    """
    Test a protocol adapter with the specified transport.
    
    Args:
        transport_type: The type of transport to use (http, stdio, docker)
        protocol_version: The protocol version to use
        url: The URL of the server (for HTTP transport)
        server_command: The command to start the server (for STDIO transport)
        docker_image: The Docker image to use (for Docker transport)
        mount_path: The local path to mount (for Docker transport)
        container_path: The path in the container to mount to (for Docker transport)
        network_name: The Docker network to use (for Docker transport)
        debug: Whether to enable debug output
        
    Returns:
        True if the test passed, False otherwise
    """
    transport = None
    
    try:
        # Create the appropriate transport
        if transport_type == "http":
            if not url:
                print("Error: URL is required for HTTP transport")
                return False
            
            transport = HTTPTransport(url, debug=debug)
        elif transport_type == "stdio":
            if not server_command:
                print("Error: Server command is required for STDIO transport")
                return False
            
            transport = STDIOTransport(command=server_command, debug=debug)
        elif transport_type == "docker":
            if not docker_image:
                print("Error: Docker image is required for Docker transport")
                return False
            
            if not mount_path:
                # Use the test data directory as the default mount path
                test_data_dir = Path(__file__).parent.parent / "test_data" / "files"
                if test_data_dir.exists():
                    mount_path = str(test_data_dir)
                else:
                    print("Error: Mount path is required for Docker transport")
                    return False
            
            if not container_path:
                container_path = "/projects"
            
            transport = DockerSTDIOTransport(
                docker_image=docker_image,
                mount_path=mount_path,
                container_path=container_path,
                network_name=network_name,
                protocol_version=protocol_version,
                debug=debug
            )
        else:
            print(f"Error: Unknown transport type: {transport_type}")
            return False
        
        # Create the protocol adapter
        adapter = get_protocol_adapter(protocol_version, transport, debug=debug)
        
        # Initialize the connection
        print(f"Initializing connection with server using {protocol_version}...")
        response = await adapter.initialize()
        
        print(f"Server supports protocol version: {adapter.protocol_version}")
        print(f"Server info: {json.dumps(adapter.server_info, indent=2)}")
        print(f"Server capabilities: {json.dumps(adapter.server_capabilities, indent=2)}")
        
        # Send the initialized notification
        print("Sending initialized notification...")
        await adapter.send_initialized()
        
        # Get the tools list
        print("Getting tools list...")
        tools = await adapter.get_tools_list()
        
        print(f"Server supports {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
        
        # If the server supports the list_allowed_directories tool, invoke it
        tool_found = False
        for tool in tools:
            if tool["name"] == "list_allowed_directories":
                tool_found = True
                print("\nTesting list_allowed_directories tool...")
                result = await adapter.invoke_tool("list_allowed_directories", {})
                print(f"Allowed directories: {json.dumps(result, indent=2)}")
                break
        
        if not tool_found:
            print("\nCould not find list_allowed_directories tool to test, but that's okay")
        
        # Clean up
        print("\nShutting down...")
        await adapter.shutdown()
        print("Sending exit notification...")
        await adapter.exit()
        
        print("Test completed successfully!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Make sure we stop the transport
        if transport:
            transport.stop()


async def main():
    parser = argparse.ArgumentParser(description="Test protocol adapters with different transports")
    parser.add_argument("--transport", choices=["http", "stdio", "docker"], required=True,
                        help="The transport type to use")
    parser.add_argument("--protocol-version", required=True,
                        help="The protocol version to use")
    parser.add_argument("--url", help="The URL of the server (for HTTP transport)")
    parser.add_argument("--server-command", help="The command to start the server (for STDIO transport)")
    parser.add_argument("--docker-image", help="The Docker image to use (for Docker transport)")
    parser.add_argument("--mount-path", help="The local path to mount (for Docker transport)")
    parser.add_argument("--container-path", help="The path in the container to mount to (for Docker transport)")
    parser.add_argument("--network-name", help="The Docker network to use (for Docker transport)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    success = await test_protocol_adapter(
        transport_type=args.transport,
        protocol_version=args.protocol_version,
        url=args.url,
        server_command=args.server_command,
        docker_image=args.docker_image,
        mount_path=args.mount_path,
        container_path=args.container_path,
        network_name=args.network_name,
        debug=args.debug
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 