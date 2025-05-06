#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test Client for MCP HTTP Server

This module provides a client for testing the MCP HTTP server.
"""

import argparse
import json
import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional, List, Union
import urllib.parse
import requests
from requests.exceptions import RequestException

# Configure logging
logger = logging.getLogger("MCPHTTPClient")

class MCPHTTPClient:
    """
    HTTP client for testing the MCP server.
    """
    
    def __init__(self, base_url: str, protocol_version: str = "2025-03-26"):
        """
        Initialize the client.
        
        Args:
            base_url: The base URL of the MCP server, e.g., "http://localhost:9000/mcp".
            protocol_version: The MCP protocol version to use.
        """
        self.base_url = base_url
        self.protocol_version = protocol_version
        self.session_id = None
        self.session = requests.Session()
        self.initialized = False
        self.request_id = 0
    
    def initialize(self, client_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize a session with the server.
        
        Args:
            client_info: Information about the client.
            
        Returns:
            Dict[str, Any]: The server's response.
            
        Raises:
            Exception: If the initialization fails.
        """
        if client_info is None:
            client_info = {
                "name": "MCP Test Client",
                "version": "1.0.0"
            }
        
        # Construct the initialization request based on protocol version
        init_params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": client_info
        }
        
        # 2025-03-26 requires capabilities
        if self.protocol_version == "2025-03-26":
            init_params["capabilities"] = {
                "protocolVersion": self.protocol_version,
                "tools": {
                    "asyncSupported": True
                }
            }
        
        # Send the request
        response = self.send_request("initialize", init_params)
        
        if "error" in response:
            raise Exception(f"Initialization failed: {response['error']}")
        
        # Extract the session ID from the response body
        if "result" in response and "session" in response["result"]:
            self.session_id = response["result"]["session"]["id"]
        else:
            # For backward compatibility, also try extracting from headers
            self.session_id = self.session.headers.get("Mcp-Session-Id")
            
        if not self.session_id:
            raise Exception("No session ID returned by server")
        
        # Set up the session for future requests
        self.session.headers.update({"Mcp-Session-Id": self.session_id})
        self.initialized = True
        
        logger.info(f"Initialized session {self.session_id} with protocol version {self.protocol_version}")
        
        return response["result"]
    
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server.
        
        Args:
            method: The method name.
            params: The method parameters.
            
        Returns:
            Dict[str, Any]: The server's response.
            
        Raises:
            RequestException: If the HTTP request fails.
        """
        if params is None:
            params = {}
        
        # Increment request ID
        self.request_id += 1
        
        # Construct the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": str(self.request_id),
            "method": method,
            "params": params
        }
        
        # Log the request
        logger.debug(f"Sending request: {json.dumps(request, indent=2)}")
        
        try:
            # Send the request
            response = self.session.post(
                self.base_url,
                json=request,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            if response.status_code == 204:  # No content
                return {}
            
            try:
                result = response.json()
                logger.debug(f"Received response: {json.dumps(result, indent=2)}")
                return result
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in response: {response.text}")
                return {"error": {"code": -32603, "message": "Invalid JSON in response"}}
        except RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": {"code": -32603, "message": f"Request failed: {str(e)}"}}
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.
        
        Returns:
            Dict[str, Any]: The server information.
        """
        response = self.send_request("server/info")
        
        if "error" in response:
            logger.error(f"Failed to get server info: {response['error']}")
            return {}
        
        return response["result"]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools.
        
        Returns:
            List[Dict[str, Any]]: The list of available tools.
        """
        response = self.send_request("tools/list")
        
        if "error" in response:
            logger.error(f"Failed to list tools: {response['error']}")
            return []
        
        return response["result"].get("tools", [])
    
    def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool.
        
        Args:
            name: The name of the tool to call.
            **kwargs: The tool arguments.
            
        Returns:
            Dict[str, Any]: The result of the tool call.
        """
        # Construct the tool call parameters based on protocol version
        if self.protocol_version == "2025-03-26":
            params = {
                "name": name,
                "parameters": kwargs
            }
        else:  # 2024-11-05
            params = {
                "name": name,
                "arguments": kwargs
            }
        
        response = self.send_request("tools/call", params)
        
        if "error" in response:
            logger.error(f"Tool call failed: {response['error']}")
            return {}
        
        return response["result"]
    
    def call_tool_async(self, name: str, **kwargs) -> str:
        """
        Call a tool asynchronously.
        
        Args:
            name: The name of the tool to call.
            **kwargs: The tool arguments.
            
        Returns:
            str: The ID of the asynchronous call.
            
        Raises:
            Exception: If the protocol version doesn't support async calls or if the call fails.
        """
        if self.protocol_version != "2025-03-26":
            raise Exception("Asynchronous tool calls are only supported in protocol version 2025-03-26")
        
        params = {
            "name": name,
            "parameters": kwargs
        }
        
        response = self.send_request("tools/call-async", params)
        
        if "error" in response:
            raise Exception(f"Async tool call failed: {response['error']}")
        
        return response["result"]["id"]
    
    def get_tool_result(self, call_id: str, max_attempts: int = 10, 
                        poll_interval: float = 0.5) -> Dict[str, Any]:
        """
        Get the result of an asynchronous tool call.
        
        Args:
            call_id: The ID of the asynchronous call.
            max_attempts: The maximum number of polling attempts.
            poll_interval: The interval between polling attempts.
            
        Returns:
            Dict[str, Any]: The result of the asynchronous tool call.
            
        Raises:
            Exception: If the protocol version doesn't support async calls,
                if the polling times out, or if the call fails.
        """
        if self.protocol_version != "2025-03-26":
            raise Exception("Asynchronous tool calls are only supported in protocol version 2025-03-26")
        
        params = {"id": call_id}
        
        for _ in range(max_attempts):
            response = self.send_request("tools/result", params)
            
            if "error" in response:
                raise Exception(f"Failed to get tool result: {response['error']}")
            
            result = response["result"]
            status = result.get("status")
            
            if status == "completed":
                return result.get("result", {})
            elif status == "error":
                raise Exception(f"Async tool call failed: {result.get('error')}")
            elif status == "cancelled":
                raise Exception("Async tool call was cancelled")
            
            # Still running, wait and try again
            time.sleep(poll_interval)
        
        raise Exception(f"Timeout waiting for async tool call result after {max_attempts} attempts")
    
    def cancel_tool(self, call_id: str) -> bool:
        """
        Cancel an asynchronous tool call.
        
        Args:
            call_id: The ID of the asynchronous call.
            
        Returns:
            bool: True if the cancellation was successful, False otherwise.
            
        Raises:
            Exception: If the protocol version doesn't support async calls.
        """
        if self.protocol_version != "2025-03-26":
            raise Exception("Asynchronous tool calls are only supported in protocol version 2025-03-26")
        
        params = {"id": call_id}
        
        response = self.send_request("tools/cancel", params)
        
        if "error" in response:
            logger.error(f"Failed to cancel tool call: {response['error']}")
            return False
        
        return response["result"].get("success", False)
    
    def close(self) -> None:
        """Close the client session."""
        if self.session_id:
            try:
                # Send a DELETE request to end the session
                response = self.session.delete(self.base_url)
                response.raise_for_status()
                logger.info(f"Closed session {self.session_id}")
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
        
        self.session.close()
        self.session_id = None
        self.initialized = False


def run_tests(client: MCPHTTPClient) -> bool:
    """
    Run a series of tests against the server.
    
    Args:
        client: The MCP HTTP client.
        
    Returns:
        bool: True if all tests passed, False otherwise.
    """
    success = True
    
    try:
        # Test initialization
        logger.info("Testing initialization...")
        client.initialize()
        
        # Test server info
        logger.info("Testing server info...")
        server_info = client.get_server_info()
        logger.info(f"Server info: {server_info}")
        
        # Test tools list
        logger.info("Testing tools list...")
        tools = client.list_tools()
        logger.info(f"Found {len(tools)} tools")
        
        # Test echo tool
        logger.info("Testing echo tool...")
        echo_result = client.call_tool("echo", message="Hello, MCP!")
        logger.info(f"Echo result: {echo_result}")
        if echo_result.get("message") != "Hello, MCP!":
            logger.error("Echo test failed")
            success = False
        
        # Test add tool
        logger.info("Testing add tool...")
        add_result = client.call_tool("add", a=5, b=7)
        logger.info(f"Add result: {add_result}")
        if add_result.get("result") != 12:
            logger.error("Add test failed")
            success = False
        
        # Test sleep tool
        logger.info("Testing sleep tool...")
        sleep_result = client.call_tool("sleep", seconds=1)
        logger.info(f"Sleep result: {sleep_result}")
        
        # Test async tools if protocol version is 2025-03-26
        if client.protocol_version == "2025-03-26":
            logger.info("Testing async tool calls...")
            
            # Test async sleep
            logger.info("Testing async sleep...")
            call_id = client.call_tool_async("sleep", seconds=2)
            logger.info(f"Async call ID: {call_id}")
            
            # Wait for result
            start_time = time.time()
            result = client.get_tool_result(call_id)
            elapsed = time.time() - start_time
            
            logger.info(f"Async sleep result: {result}, took {elapsed:.2f}s")
            
            # Test cancellation (with a longer sleep)
            logger.info("Testing async cancellation...")
            call_id = client.call_tool_async("sleep", seconds=10)
            logger.info(f"Async call ID: {call_id}")
            
            # Wait a bit, then cancel
            time.sleep(0.5)
            cancel_result = client.cancel_tool(call_id)
            logger.info(f"Cancel result: {cancel_result}")
            
            if not cancel_result:
                logger.error("Cancel test failed")
                success = False
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        success = False
    
    return success


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP HTTP Client")
    parser.add_argument(
        "--url", 
        type=str, 
        default="http://localhost:9000/mcp",
        help="The URL of the MCP server"
    )
    parser.add_argument(
        "--protocol-version", 
        type=str, 
        default="2025-03-26",
        choices=["2024-11-05", "2025-03-26"],
        help="The MCP protocol version to use"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run the client
    client = MCPHTTPClient(args.url, args.protocol_version)
    
    try:
        success = run_tests(client)
        
        if success:
            logger.info("All tests passed")
            sys.exit(0)
        else:
            logger.error("Some tests failed")
            sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main() 