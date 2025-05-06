#!/usr/bin/env python3
"""
Simple test script for the Minimal HTTP MCP Server using only the standard library.
"""

import argparse
import http.client
import json
import logging
import sys
import time
import urllib.parse
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SimpleHTTPTest')

class SimpleMCPClient:
    """Simple HTTP client for testing the MCP server using standard library."""

    def __init__(self, host: str, port: int, path: str = "/mcp", debug: bool = False):
        """
        Initialize the client.
        
        Args:
            host: The server hostname
            port: The server port
            path: The MCP endpoint path
            debug: Whether to enable debug logging
        """
        self.host = host
        self.port = port
        self.path = path
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
            # Create connection
            conn = http.client.HTTPConnection(self.host, self.port)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Add session ID if available and not an initialize request
            if self.session_id and method != "initialize":
                headers["Mcp-Session-Id"] = self.session_id
                
            self.logger.debug(f">> Headers: {headers}")
            
            # Send request
            conn.request("POST", self.path, body=json.dumps(request), headers=headers)
            
            # Get response
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
            response_headers = {k.lower(): v for k, v in response.getheaders()}
            
            # Log the response
            self.logger.debug(f"<< Response ({response.status}): {response_data}")
            self.logger.debug(f"<< Response Headers: {response_headers}")
            
            # Parse the response
            if response.status == 200:
                response_json = json.loads(response_data)
                
                # If this was a successful initialize, store the session ID
                if method == "initialize" and "result" in response_json and \
                   "session" in response_json["result"] and "id" in response_json["result"]["session"]:
                    self.session_id = response_json["result"]["session"]["id"]
                    self.logger.info(f"Initialized session with ID: {self.session_id}")
                elif method == "initialize":
                    # Also try to get from headers if body parse failed or was unexpected
                    header_session_id = response_headers.get('mcp-session-id')
                    if header_session_id:
                        self.session_id = header_session_id
                        self.logger.info(f"Initialized session with ID from header: {self.session_id}")
                
                return response_json
            else:
                self.logger.error(f"HTTP Error: {response.status} - {response_data}")
                return {"error": {"code": response.status, "message": response_data}}
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return {"error": {"code": -1, "message": f"Request failed: {str(e)}"}}
        finally:
            conn.close()
    
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
                "name": "MCP Simple Test Client",
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


def run_tests(host: str, port: int, protocol_version: str, debug: bool = False):
    """Run a basic test suite against the server."""
    client = SimpleMCPClient(host, port, debug=debug)
    
    # Test initialization
    logger.info(f"Testing initialization with protocol version {protocol_version}")
    init_result = client.initialize(protocol_version)
    if "error" in init_result:
        logger.error(f"Initialization failed: {init_result['error']}")
        return False
    
    # Test server info
    logger.info("Testing server info")
    server_info = client.send_request("server/info")
    if "error" in server_info:
        logger.error(f"Server info failed: {server_info['error']}")
        return False
    
    # Test tools list
    logger.info("Testing tools list")
    tools_list = client.send_request("tools/list")
    if "error" in tools_list:
        logger.error(f"Tools list failed: {tools_list['error']}")
        return False
    
    if "result" not in tools_list or "tools" not in tools_list["result"]:
        logger.error("Missing tools in response")
        return False
    
    # Test basic tool calls
    logger.info("Testing basic tool calls")
    tool_params_key = "parameters" if protocol_version == "2025-03-26" else "arguments"
    
    # Echo tool
    echo_payload = {
        "name": "echo",
        tool_params_key: {"message": "test"}
    }
    echo_result = client.send_request("tools/call", echo_payload)
    if "error" in echo_result:
        logger.error(f"Echo failed: {echo_result['error']}")
        return False
    
    # Add tool
    add_payload = {
        "name": "add",
        tool_params_key: {"a": 1, "b": 2}
    }
    add_result = client.send_request("tools/call", add_payload)
    if "error" in add_result:
        logger.error(f"Add failed: {add_result['error']}")
        return False
    
    # Test async tool calls if supported
    if protocol_version == "2025-03-26":
        logger.info("Testing async tool calls")
        async_payload = {
            "name": "sleep",
            "parameters": {"seconds": 1}
        }
        async_result = client.send_request("tools/call-async", async_payload)
        if "error" in async_result:
            logger.error(f"Async call failed: {async_result['error']}")
            return False
        
        call_id = async_result["result"]["id"]
        logger.info(f"Async call ID: {call_id}")
        
        # Poll for result
        poll_attempts = 0
        max_attempts = 20
        
        while poll_attempts < max_attempts:
            poll_payload = {"id": call_id}
            poll_result = client.send_request("tools/result", poll_payload)
            
            if "error" in poll_result:
                logger.error(f"Result poll failed: {poll_result['error']}")
                return False
                
            status = poll_result["result"]["status"]
            logger.info(f"Poll status: {status}")
            
            if status == "completed":
                break
            
            poll_attempts += 1
            time.sleep(0.2)
        
        if poll_attempts >= max_attempts:
            logger.error(f"Async operation did not complete after {max_attempts} attempts")
            return False
    
    logger.info("All tests passed!")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simple test script for MCP HTTP Server"
    )
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Hostname of the MCP HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int,
        default=9000,
        help="Port of the MCP HTTP server (default: 9000)"
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
    success = run_tests(args.host, args.port, args.protocol_version, args.debug)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 