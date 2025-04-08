# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP HTTP Server Tester

A class for testing MCP HTTP server implementations.
"""

import json
import uuid
import http.client
import socket
import time
from urllib.parse import urlparse

class MCPHttpTester:
    """Class to test an MCP HTTP server implementation."""
    
    def __init__(self, url, debug=False):
        """
        Initialize the tester with the server URL.
        
        Args:
            url: The URL of the MCP server
            debug: Whether to print debug information
        """
        self.url = url
        self.debug = debug
        
        # Parse the URL
        parsed_url = urlparse(url)
        self.host = parsed_url.netloc
        self.path = parsed_url.path or "/"
        
        # Session information
        self.session_id = None
        self.initialized = False
        
        # Protocol information
        self.protocol_version = "2025-03-26"
        
        self.log(f"MCP HTTP Tester initialized for {url}")
        self.log(f"Host: {self.host}, Path: {self.path}")
    
    def log(self, message):
        """Print a log message if debug is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def send_request(self, method, json_data=None, headers=None, request_method="POST"):
        """
        Send a JSON-RPC request to the server.
        
        Args:
            method: The JSON-RPC method to call
            json_data: Additional JSON data to include (optional)
            headers: Additional headers to include (optional)
            request_method: The HTTP method to use (default: POST)
            
        Returns:
            Tuple of (status_code, headers, body)
        """
        # Build the request
        if json_data is None:
            json_data = {}
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": str(uuid.uuid4())
        }
        
        # Add params if provided
        if json_data:
            request["params"] = json_data
        
        # Convert to JSON
        json_str = json.dumps(request)
        self.log(f"Request: {json_str}")
        
        # Set up headers
        all_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"  # Add text/event-stream for better compatibility
        }
        
        # Add session ID if we have one and this isn't an initialize request
        if self.session_id and method != "initialize":
            all_headers["Mcp-Session-Id"] = self.session_id
        
        # Add any additional headers
        if headers:
            all_headers.update(headers)
        
        # Send the request
        conn = http.client.HTTPConnection(self.host, timeout=10)  # Reduce timeout to 10 seconds
        
        if request_method == "OPTIONS":
            conn.request(request_method, self.path, headers=all_headers)
        else:
            conn.request(request_method, self.path, body=json_str, headers=all_headers)
        
        # Get the response
        resp = conn.getresponse()
        status = resp.status
        reason = resp.reason
        
        # Get headers
        headers = {}
        for header in resp.getheaders():
            headers[header[0].lower()] = header[1]
        
        # Read body
        body_bytes = resp.read()
        body = body_bytes.decode('utf-8')
        
        # Close the connection
        conn.close()
        
        self.log(f"Response Status: {status} {reason}")
        self.log(f"Response Headers: {headers}")
        self.log(f"Response Body: {body}")
        
        # Parse the JSON response body if it's valid JSON
        parsed_body = None
        if body and status == 200:
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                self.log("Failed to parse response as JSON")
        
        return status, headers, parsed_body or body
    
    def options_request(self):
        """Send an OPTIONS request to check server CORS support."""
        print("Testing OPTIONS request...")
        
        try:
            # Use a direct connection with a shorter timeout specifically for OPTIONS
            conn = http.client.HTTPConnection(self.host, timeout=5)
            conn.request("OPTIONS", self.path, headers={
                "Accept": "application/json, text/event-stream"
            })
            
            # Get the response
            resp = conn.getresponse()
            status = resp.status
            
            # Get headers
            headers = {}
            for header in resp.getheaders():
                headers[header[0].lower()] = header[1]
            
            # Read and discard body
            resp.read()
            conn.close()
            
            if status != 200:
                print(f"ERROR: OPTIONS request failed with status {status}")
                return False
            
            # Check CORS headers
            if 'access-control-allow-origin' not in headers:
                print("ERROR: Missing Access-Control-Allow-Origin header")
                return False
            
            if 'access-control-allow-methods' not in headers:
                print("ERROR: Missing Access-Control-Allow-Methods header")
                return False
            
            if 'access-control-allow-headers' not in headers:
                print("ERROR: Missing Access-Control-Allow-Headers header")
                return False
            
            print("OPTIONS request successful")
            return True
            
        except (http.client.HTTPException, socket.error) as e:
            print(f"ERROR: OPTIONS request failed with exception: {str(e)}")
            # Continue with other tests even if OPTIONS fails
            print("Continuing with other tests...")
            return False
    
    def initialize(self):
        """Initialize the server and store the session ID."""
        print("Testing server initialization...")
        
        params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": {
                "name": "MCP HTTP Tester",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        }
        
        status, headers, body = self.send_request("initialize", params)
        
        if status != 200:
            print(f"ERROR: Initialize request failed with status {status}")
            return False
        
        # Handle the case where the server is already initialized
        if isinstance(body, dict) and 'error' in body:
            error = body['error']
            if error.get('code') == -32803 and "already initialized" in error.get('message', ''):
                print("Server already initialized, continuing with tests...")
                # We need to retry the initialize call to get the session ID
                print("Attempting to get a session ID...")
                # Try calling server/info to get a session ID
                status, headers, _ = self.send_request("server/info")
                if 'mcp-session-id' not in headers:
                    print("ERROR: Could not retrieve session ID")
                    return False
                self.session_id = headers['mcp-session-id']
                print(f"Retrieved session ID: {self.session_id}")
                self.initialized = True
                return True
            else:
                print(f"ERROR: Server returned error: {error}")
                return False
        
        # Check for session ID in headers
        if 'mcp-session-id' not in headers:
            print("ERROR: No Mcp-Session-Id header in response")
            return False
        
        self.session_id = headers['mcp-session-id']
        print(f"Received session ID: {self.session_id}")
        
        # Verify response body
        if not isinstance(body, dict):
            print("ERROR: Response body is not a JSON object")
            return False
        
        if 'result' not in body:
            print("ERROR: Response missing 'result' field")
            return False
        
        result = body['result']
        
        # Check for required fields in result
        if 'protocolVersion' not in result:
            print("ERROR: Missing protocolVersion in result")
            return False
        
        if 'serverInfo' not in result:
            print("ERROR: Missing serverInfo in result")
            return False
        
        if 'capabilities' not in result:
            print("ERROR: Missing capabilities in result")
            return False
        
        print("Server initialization successful")
        self.initialized = True
        return True
    
    def list_tools(self):
        """Test the tools/list endpoint."""
        if not self.initialized:
            print("ERROR: Server not initialized, cannot list tools")
            return False
        
        print("Testing tools/list endpoint...")
        
        status, _, body = self.send_request("tools/list")
        
        if status != 200:
            print(f"ERROR: tools/list request failed with status {status}")
            return False
        
        # Verify response body
        if not isinstance(body, dict):
            print("ERROR: Response body is not a JSON object")
            return False
        
        if 'result' not in body:
            print("ERROR: Response missing 'result' field")
            return False
        
        result = body['result']
        
        # Check for tools array
        if 'tools' not in result or not isinstance(result['tools'], list):
            print("ERROR: Response missing 'tools' array")
            return False
        
        tools = result['tools']
        print(f"Server returned {len(tools)} tools")
        
        return True
    
    def test_echo_tool(self):
        """Test the echo tool."""
        if not self.initialized:
            print("ERROR: Server not initialized, cannot call tools")
            return False
        
        print("Testing tools/call with echo tool...")
        
        message = "Hello, MCP HTTP Server!"
        params = {
            "name": "echo",
            "parameters": {
                "message": message
            }
        }
        
        status, _, body = self.send_request("tools/call", params)
        
        if status != 200:
            print(f"ERROR: tools/call request failed with status {status}")
            return False
        
        # Verify response body
        if not isinstance(body, dict):
            print("ERROR: Response body is not a JSON object")
            return False
        
        if 'result' not in body:
            print("ERROR: Response missing 'result' field")
            return False
        
        result = body['result']
        
        # Check that the echo message is returned
        if 'message' not in result or result['message'] != message:
            print(f"ERROR: Echo tool did not return the correct message")
            print(f"Expected: {message}")
            print(f"Got: {result.get('message', 'missing')}")
            return False
        
        print("Echo tool test successful")
        return True
    
    def test_add_tool(self):
        """Test the add tool."""
        if not self.initialized:
            print("ERROR: Server not initialized, cannot call tools")
            return False
        
        print("Testing tools/call with add tool...")
        
        a, b = 42, 58
        expected_sum = a + b
        
        params = {
            "name": "add",
            "parameters": {
                "a": a,
                "b": b
            }
        }
        
        status, _, body = self.send_request("tools/call", params)
        
        if status != 200:
            print(f"ERROR: tools/call request failed with status {status}")
            return False
        
        # Verify response body
        if not isinstance(body, dict):
            print("ERROR: Response body is not a JSON object")
            return False
        
        if 'result' not in body:
            print("ERROR: Response missing 'result' field")
            return False
        
        result = body['result']
        
        # Check that the sum is correct
        if 'sum' not in result or result['sum'] != expected_sum:
            print(f"ERROR: Add tool did not return the correct sum")
            print(f"Expected: {expected_sum}")
            print(f"Got: {result.get('sum', 'missing')}")
            return False
        
        print("Add tool test successful")
        return True
    
    def test_async_sleep_tool(self):
        """Test the async sleep tool functionality."""
        if not self.initialized:
            print("ERROR: Server not initialized, cannot call tools")
            return False
        
        print("Testing tools/call-async with sleep tool...")
        
        # Only run this test for 2025-03-26 protocol
        if self.protocol_version != "2025-03-26":
            print("Skipping async test for older protocol versions")
            return True
        
        sleep_time = 3  # seconds
        
        params = {
            "name": "sleep",
            "parameters": {
                "seconds": sleep_time
            }
        }
        
        status, _, body = self.send_request("tools/call-async", params)
        
        if status != 200:
            print(f"ERROR: tools/call-async request failed with status {status}")
            return False
        
        # Verify response body
        if not isinstance(body, dict):
            print("ERROR: Response body is not a JSON object")
            return False
        
        if 'result' not in body:
            print("ERROR: Response missing 'result' field")
            return False
        
        result = body['result']
        
        # Check for task ID
        if 'id' not in result:
            print("ERROR: Missing task ID in result")
            return False
        
        task_id = result['id']
        print(f"Started async task with ID: {task_id}")
        
        # Poll for result
        max_attempts = 10
        attempt = 0
        completed = False
        
        print(f"Waiting for async task to complete (max {max_attempts} attempts)...")
        
        while attempt < max_attempts:
            time.sleep(1)
            attempt += 1
            
            params = {
                "id": task_id
            }
            
            status, _, body = self.send_request("tools/result", params)
            
            if status != 200:
                print(f"ERROR: tools/result request failed with status {status}")
                return False
            
            if not isinstance(body, dict) or 'result' not in body:
                print("ERROR: Invalid response format")
                return False
            
            result = body['result']
            
            if 'status' not in result:
                print("ERROR: Missing status in result")
                return False
            
            if result['status'] == 'completed':
                completed = True
                print(f"Async task completed after {attempt} attempts")
                break
            
            print(f"Attempt {attempt}: Task status = {result['status']}")
        
        if not completed:
            print("ERROR: Async task did not complete in time")
            return False
        
        print("Async sleep tool test successful")
        return True
    
    def reset_server(self):
        """Try to reset the server by sending a shutdown request."""
        print("Attempting to reset server state...")
        try:
            conn = http.client.HTTPConnection(self.host, timeout=5)
            headers = {"Content-Type": "application/json"}
            
            # Send a shutdown request without a session ID
            request = {
                "jsonrpc": "2.0",
                "method": "shutdown",
                "id": str(uuid.uuid4())
            }
            json_str = json.dumps(request)
            
            conn.request("POST", self.path, body=json_str, headers=headers)
            
            # Get and discard the response
            resp = conn.getresponse()
            resp.read()
            conn.close()
            
            # Wait a brief moment for the server to process the shutdown
            time.sleep(1)
            
            print("Server reset attempted, continuing with tests")
            return True
        except Exception as e:
            print(f"Server reset attempt failed: {str(e)}")
            print("Continuing with tests anyway")
            return False

    def run_all_tests(self):
        """Run all tests in sequence."""
        print(f"Running all tests against {self.url}")
        
        # Try to reset the server state first
        self.reset_server()
        
        tests = [
            ("OPTIONS request", self.options_request),
            ("Initialize", self.initialize),
            ("List Tools", self.list_tools),
            ("Echo Tool", self.test_echo_tool),
            ("Add Tool", self.test_add_tool),
            ("Async Sleep Tool", self.test_async_sleep_tool)
        ]
        
        results = []
        
        for name, test_func in tests:
            print(f"\n=== Running test: {name} ===")
            
            try:
                result = test_func()
                results.append((name, result))
                
                if not result and name == "Initialize":
                    print("Server initialization failed, aborting remaining tests")
                    break
                    
            except Exception as e:
                print(f"ERROR: Test {name} raised exception: {str(e)}")
                import traceback
                traceback.print_exc()
                results.append((name, False))
                
                if name == "Initialize":
                    print("Server initialization failed, aborting remaining tests")
                    break
        
        # Print summary
        print("\n=== Test Results ===")
        passed = 0
        failed = 0
        
        for name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"{status}: {name}")
            
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\nSummary: {passed} passed, {failed} failed")
        
        return failed == 0 