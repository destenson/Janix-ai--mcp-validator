#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base test classes for MCP test suites.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

# Get environment variables for testing configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
MCP_CLIENT_URL = os.environ.get("MCP_CLIENT_URL", "http://localhost:8081")
MCP_TRANSPORT_TYPE = os.environ.get("MCP_TRANSPORT_TYPE", "http")
MCP_SERVER_PROCESS_ID = os.environ.get("MCP_SERVER_PROCESS", None)

# Global variable to store server process reference if using STDIO
SERVER_PROCESS = None

def set_server_process(process):
    """Set the global server process for STDIO transport.
    
    Args:
        process: The subprocess.Popen object for the MCP server.
    """
    global SERVER_PROCESS
    SERVER_PROCESS = process

class MCPBaseTest:
    """Base class for all MCP test suites."""
    
    def __init__(self):
        """Initialize the base test class with common attributes."""
        self.server_url = MCP_SERVER_URL
        self.client_url = MCP_CLIENT_URL
        self.transport_type = MCP_TRANSPORT_TYPE
        self.server_capabilities = {}
        self.client_capabilities = {}
        self.session_id = None
        
        # If we're in STDIO mode and have a server process ID, get the actual process
        global SERVER_PROCESS
        if self.transport_type == "stdio" and MCP_SERVER_PROCESS_ID and SERVER_PROCESS is None:
            # This would be populated by the test runner in a real implementation
            # For now, we'll have a placeholder
            SERVER_PROCESS = self._get_server_process()
    
    def _get_server_process(self):
        """Get the server process object from the main test runner.
        
        In a real implementation, this would retrieve the actual subprocess object.
        """
        # Placeholder - in a real implementation, this would retrieve the actual process
        return None
        
    def _send_request(self, data: Dict[str, Any]) -> Any:
        """Send a request to the MCP server.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            The response object (HTTP Response for HTTP transport, dict for STDIO).
        """
        if self.transport_type == "http":
            return self._send_http_request(data)
        elif self.transport_type == "stdio":
            return self._send_stdio_request(data)
        else:
            raise ValueError(f"Unsupported transport type: {self.transport_type}")
    
    def _send_http_request(self, data: Dict[str, Any]) -> requests.Response:
        """Send a request to the MCP server using HTTP transport.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            The HTTP response object.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.session_id:
            headers["MCP-Session-ID"] = self.session_id
            
        response = requests.post(
            self.server_url,
            headers=headers,
            json=data
        )
        
        # Check for and store session ID if provided
        if "MCP-Session-ID" in response.headers:
            self.session_id = response.headers["MCP-Session-ID"]
            
        return response
    
    def _send_stdio_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server using STDIO transport.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            A mock response object that mimics the HTTP response interface.
        """
        global SERVER_PROCESS
        
        if SERVER_PROCESS is None:
            # Mock response for when server process is not available
            return MockResponse(
                status_code=500,
                json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": "Server not available"}}
            )
        
        try:
            # Convert data to JSON string and add newline
            request_str = json.dumps(data) + "\n"
            
            # Write to server's stdin
            SERVER_PROCESS.stdin.write(request_str.encode('utf-8'))
            SERVER_PROCESS.stdin.flush()
            
            # Read response from stdout
            response_line = SERVER_PROCESS.stdout.readline().decode('utf-8').strip()
            response_data = json.loads(response_line)
            
            # Create a mock response object
            return MockResponse(status_code=200, json_data=response_data)
        except Exception as e:
            # Return error response on failure
            return MockResponse(
                status_code=500,
                json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": f"STDIO communication error: {str(e)}"}}
            )
    
    def _send_request_to_client(self, data: Dict[str, Any]) -> requests.Response:
        """Send a JSON-RPC request to the client."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return requests.post(self.client_url, json=data, headers=headers)


class MockResponse:
    """Mock HTTP response object to provide consistent interface for STDIO transport."""
    
    def __init__(self, status_code: int, json_data: Dict[str, Any]):
        """Initialize the mock response.
        
        Args:
            status_code: HTTP status code equivalent
            json_data: JSON response data
        """
        self.status_code = status_code
        self._json_data = json_data
        self.headers = {}
    
    def json(self) -> Dict[str, Any]:
        """Return the JSON data."""
        return self._json_data 