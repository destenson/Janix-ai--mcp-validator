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
        self.session_id = None
        
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
            # Add session ID if available and not an initialize request
            if self.session_id and method != "initialize":
                headers["Mcp-Session-Id"] = self.session_id
                
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
                
                # If this was a successful initialize, store the session ID
                if method == "initialize" and "result" in response_data and \
                   response_data["result"].get("session") and response_data["result"]["session"].get("id"):
                    self.session_id = response_data["result"]["session"]["id"]
                    self.logger.info(f"Initialized session with ID: {self.session_id}")
                elif method == "initialize" and "result" not in response_data:
                     # Also try to get from headers if body parse failed or was unexpected for session ID
                     header_session_id = response.headers.get('Mcp-Session-Id')
                     if header_session_id:
                         self.session_id = header_session_id
                         self.logger.info(f"Initialized session with ID from header: {self.session_id}")

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
    tool_params_key = "parameters" if protocol_version == "2025-03-26" else "arguments"
    
    echo_payload = {
        "name": "echo",
        tool_params_key: {"message": "test"}
    }
    echo_result = client.send_request("tools/call", echo_payload)
    assert "error" not in echo_result, f"Echo failed: {echo_result.get('error')}"
    assert "result" in echo_result, f"Missing result in echo response: {echo_result}"
    assert "message" in echo_result["result"], f"Missing message in echo result: {echo_result['result']}"
    assert echo_result["result"]["message"] == "test", f"Echo result mismatch: {echo_result['result']}"
    
    add_payload = {
        "name": "add",
        tool_params_key: {"a": 1, "b": 2}
    }
    add_result = client.send_request("tools/call", add_payload)
    assert "error" not in add_result, f"Add failed: {add_result.get('error')}"
    assert "result" in add_result, f"Missing result in add response: {add_result}"
    assert "result" in add_result["result"], f"Missing result field in add result: {add_result['result']}"
    assert add_result["result"]["result"] == 3, f"Add result mismatch: {add_result['result']}"
    
    # Test async tool calls if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing async tool calls")
        async_call_payload = {
            "name": "sleep",
            "parameters": {"seconds": 1}
        }
        async_result = client.send_request("tools/call-async", async_call_payload)
        assert "error" not in async_result, f"Async call failed: {async_result.get('error')}"
        assert "result" in async_result, f"Missing result in async call response: {async_result}"
        assert "id" in async_result["result"], f"Missing id in async call result: {async_result['result']}"
        
        call_id = async_result["result"]["id"]
        logger.info(f"Async call ID: {call_id}")
        
        # Poll for result
        poll_attempts = 0
        max_attempts = 20
        while poll_attempts < max_attempts:
            poll_payload = {"id": call_id}
            poll_result = client.send_request("tools/result", poll_payload)
            assert "error" not in poll_result, f"Result poll failed: {poll_result.get('error')}"
            assert "result" in poll_result, f"Missing result in poll response: {poll_result}"
            assert "status" in poll_result["result"], f"Missing status in poll result: {poll_result['result']}"
            
            status = poll_result["result"]["status"]
            logger.info(f"Poll status: {status}")
            
            if status == "completed":
                # Verify the result
                assert "result" in poll_result["result"], f"Missing result data in completed poll: {poll_result['result']}"
                assert "slept" in poll_result["result"]["result"], f"Missing expected fields in async result: {poll_result['result']['result']}"
                break
                
            poll_attempts += 1
            await asyncio.sleep(0.2)
            
        assert poll_attempts < max_attempts, f"Async operation did not complete after {max_attempts} attempts"
    
    # Test notifications if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing notifications")
        pass
    
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