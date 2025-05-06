#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP Test Client

This script tests both protocol versions (2024-11-05 and 2025-03-26) of both server types (STDIO and HTTP).
"""

import os
import sys
import json
import time
import logging
import requests
import subprocess
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp-test-client")

class MCPTestClient:
    """Base class for MCP test clients."""
    
    def __init__(self, protocol_version: str):
        """Initialize the test client."""
        self.protocol_version = protocol_version
        self.request_id = 0
        
    def next_request_id(self) -> str:
        """Get the next request ID."""
        self.request_id += 1
        return str(self.request_id)
        
    def make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a JSON-RPC request."""
        request = {
            "jsonrpc": "2.0",
            "id": self.next_request_id(),
            "method": method,
            "params": params or {}
        }
        return request
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities based on protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "protocolVersion": "2024-11-05",
                "tools": True
            }
        else:
            return {
                "protocolVersion": "2025-03-26",
                "tools": {
                    "asyncSupported": True
                }
            }
            
    def get_tool_params(self, tool_name: str, **params) -> Dict[str, Any]:
        """Get tool parameters in the correct format for the protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "name": tool_name,
                "arguments": params
            }
        else:
            return {
                "name": tool_name,
                "parameters": params
            }

class MCPHTTPTestClient(MCPTestClient):
    """HTTP-based MCP test client."""
    
    def __init__(self, protocol_version: str, host: str = "localhost", port: int = 9000):
        """Initialize the HTTP test client."""
        super().__init__(protocol_version)
        self.base_url = f"http://{host}:{port}/mcp"
        self.session_id = None
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the HTTP server."""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add session ID to header if we have one
        if self.session_id:
            headers["X-MCP-Session"] = self.session_id
            logger.debug(f"Using session ID: {self.session_id}")
            
        response = requests.post(self.base_url, json=request, headers=headers)
        response.raise_for_status()
        
        response_json = response.json()
        
        # Extract session ID from initialize response
        if request.get("method") == "initialize":
            result = response_json.get("result", {})
            session = result.get("session", {})
            if "id" in session:
                self.session_id = session["id"]
                logger.debug(f"Got session ID from initialize: {self.session_id}")
            
        return response_json
        
    def cleanup(self):
        """Clean up the session."""
        if self.session_id:
            try:
                headers = {"X-MCP-Session": self.session_id}
                requests.delete(self.base_url, headers=headers)
            except Exception as e:
                logger.error(f"Error cleaning up session: {str(e)}")
                

class MCPSTDIOTestClient(MCPTestClient):
    """STDIO-based MCP test client."""
    
    def __init__(self, protocol_version: str, server_process: subprocess.Popen):
        """Initialize the STDIO test client."""
        super().__init__(protocol_version)
        self.server = server_process
        
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the STDIO server."""
        request_str = json.dumps(request)
        self.server.stdin.write(request_str.encode() + b"\n")
        self.server.stdin.flush()
        
        response_str = self.server.stdout.readline().decode().strip()
        return json.loads(response_str)
        
    def cleanup(self):
        """Clean up the server process."""
        self.server.terminate()
        self.server.wait()

def run_test_sequence(client: MCPTestClient):
    """Run a test sequence on a client."""
    logger.info(f"Testing {client.__class__.__name__} with protocol version {client.protocol_version}")
    
    try:
        # Initialize
        init_request = client.make_request("initialize", {
            "protocolVersion": client.protocol_version,
            "clientInfo": {
                "name": "MCP Test Client",
                "version": "1.0.0"
            },
            "capabilities": client.get_capabilities()
        })
        init_response = client.send_request(init_request)
        logger.info(f"Initialize response: {json.dumps(init_response, indent=2)}")
        
        # Server info
        info_request = client.make_request("server/info")
        info_response = client.send_request(info_request)
        logger.info(f"Server info response: {json.dumps(info_response, indent=2)}")
        
        # List tools
        tools_method = "mcp/tools" if client.protocol_version == "2024-11-05" else "tools/list"
        tools_request = client.make_request(tools_method)
        tools_response = client.send_request(tools_request)
        logger.info(f"Tools list response: {json.dumps(tools_response, indent=2)}")
        
        # Test echo tool
        echo_params = {"text": "Hello, MCP!"} if client.protocol_version == "2024-11-05" else {"message": "Hello, MCP!"}
        echo_request = client.make_request(
            "mcp/tools/call" if client.protocol_version == "2024-11-05" else "tools/call",
            client.get_tool_params("echo", **echo_params)
        )
        echo_response = client.send_request(echo_request)
        logger.info(f"Echo response: {json.dumps(echo_response, indent=2)}")
        
        # Test add tool
        add_request = client.make_request(
            "mcp/tools/call" if client.protocol_version == "2024-11-05" else "tools/call",
            client.get_tool_params("add", a=5, b=7)
        )
        add_response = client.send_request(add_request)
        logger.info(f"Add response: {json.dumps(add_response, indent=2)}")
        
        # Shutdown
        shutdown_request = client.make_request("shutdown")
        shutdown_response = client.send_request(shutdown_request)
        logger.info(f"Shutdown response: {json.dumps(shutdown_response, indent=2)}")
        
    finally:
        client.cleanup()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCP Servers")
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        help="Protocol version to test (tests both if not specified)"
    )
    parser.add_argument(
        "--server-type",
        choices=["http", "stdio"],
        help="Server type to test (tests both if not specified)"
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=9000,
        help="Port for HTTP server"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    versions = [args.protocol_version] if args.protocol_version else ["2024-11-05", "2025-03-26"]
    server_types = [args.server_type] if args.server_type else ["http", "stdio"]
    
    for version in versions:
        for server_type in server_types:
            try:
                if server_type == "http":
                    # Start HTTP server
                    server_script = f"ref_http_server/server_{version.replace('-', '_')}.py"
                    server_process = subprocess.Popen(
                        [sys.executable, server_script, "--port", str(args.http_port)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    time.sleep(1)  # Wait for server to start
                    
                    client = MCPHTTPTestClient(version, port=args.http_port)
                    run_test_sequence(client)
                    
                    server_process.terminate()
                    server_process.wait()
                    
                else:
                    # Start STDIO server
                    server_script = f"ref_stdio_server/stdio_server_{version.replace('-', '_')}.py"
                    server_process = subprocess.Popen(
                        [sys.executable, server_script],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    client = MCPSTDIOTestClient(version, server_process)
                    run_test_sequence(client)
                    
            except Exception as e:
                logger.error(f"Error testing {server_type} server with version {version}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 