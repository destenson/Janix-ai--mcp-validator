#!/usr/bin/env python3
"""
Basic interaction script for testing MCP servers.
This script initializes a connection with an MCP server and allows you to list available tools.
"""

import argparse
import logging
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mcp_testing.transports.stdio import StdioTransportAdapter

def main():
    parser = argparse.ArgumentParser(description="Test basic interaction with an MCP server")
    parser.add_argument("--server-command", required=True, help="Command to start the server")
    parser.add_argument("--protocol-version", default="2025-03-26", help="Protocol version to use")
    parser.add_argument("--list-allowed-dirs", action="store_true", help="Call list_allowed_directories tool if available")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")
    logger = logging.getLogger(__name__)

    # Create environment variables
    env_vars = os.environ.copy()
    env_vars["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    # Create the transport adapter
    transport = StdioTransportAdapter(args.server_command, env_vars=env_vars, debug=args.debug)
    
    try:
        # Start the server
        logger.info("Starting server...")
        if not transport.start():
            logger.error("Failed to start server")
            return 1
        
        # Initialize the server
        logger.info("Initializing server...")
        init_request = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": args.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "MCPTestingFramework", "version": "1.0.0"}
            }
        }
        
        init_result = transport.send_request(init_request)
        logger.info("Initialization result:")
        logger.info(json.dumps(init_result, indent=2))
        
        # Send initialized notification
        logger.info("Sending initialized notification...")
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        transport.send_notification(init_notification)
        
        # List tools
        logger.info("\nListing available tools...")
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": "tools_list",
                "method": "tools/list",
                "params": {}
            }
            tools_response = transport.send_request(tools_request)
            
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                logger.info(f"Server has {len(tools)} tools:")
                for i, tool in enumerate(tools, 1):
                    logger.info(f"{i}. {tool['name']}: {tool['description']}")
            else:
                logger.info("No tools found or unexpected response format.")
                logger.info(json.dumps(tools_response, indent=2))
        except Exception as e:
            logger.error(f"Error listing tools: {e}")

        # Try to list allowed directories if requested
        if args.list_allowed_dirs:
            logger.info("\nTrying to list allowed directories...")
            try:
                allowed_dirs_request = {
                    "jsonrpc": "2.0",
                    "id": "tool_call",
                    "method": "tools/call",
                    "params": {
                        "name": "list_allowed_directories",
                        "arguments": {}
                    }
                }
                allowed_dirs_response = transport.send_request(allowed_dirs_request)
                logger.info("Allowed directories response:")
                logger.info(json.dumps(allowed_dirs_response, indent=2))
            except Exception as e:
                logger.error(f"Error listing allowed directories: {e}")
                
        # Try a list_directory tool call
        logger.info("\nTrying to list the Desktop directory...")
        try:
            list_dir_request = {
                "jsonrpc": "2.0",
                "id": "list_dir_call",
                "method": "tools/call",
                "params": {
                    "name": "list_directory",
                    "arguments": {
                        "path": "/Users/scott/Desktop"
                    }
                }
            }
            list_dir_response = transport.send_request(list_dir_request)
            logger.info("Directory listing response:")
            logger.info(json.dumps(list_dir_response, indent=2))
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
                
    except Exception as e:
        logger.error(f"Error during interaction: {e}")
        return 1
    finally:
        # Try shutdown (might not be supported)
        try:
            logger.info("\nSending shutdown request...")
            shutdown_request = {
                "jsonrpc": "2.0",
                "id": "shutdown",
                "method": "shutdown", 
                "params": {}
            }
            shutdown_response = transport.send_request(shutdown_request)
            logger.info(f"Shutdown response: {json.dumps(shutdown_response, indent=2)}")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        # Stop the transport
        transport.stop()
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 