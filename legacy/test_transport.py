#!/usr/bin/env python3

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.

"""
Test script for MCP Protocol Validator transport layer.

This script demonstrates how to use the different transport implementations
to connect to and communicate with MCP servers.
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, List, Optional

# Import transport implementations
from transport import MCPTransport, HTTPTransport, STDIOTransport, DockerSTDIOTransport


def test_http_transport(url: str, debug: bool = False) -> bool:
    """
    Test the HTTP transport implementation.
    
    Args:
        url: The URL of the HTTP server
        debug: Whether to enable debug output
        
    Returns:
        True if the test was successful, False otherwise
    """
    print(f"\n=== Testing HTTP Transport with URL: {url} ===\n")
    
    # Create the transport
    transport = HTTPTransport(url=url, debug=debug)
    
    try:
        # Start the transport
        if not transport.start():
            print("Failed to start HTTP transport")
            return False
            
        # Initialize the server
        print("Initializing server...")
        init_response = transport.initialize(
            protocol_version="2025-03-26",
            client_info={
                "name": "TransportTest",
                "version": "1.0.0"
            },
            capabilities={}
        )
        
        print(f"Initialization response: {json.dumps(init_response, indent=2)}")
        
        # Get tools list
        print("\nGetting tools list...")
        tools = transport.get_tools_list()
        
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f" - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            
        # Test successful
        print("\nHTTP transport test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during HTTP transport test: {str(e)}")
        return False
        
    finally:
        # Stop the transport
        transport.stop()


def test_stdio_transport(command: str, debug: bool = False) -> bool:
    """
    Test the STDIO transport implementation.
    
    Args:
        command: The command to start the server
        debug: Whether to enable debug output
        
    Returns:
        True if the test was successful, False otherwise
    """
    print(f"\n=== Testing STDIO Transport with command: {command} ===\n")
    
    # Create the transport
    transport = STDIOTransport(command=command, debug=debug)
    
    try:
        # Start the transport
        if not transport.start():
            print("Failed to start STDIO transport")
            return False
            
        # Initialize the server
        print("Initializing server...")
        init_response = transport.initialize(
            protocol_version="2025-03-26",
            client_info={
                "name": "TransportTest",
                "version": "1.0.0"
            },
            capabilities={}
        )
        
        print(f"Initialization response: {json.dumps(init_response, indent=2)}")
        
        # Get tools list
        print("\nGetting tools list...")
        tools = transport.get_tools_list()
        
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f" - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            
        # Test successful
        print("\nSTDIO transport test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during STDIO transport test: {str(e)}")
        return False
        
    finally:
        # Stop the transport
        transport.stop()


def test_docker_transport(docker_image: str, mount_path: str, debug: bool = False) -> bool:
    """
    Test the Docker STDIO transport implementation.
    
    Args:
        docker_image: The Docker image to run
        mount_path: The path to mount in the container
        debug: Whether to enable debug output
        
    Returns:
        True if the test was successful, False otherwise
    """
    print(f"\n=== Testing Docker STDIO Transport with image: {docker_image} ===\n")
    
    # Create the transport
    transport = DockerSTDIOTransport(
        docker_image=docker_image,
        mount_path=mount_path,
        protocol_version="2025-03-26",
        debug=debug
    )
    
    try:
        # Start the transport
        if not transport.start():
            print("Failed to start Docker STDIO transport")
            return False
            
        # Initialize the server
        print("Initializing server...")
        init_response = transport.initialize(
            protocol_version="2025-03-26",
            client_info={
                "name": "TransportTest",
                "version": "1.0.0"
            },
            capabilities={}
        )
        
        print(f"Initialization response: {json.dumps(init_response, indent=2)}")
        
        # Get tools list
        print("\nGetting tools list...")
        tools = transport.get_tools_list()
        
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f" - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            
        # Test successful
        print("\nDocker STDIO transport test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during Docker STDIO transport test: {str(e)}")
        return False
        
    finally:
        # Stop the transport
        transport.stop()


def main():
    """Main function to run the transport tests."""
    parser = argparse.ArgumentParser(description="Test MCP Protocol Validator transport layer")
    parser.add_argument("--transport", choices=["http", "stdio", "docker"], required=True,
                       help="Transport type to test")
    parser.add_argument("--url", help="URL for HTTP transport")
    parser.add_argument("--command", help="Command for STDIO transport")
    parser.add_argument("--docker-image", default="mcp/filesystem",
                       help="Docker image for Docker transport")
    parser.add_argument("--mount-path", default="../test_data/files",
                       help="Path to mount in Docker container")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Run the appropriate test based on transport type
    if args.transport == "http":
        if not args.url:
            parser.error("--url is required for HTTP transport")
        success = test_http_transport(args.url, args.debug)
    elif args.transport == "stdio":
        if not args.command:
            parser.error("--command is required for STDIO transport")
        success = test_stdio_transport(args.command, args.debug)
    elif args.transport == "docker":
        success = test_docker_transport(args.docker_image, args.mount_path, args.debug)
    
    # Exit with appropriate status
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 