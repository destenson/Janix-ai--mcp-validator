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
                        line_str = line.decode('utf-8').rstrip()
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
        if self.transport_type == "stdio" and MCP_SERVER_PROCESS_ID and SERVER_PROCESS is None:
            # This would be populated by the test runner in a real implementation
            # For now, we'll have a placeholder
            SERVER_PROCESS = self._get_server_process()
    
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
                # Check if process is still alive before attempting communication
                if SERVER_PROCESS.poll() is not None:
                    error_msg = f"Server process terminated with exit code {SERVER_PROCESS.returncode}"
                    if debug:
                        print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                    
                    # Try to restart the server if we have the command
                    server_command = os.environ.get("MCP_SERVER_COMMAND")
                    if server_command and retries < max_retries:
                        if debug:
                            print(f"STDIO: Attempting to restart server (retry {retries+1}/{max_retries})", file=sys.stderr)
                        try:
                            SERVER_PROCESS = subprocess.Popen(
                                server_command,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                bufsize=1  # Line buffered
                            )
                            # Give the server a moment to initialize
                            time.sleep(2)
                            retries += 1
                            continue
                        except Exception as e:
                            error_msg = f"Failed to restart server: {str(e)}"
                            if debug:
                                print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                    
                    return MockResponse(
                        status_code=500,
                        json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                    )
                
                if debug:
                    print(f"STDIO sending: {request_str.strip()}", file=sys.stderr)
                
                # Write to server's stdin - use try block specifically for broken pipe
                try:
                    SERVER_PROCESS.stdin.write(request_str.encode('utf-8'))
                    SERVER_PROCESS.stdin.flush()
                except BrokenPipeError as e:
                    if retries < max_retries:
                        if debug:
                            print(f"STDIO WARNING: Broken pipe detected, retrying ({retries+1}/{max_retries})", file=sys.stderr)
                        # Increment retry counter and try again
                        retries += 1
                        last_error = e
                        
                        # Try to restart the server if we have the command
                        server_command = os.environ.get("MCP_SERVER_COMMAND")
                        if server_command:
                            if debug:
                                print(f"STDIO: Attempting to restart server", file=sys.stderr)
                            try:
                                # Close existing process if possible
                                try:
                                    SERVER_PROCESS.terminate()
                                    SERVER_PROCESS.wait(timeout=3)
                                except:
                                    pass
                                
                                SERVER_PROCESS = subprocess.Popen(
                                    server_command,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stdin=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    bufsize=1  # Line buffered
                                )
                                # Give the server a moment to initialize
                                time.sleep(2)
                            except Exception as e:
                                if debug:
                                    print(f"STDIO ERROR: Failed to restart server: {str(e)}", file=sys.stderr)
                        
                        time.sleep(1)  # Brief delay before retry
                        continue
                    else:
                        # Max retries reached
                        error_msg = f"Broken pipe error after {max_retries} retries: {str(e)}"
                        if debug:
                            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                        return MockResponse(
                            status_code=500,
                            json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                        )
                
                # Read response with progressive timeout
                response_line = ""
                start_time = time.time()
                
                # Try to read with timeout using select
                readable, _, _ = select.select([SERVER_PROCESS.stdout], [], [], timeout)
                if readable:
                    response_line = SERVER_PROCESS.stdout.readline().decode('utf-8').strip()
                    
                    if debug:
                        print(f"STDIO received: {response_line}", file=sys.stderr)
                        
                    if not response_line:
                        if retries < max_retries:
                            if debug:
                                print(f"STDIO WARNING: Empty response received, retrying ({retries+1}/{max_retries})", file=sys.stderr)
                            retries += 1
                            time.sleep(1)  # Brief delay before retry
                            continue
                        else:
                            error_msg = "Empty response from server after max retries"
                            if debug:
                                print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                            return MockResponse(
                                status_code=500,
                                json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                            )
                    
                    try:
                        response_data = json.loads(response_line)
                        # Create a mock response object with success
                        return MockResponse(status_code=200, json_data=response_data)
                    except json.JSONDecodeError as e:
                        if retries < max_retries:
                            if debug:
                                print(f"STDIO WARNING: Invalid JSON in response, retrying ({retries+1}/{max_retries})", file=sys.stderr)
                                print(f"Response was: {response_line}", file=sys.stderr)
                            retries += 1
                            time.sleep(1)  # Brief delay before retry
                            continue
                        else:
                            error_msg = f"Invalid JSON in response after max retries: {str(e)}"
                            if debug:
                                print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                                print(f"Response was: {response_line}", file=sys.stderr)
                            return MockResponse(
                                status_code=500,
                                json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                            )
                else:
                    # Timeout occurred
                    if retries < max_retries:
                        if debug:
                            print(f"STDIO WARNING: Timeout waiting for response after {timeout} seconds, retrying ({retries+1}/{max_retries})", file=sys.stderr)
                        retries += 1
                        # Exponential backoff for timeout
                        timeout = min(timeout * 1.5, 30.0)  # Increase timeout but cap at 30 seconds
                        continue
                    else:
                        error_msg = f"Timeout waiting for response after {timeout} seconds (max retries reached)"
                        if debug:
                            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                        return MockResponse(
                            status_code=500,
                            json_data={"jsonrpc": "2.0", "id": data.get("id"), "error": {"code": -32000, "message": error_msg}}
                        )
            
            except Exception as e:
                # For any other exceptions
                if retries < max_retries:
                    if debug:
                        print(f"STDIO WARNING: Error during communication, retrying ({retries+1}/{max_retries}): {str(e)}", file=sys.stderr)
                    retries += 1
                    last_error = e
                    time.sleep(1)  # Brief delay before retry
                    continue
                else:
                    error_msg = f"STDIO communication error after {max_retries} retries: {str(e)}"
                    if debug:
                        print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                    # Return error response on failure
                    request_id = data.get("id") if isinstance(data, dict) else None
                    return MockResponse(
                        status_code=500,
                        json_data={"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": error_msg}}
                    )
        
        # If we get here, we've exhausted all retries
        error_msg = f"Failed after {max_retries} retries: {str(last_error)}"
        if debug:
            print(f"STDIO ERROR: {error_msg}", file=sys.stderr)
        request_id = data.get("id") if isinstance(data, dict) else None
        return MockResponse(
            status_code=500,
            json_data={"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": error_msg}}
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
        
        # For STDIO, a successful JSON-RPC response should be interpreted as status 200
        # regardless of what status_code was passed in
        if isinstance(json_data, dict) and "result" in json_data:
            self.status_code = 200
        
        # For error responses, maintain the error status code
        elif isinstance(json_data, dict) and "error" in json_data:
            # Keep the 500 status code if it was set, otherwise use 200 as per JSON-RPC spec
            if self.status_code != 500:
                self.status_code = 200
                
        # For batch responses, check if it's a list
        elif isinstance(json_data, list):
            self.status_code = 200
        
        # Set a default text property to simulate HTTP response
        self.text = json.dumps(json_data) if json_data else ""
    
    def json(self) -> Dict[str, Any]:
        """Return the JSON data."""
        return self._json_data 