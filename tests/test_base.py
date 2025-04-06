#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base test classes for MCP test suites.
"""

import os
import json
import requests
import sys
import time
import select
import subprocess
import threading
import io
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Get environment variables for testing configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
MCP_CLIENT_URL = os.environ.get("MCP_CLIENT_URL", "http://localhost:8081")
MCP_TRANSPORT_TYPE = os.environ.get("MCP_TRANSPORT_TYPE", "http")
MCP_SERVER_PROCESS_ID = os.environ.get("MCP_SERVER_PROCESS", None)
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2025-03-26")

# Global variable to store server process reference if using STDIO
SERVER_PROCESS = None

def set_server_process(process):
    """Set the global server process for STDIO transport.
    
    Args:
        process: The subprocess.Popen object for the MCP server.
    """
    global SERVER_PROCESS
    SERVER_PROCESS = process
    
    # Start the debug output thread automatically when a server process is set
    if SERVER_PROCESS is not None:
        start_debug_output_thread(SERVER_PROCESS)

def start_debug_output_thread(server_process):
    """
    Start a thread to capture and print the server's stderr output.
    
    Args:
        server_process: The server subprocess
    """
    # If already terminated, return early
    if server_process.poll() is not None:
        return
        
    def print_server_stderr():
        """Thread target for printing server stderr output."""
        while server_process and server_process.poll() is None:
            try:
                # Use select to avoid blocking
                ready, _, _ = select.select([server_process.stderr], [], [], 0.5)
                if ready:
                    line = server_process.stderr.readline()
                    if line:
                        line_str = line.decode('utf-8').rstrip() if isinstance(line, bytes) else line.rstrip()
                        print(f"[SERVER] {line_str}", file=sys.stderr)
            except Exception as e:
                # Don't crash the thread on error
                print(f"Error reading server stderr: {str(e)}", file=sys.stderr)
                time.sleep(1)  # Avoid tight loop on error
    
    stderr_thread = threading.Thread(target=print_server_stderr, daemon=True)
    stderr_thread.start()
    return stderr_thread

class MCPBaseTest:
    """Base class for all MCP test suites."""
    
    def setup_method(self, method):
        """Initialize the base test class with common attributes.
        
        This uses pytest's setup_method which runs before each test method
        instead of __init__ which causes pytest collection issues.
        """
        self.server_url = MCP_SERVER_URL
        self.client_url = MCP_CLIENT_URL
        self.transport_type = MCP_TRANSPORT_TYPE
        self.protocol_version = MCP_PROTOCOL_VERSION
        self.server_capabilities = {}
        self.client_capabilities = {}
        self.session_id = None
        
        # If we're in STDIO mode and have a server process ID, get the actual process
        global SERVER_PROCESS
        if self.transport_type == "stdio" and SERVER_PROCESS is None:
            # This would be populated by the test runner in a real implementation
            print("WARNING: Running in STDIO mode but no server process is available", file=sys.stderr)
    
    def get_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for the current protocol version.
        
        Returns:
            The loaded JSON schema as a dictionary.
        """
        schema_file = f"mcp_schema_{self.protocol_version}.json"
        schema_path = Path(__file__).parent.parent / "schema" / schema_file
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file for version {self.protocol_version} not found at {schema_path}")
        
        with open(schema_path) as f:
            return json.load(f)
        
    def _send_request(self, data: Dict[str, Any]) -> Any:
        """Send a request to the MCP server.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            The response object (HTTP Response for HTTP transport, dict for STDIO).
        """
        # Force STDIO transport when we have a global server process
        global SERVER_PROCESS
        if SERVER_PROCESS is not None:
            return self._send_stdio_request(data)
        
        # Otherwise use configured transport
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
        
        # Debug mode can be enabled via environment variable
        debug = os.environ.get("MCP_DEBUG_STDIO", "0").lower() in ("1", "true", "yes")
        
        # Configurable timeout - increased from 5 to 10 seconds by default
        # Also allow configuration via environment variable
        timeout = float(os.environ.get("MCP_STDIO_TIMEOUT", "10.0"))
        
        # Maximum number of retries for broken pipes
        max_retries = int(os.environ.get("MCP_STDIO_MAX_RETRIES", "3"))
        
        if SERVER_PROCESS is None:
            error_msg = "Server process is not available for STDIO transport"
            if debug:
                print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
            # Mock response for when server process is not available
            return MockResponse(
                status_code=500,
                json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
            )
        
        # Convert data to JSON string and add newline
        request_str = json.dumps(data) + "\n"
        
        # Track retries
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                # Check if process is still alive
                if SERVER_PROCESS.poll() is not None:
                    exit_code = SERVER_PROCESS.poll()
                    error_msg = f"Server process terminated with exit code {exit_code}"
                    if debug:
                        print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                    return MockResponse(
                        status_code=500,
                        json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                    )
                
                # For debugging
                if debug:
                    print(f"STDIO REQUEST: {request_str.strip()}", file=sys.stderr)
                
                # Write the request to the server's stdin
                if isinstance(SERVER_PROCESS.stdin, io.TextIOWrapper):
                    SERVER_PROCESS.stdin.write(request_str)
                else:
                    SERVER_PROCESS.stdin.write(request_str.encode('utf-8'))
                SERVER_PROCESS.stdin.flush()
                
                # If it's a notification (no id), there's no response
                if "id" not in data:
                    if debug:
                        print("STDIO NOTIFICATION: No response expected", file=sys.stderr)
                    return MockResponse(
                        status_code=204,  # No Content
                        json_data=None
                    )
                
                # Wait for response
                response_str = None
                start_time = time.time()
                
                while (time.time() - start_time) < timeout:
                    # Check for server process termination during wait
                    if SERVER_PROCESS.poll() is not None:
                        exit_code = SERVER_PROCESS.poll()
                        error_msg = f"Server process terminated with exit code {exit_code} while waiting for response"
                        if debug:
                            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                        return MockResponse(
                            status_code=500,
                            json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                        )
                    
                    # Use select to avoid blocking indefinitely
                    ready_to_read, _, _ = select.select([SERVER_PROCESS.stdout], [], [], 0.1)
                    
                    if ready_to_read:
                        if isinstance(SERVER_PROCESS.stdout, io.TextIOWrapper):
                            response_str = SERVER_PROCESS.stdout.readline()
                        else:
                            response_line = SERVER_PROCESS.stdout.readline()
                            response_str = response_line.decode('utf-8') if response_line else None
                        
                        if response_str:
                            break
                
                # If no response received within timeout
                if not response_str:
                    if retries < max_retries:
                        if debug:
                            print(f"STDIO WARNING: No response received, retrying ({retries+1}/{max_retries})...", file=sys.stderr)
                        retries += 1
                        time.sleep(1)  # Wait before retry
                        continue
                    else:
                        error_msg = f"No response received after {timeout} seconds and {max_retries} retries"
                        if debug:
                            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                        return MockResponse(
                            status_code=504,  # Gateway Timeout
                            json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                        )
                
                # For debugging
                if debug:
                    print(f"STDIO RESPONSE: {response_str.strip()}", file=sys.stderr)
                
                # Parse the JSON response
                try:
                    response_data = json.loads(response_str)
                    # Check if response ID matches request ID
                    if "id" in response_data and response_data["id"] != data["id"]:
                        if debug:
                            print(f"STDIO WARNING: Response ID {response_data['id']} does not match request ID {data['id']}", file=sys.stderr)
                    return MockResponse(
                        status_code=200,
                        json_data=response_data
                    )
                except json.JSONDecodeError as e:
                    if debug:
                        print(f"STDIO ERROR: Failed to parse JSON response: {str(e)}\nResponse: {response_str}", file=sys.stderr)
                    return MockResponse(
                        status_code=502,  # Bad Gateway
                        json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": f"Failed to parse JSON response: {str(e)}"}}
                    )
                    
            except BrokenPipeError as e:
                last_error = e
                if retries < max_retries:
                    if debug:
                        print(f"STDIO WARNING: Broken pipe, retrying ({retries+1}/{max_retries})...", file=sys.stderr)
                    retries += 1
                    time.sleep(1)  # Wait before retry
                else:
                    error_msg = f"Broken pipe after {max_retries} retries: {str(last_error)}"
                    if debug:
                        print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                    return MockResponse(
                        status_code=500,
                        json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                    )
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if debug:
                    print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                return MockResponse(
                    status_code=500,
                    json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                )
                
        # This should not be reached, but just in case
        error_msg = f"Failed to send request after {max_retries} retries"
        if debug:
            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
        return MockResponse(
            status_code=500,
            json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
        )

class MockResponse:
    """A mock HTTP response object used for STDIO transport."""
    
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]]):
        """Initialize the mock response.
        
        Args:
            status_code: The HTTP status code for the response.
            json_data: The JSON data for the response.
        """
        self.status_code = status_code
        self._json_data = json_data
        self.headers = {}
        
    def json(self) -> Dict[str, Any]:
        """Get the JSON data from the response.
        
        Returns:
            The JSON data.
        """
        if self._json_data is None:
            raise ValueError("No JSON data available")
        return self._json_data 