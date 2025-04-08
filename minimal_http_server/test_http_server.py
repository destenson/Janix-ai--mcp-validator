#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test script for the Minimal HTTP MCP Server.

This script sends a series of test requests to the HTTP server to verify its functionality.
"""

import argparse
import asyncio
import json
import logging
import requests
import sys
import time
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('HTTPServerTest')

class MCPHTTPClient:
    """Simple HTTP client for testing the MCP server."""

    def __init__(self, server_url: str, debug: bool = False):
        """
        Initialize the client.
        
        Args:
            server_url: The URL of the MCP server
            debug: Whether to enable debug logging
        """
        self.server_url = server_url
        self.request_id = 0
        self.protocol_version = None
        self.initialized = False
        
        # Set up logging
        self.logger = logger
        if debug:
            self.logger.setLevel(logging.DEBUG)
    
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server.
        
        Args:
            method: The method name
            params: The method parameters
            
        Returns:
            The response from the server
        """
        # Generate request ID
        self.request_id += 1
        current_id = self.request_id
        
        # Build request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": current_id
        }
        
        if params:
            request["params"] = params
        
        # Log the request
        self.logger.debug(f">> Request: {json.dumps(request)}")
        
        try:
            # Send the request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            self.logger.debug(f">> Headers: {headers}")
            self.logger.debug(f">> URL: {self.server_url}")
            
            response = requests.post(self.server_url, json=request, headers=headers)
            
            # Log the response
            self.logger.debug(f"<< Response ({response.status_code}): {response.text}")
            self.logger.debug(f"<< Response Headers: {dict(response.headers)}")
            
            # Parse and return the response
            if response.status_code == 200:
                response_data = response.json()
                if "error" in response_data:
                    self.logger.error(f"Error: {response_data['error']}")
                return response_data
            else:
                self.logger.error(f"HTTP Error: {response.status_code} - {response.text}")
                return {"error": {"code": response.status_code, "message": response.text}}
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return {"error": {"code": -1, "message": f"Request failed: {str(e)}"}}
    
    def send_notification(self, method: str, params: Dict[str, Any] = None) -> None:
        """
        Send a JSON-RPC notification to the server.
        
        Args:
            method: The method name
            params: The method parameters
        """
        # Build notification
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params:
            notification["params"] = params
        
        # Log the notification
        self.logger.debug(f">> Notification: {json.dumps(notification)}")
        
        try:
            # Send the notification
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.server_url, json=notification, headers=headers)
            
            # Log the response
            self.logger.debug(f"<< Response ({response.status_code}): {response.text}")
        except requests.RequestException as e:
            self.logger.error(f"Notification failed: {str(e)}")
    
    def initialize(self, protocol_version: str = "2025-03-26") -> Dict[str, Any]:
        """
        Initialize the connection to the server.
        
        Args:
            protocol_version: The protocol version to use
            
        Returns:
            The initialization result
        """
        # Build initialization params
        params = {
            "protocolVersion": protocol_version,
            "clientInfo": {
                "name": "MCP HTTP Test Client",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": True
            }
        }
        
        # If using 2025-03-26, add specific capabilities
        if protocol_version == "2025-03-26":
            params["capabilities"]["tools"] = {
                "asyncSupported": True
            }
            params["capabilities"]["resources"] = True
        
        # Send initialization request
        response = self.send_request("initialize", params)
        
        # Check for errors
        if "error" in response:
            self.logger.error(f"Initialization failed: {response['error']}")
            return response
        
        # Update client state
        self.protocol_version = protocol_version
        self.initialized = True
        
        return response.get("result", {})
    
    def shutdown(self) -> Dict[str, Any]:
        """
        Send a shutdown request to the server.
        
        Returns:
            The shutdown result
        """
        if not self.initialized:
            self.logger.warning("Client not initialized, cannot shutdown")
            return {"error": {"message": "Client not initialized"}}
        
        # Send shutdown request
        response = self.send_request("shutdown")
        
        # Check for errors
        if "error" in response:
            self.logger.error(f"Shutdown failed: {response['error']}")
        else:
            self.initialized = False
        
        return response.get("result", {})


async def run_tests(server_url: str, protocol_version: str, debug: bool = False):
    """
    Run tests against the MCP HTTP server.
    
    Args:
        server_url: The URL of the MCP server
        protocol_version: The protocol version to use
        debug: Whether to enable debug logging
    """
    client = MCPHTTPClient(server_url, debug)
    available_tools = []
    
    # 1. Test initialization
    logger.info("\n=== Test: Initialization ===")
    init_result = client.initialize(protocol_version)
    logger.info(f"Server initialized with protocol version: {protocol_version}")
    logger.info(f"Server info: {init_result.get('serverInfo', {})}")
    logger.info(f"Server capabilities: {init_result.get('capabilities', {})}")
    
    # 2. Test server info
    logger.info("\n=== Test: Server Info ===")
    server_info = client.send_request("server/info")
    if "result" in server_info:
        logger.info(f"Server info: {server_info['result']}")
    
    # 3. Test tools listing
    logger.info("\n=== Test: Tools Listing ===")
    tools_method = "tools/list"
    if protocol_version == "2024-11-05":
        tools_method = "mcp/tools"
    
    tools_response = client.send_request(tools_method)
    if "result" in tools_response and "tools" in tools_response["result"]:
        tools = tools_response["result"]["tools"]
        logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        
        # Save tools for later use
        available_tools = tools
    
    # 4. Test direct tool calls
    logger.info("\n=== Test: Direct Tool Calls ===")
    if available_tools and "echo" in [tool["name"] for tool in available_tools]:
        echo_response = client.send_request("echo", {"message": "Hello, MCP HTTP Server!"})
        if "result" in echo_response:
            logger.info(f"Echo response: {echo_response['result']}")
    
    if available_tools and "add" in [tool["name"] for tool in available_tools]:
        add_response = client.send_request("add", {"a": 5, "b": 7})
        if "result" in add_response:
            logger.info(f"Add response: {add_response['result']}")
    
    # 5. Test tools/call method
    logger.info("\n=== Test: Tools/Call Method ===")
    tools_call_method = "tools/call"
    if protocol_version == "2024-11-05":
        tools_call_method = "mcp/tools/call"
    
    params_key = "parameters" if protocol_version == "2025-03-26" else "arguments"
    tools_call_params = {
        "name": "echo",
        params_key: {"message": "Hello via tools/call!"}
    }
    
    tools_call_response = client.send_request(tools_call_method, tools_call_params)
    if "result" in tools_call_response:
        logger.info(f"Tools/call response: {tools_call_response['result']}")
    
    # 6. Test async tool calls (only for 2025-03-26)
    if protocol_version == "2025-03-26":
        logger.info("\n=== Test: Async Tool Calls ===")
        
        # 6.1 Start async call
        async_call_params = {
            "name": "sleep",
            "parameters": {"seconds": 2}
        }
        
        async_call_response = client.send_request("tools/call-async", async_call_params)
        if "result" in async_call_response and "id" in async_call_response["result"]:
            async_id = async_call_response["result"]["id"]
            logger.info(f"Async call started with ID: {async_id}")
            
            # 6.2 Poll for result (would normally be in a loop)
            logger.info("Waiting for async result...")
            time.sleep(1)  # Wait a bit, but less than the sleep time
            
            result_params = {"id": async_id}
            result_response = client.send_request("tools/result", result_params)
            if "result" in result_response:
                logger.info(f"Partial result (should be running): {result_response['result']}")
            
            # Wait for completion
            time.sleep(2)  # Wait a bit longer to ensure completion
            
            final_result_response = client.send_request("tools/result", result_params)
            if "result" in final_result_response:
                logger.info(f"Final result: {final_result_response['result']}")
            
            # 6.3 Test cancellation with a new async call
            logger.info("\n=== Test: Async Cancellation ===")
            
            # Start a new async call with longer sleep
            cancel_call_params = {
                "name": "sleep",
                "parameters": {"seconds": 5}
            }
            
            cancel_call_response = client.send_request("tools/call-async", cancel_call_params)
            if "result" in cancel_call_response and "id" in cancel_call_response["result"]:
                cancel_id = cancel_call_response["result"]["id"]
                logger.info(f"Async call started with ID: {cancel_id}")
                
                # Wait a bit then cancel
                time.sleep(1)
                
                cancel_params = {"id": cancel_id}
                cancel_response = client.send_request("tools/cancel", cancel_params)
                if "result" in cancel_response:
                    logger.info(f"Cancellation result: {cancel_response['result']}")
                
                # Check final status
                time.sleep(1)
                
                status_response = client.send_request("tools/result", {"id": cancel_id})
                if "result" in status_response:
                    logger.info(f"Status after cancellation: {status_response['result']}")
    
    # 7. Test resources (only for 2025-03-26)
    if protocol_version == "2025-03-26":
        logger.info("\n=== Test: Resources ===")
        
        # 7.1 List resources
        resources_response = client.send_request("resources/list")
        resources = []
        if "result" in resources_response and "resources" in resources_response["result"]:
            resources = resources_response["result"]["resources"]
            logger.info(f"Available resources: {[res['id'] for res in resources]}")
            
        # 7.2 Get a specific resource
        if resources:
            resource_id = resources[0]["id"]
            resource_response = client.send_request("resources/get", {"id": resource_id})
            if "result" in resource_response:
                logger.info(f"Resource details: {resource_response['result']}")
    
    # 8. Test batch requests
    logger.info("\n=== Test: Batch Requests ===")
    batch_requests = [
        {"jsonrpc": "2.0", "method": "server/info", "id": 100},
        {"jsonrpc": "2.0", "method": "echo", "params": {"message": "Batch message"}, "id": 101}
    ]
    
    # Send batch request
    logger.info("Sending batch request...")
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(server_url, json=batch_requests, headers=headers)
        
        if response.status_code == 200:
            batch_responses = response.json()
            logger.info(f"Received {len(batch_responses)} responses in batch")
            for resp in batch_responses:
                logger.info(f"Batch response ID {resp.get('id')}: {resp.get('result')}")
        else:
            logger.error(f"Batch request failed: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        logger.error(f"Batch request failed: {str(e)}")
    
    # 9. Test notifications
    logger.info("\n=== Test: Notifications ===")
    client.send_notification("echo", {"message": "This is a notification"})
    logger.info("Notification sent (no response expected)")
    
    # 10. Test error handling
    logger.info("\n=== Test: Error Handling ===")
    
    # Invalid method
    invalid_method_response = client.send_request("invalid_method")
    if "error" in invalid_method_response:
        logger.info(f"Invalid method error: {invalid_method_response['error']}")
    
    # Invalid parameters
    if available_tools and "add" in [tool["name"] for tool in available_tools]:
        invalid_params_response = client.send_request("add", {"a": "not_a_number", "b": 5})
        if "error" in invalid_params_response:
            logger.info(f"Invalid parameters error: {invalid_params_response['error']}")
    
    # 11. Test shutdown
    logger.info("\n=== Test: Shutdown ===")
    shutdown_result = client.shutdown()
    logger.info("Server shutdown requested")
    
    logger.info("\n=== All tests completed ===")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test script for MCP HTTP Server"
    )
    parser.add_argument(
        "--url", 
        default="http://localhost:8000/mcp",
        help="URL of the MCP HTTP server (default: http://localhost:8000/mcp)"
    )
    parser.add_argument(
        "--protocol-version", 
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="Protocol version to use (default: 2025-03-26)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Run tests
    asyncio.run(run_tests(args.url, args.protocol_version, args.debug))


if __name__ == "__main__":
    main() 