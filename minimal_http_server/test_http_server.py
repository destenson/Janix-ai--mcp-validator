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
    """Run a comprehensive test suite against the server."""
    client = MCPHTTPClient(server_url, debug)
    
    # Test initialization
    logger.info(f"Testing initialization with protocol version {protocol_version}")
    init_result = client.initialize(protocol_version)
    assert "error" not in init_result, f"Initialization failed: {init_result.get('error')}"
    
    # Test server info
    logger.info("Testing server info")
    server_info = client.send_request("server/info")
    assert "error" not in server_info, f"Server info failed: {server_info.get('error')}"
    
    # Test tools list
    logger.info("Testing tools list")
    tools_list = client.send_request("tools/list")
    assert "error" not in tools_list, f"Tools list failed: {tools_list.get('error')}"
    assert "result" in tools_list and "tools" in tools_list["result"]
    
    # Test basic tool calls
    logger.info("Testing basic tool calls")
    echo_result = client.send_request("tools/call", {
        "name": "echo",
        "arguments": {"message": "test"}
    })
    assert "error" not in echo_result, f"Echo failed: {echo_result.get('error')}"
    assert echo_result["result"]["result"] == "test"
    
    add_result = client.send_request("tools/call", {
        "name": "add",
        "arguments": {"a": 1, "b": 2}
    })
    assert "error" not in add_result, f"Add failed: {add_result.get('error')}"
    assert add_result["result"]["result"] == 3
    
    # Test async tool calls if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing async tool calls")
        async_result = client.send_request("tools/callAsync", {
            "name": "sleep",
            "arguments": {"seconds": 1}
        })
        assert "error" not in async_result, f"Async call failed: {async_result.get('error')}"
        call_id = async_result["result"]["callId"]
        
        # Poll for result
        while True:
            poll_result = client.send_request("tools/result", {"callId": call_id})
            if "error" not in poll_result and poll_result["result"]["status"] == "completed":
                break
            await asyncio.sleep(0.1)
    
    # Test notifications if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing notifications")
        # Start SSE connection
        import requests_sse
        session = requests.Session()
        headers = {"Accept": "text/event-stream"}
        if "Mcp-Session-Id" in client.session.headers:
            headers["Mcp-Session-Id"] = client.session.headers["Mcp-Session-Id"]
        
        async with requests_sse.EventSource(
            f"{server_url}/notifications",
            headers=headers,
            session=session
        ) as event_source:
            # Send a test notification
            notify_result = client.send_request("notifications/send", {
                "message": "test notification"
            })
            assert "error" not in notify_result, f"Send notification failed: {notify_result.get('error')}"
            
            # Wait for notification
            try:
                event = await asyncio.wait_for(event_source.get(), timeout=5.0)
                assert event.data == "test notification"
            except asyncio.TimeoutError:
                assert False, "Timeout waiting for notification"
    
    # Test resources if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing resources")
        resources_list = client.send_request("resources/list")
        assert "error" not in resources_list, f"Resources list failed: {resources_list.get('error')}"
        
        if resources_list["result"]["resources"]:
            resource_id = resources_list["result"]["resources"][0]["id"]
            resource_get = client.send_request("resources/get", {"id": resource_id})
            assert "error" not in resource_get, f"Resource get failed: {resource_get.get('error')}"
    
    # Test shutdown
    logger.info("Testing shutdown")
    shutdown_result = client.shutdown()
    assert "error" not in shutdown_result, f"Shutdown failed: {shutdown_result.get('error')}"
    
    logger.info("All tests passed!")


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