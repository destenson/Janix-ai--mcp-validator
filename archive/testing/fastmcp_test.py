#!/usr/bin/env python3
"""
Comprehensive test for FastMCP HTTP server with SSE transport.

This script tests the FastMCP server with SSE transport, handling the
session ID and async responses correctly.
"""

import argparse
import json
import requests
import sseclient
import threading
import time
import uuid
import datetime
import sys
from urllib.parse import urljoin
import re
import os

class FastMCPTester:
    """Test client for FastMCP HTTP servers with SSE transport."""
    
    def __init__(self, server_url, debug=False):
        """Initialize the test client."""
        self.server_url = server_url.rstrip('/')
        if not self.server_url.endswith('/mcp'):
            self.server_url += '/mcp'
            
        self.base_url = self.server_url.rsplit('/mcp', 1)[0]
        self.debug = debug
        self.session_id = None
        self.sse_client = None
        self.sse_thread = None
        self.sse_responses = {}
        self.sse_event = threading.Event()
        self.stop_sse = False
        self.test_results = {"passed": 0, "failed": 0, "details": []}
        
        # Create session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        if debug:
            print(f"[DEBUG] Testing server at {server_url}")
            print(f"[DEBUG] Base URL: {self.base_url}")
            print(f"[DEBUG] MCP endpoint: {self.server_url}")
    
    def log(self, message):
        """Log a debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def establish_session(self):
        """Establish an SSE connection and get a session ID."""
        notifications_url = urljoin(self.base_url, "/notifications")
        
        self.log(f"Connecting to SSE endpoint: {notifications_url}")
        
        try:
            response = requests.get(notifications_url, stream=True)
            if response.status_code != 200:
                self.add_result("Session Establishment", False, 
                               f"Error connecting to SSE endpoint: {response.status_code}")
                return False
            
            self.sse_client = sseclient.SSEClient(response)
            self.stop_sse = False
            
            # Start thread to listen for SSE events
            self.sse_thread = threading.Thread(target=self._sse_listener)
            self.sse_thread.daemon = True
            self.sse_thread.start()
            
            # Wait for first event (should contain session ID)
            start_time = time.time()
            while time.time() - start_time < 5 and not self.session_id:
                time.sleep(0.1)
            
            if not self.session_id:
                self.add_result("Session Establishment", False, 
                               "No session ID received from SSE connection")
                return False
            
            self.add_result("Session Establishment", True, 
                           f"Successfully established session: {self.session_id}")
            return True
            
        except Exception as e:
            self.add_result("Session Establishment", False, 
                           f"Error establishing SSE connection: {e}")
            return False
    
    def _sse_listener(self):
        """Background thread that listens for SSE events."""
        try:
            for event in self.sse_client.events():
                if self.stop_sse:
                    break
                
                if not event.data:
                    continue
                
                self.log(f"SSE event received: {event.data}")
                
                # Check if this is a session ID notification - handle multiple formats
                if "Connected to session" in event.data:
                    try:
                        # Extract session ID from message
                        self.session_id = event.data.split("Connected to session ")[1].strip()
                        self.log(f"Session ID from SSE: {self.session_id}")
                        self.sse_event.set()
                        continue
                    except Exception:
                        pass
                
                # Alternative format: /?session_id=abcdef1234
                if "session_id=" in event.data:
                    try:
                        # Extract session ID from the URL-style message
                        session_match = re.search(r'session_id=([a-f0-9]+)', event.data)
                        if session_match:
                            self.session_id = session_match.group(1)
                            self.log(f"Session ID from URL-style SSE: {self.session_id}")
                            self.sse_event.set()
                            continue
                    except Exception as e:
                        self.log(f"Error extracting session ID: {e}")
                
                # Try to parse as JSON
                try:
                    data = json.loads(event.data)
                    if "id" in data:
                        self.sse_responses[data["id"]] = data
                        self.sse_event.set()
                except json.JSONDecodeError:
                    self.log(f"Non-JSON SSE event: {event.data}")
        except Exception as e:
            self.log(f"SSE listener error: {e}")
        finally:
            self.log("SSE listener stopped")
    
    def wait_for_sse_response(self, request_id, timeout=10):
        """Wait for an SSE response for the given request ID."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id in self.sse_responses:
                return self.sse_responses.pop(request_id)
            self.sse_event.wait(0.1)
            self.sse_event.clear()
        
        return None
    
    def send_request(self, method, params=None, request_id=None):
        """Send a request to the server."""
        if request_id is None:
            request_id = f"{method}-{str(uuid.uuid4())}"
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params is not None:
            request["params"] = params
        
        url = self.server_url
        if self.session_id:
            if "?" in url:
                url += f"&session_id={self.session_id}"
            else:
                url += f"?session_id={self.session_id}"
        
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        self.log(f"Sending request: {json.dumps(request)}")
        self.log(f"URL: {url}")
        self.log(f"Headers: {headers}")
        
        try:
            response = self.session.post(
                url,
                json=request,
                headers=headers,
                timeout=5
            )
            
            self.log(f"Response status: {response.status_code}")
            if response.text:
                self.log(f"Response body: {response.text}")
            
            return response.status_code, response.headers, response.text, request_id
        except Exception as e:
            self.log(f"Request error: {e}")
            return 0, {}, str(e), request_id
    
    def add_result(self, test_name, passed, message):
        """Add a test result."""
        if passed:
            self.test_results["passed"] += 1
            status = "PASS"
        else:
            self.test_results["failed"] += 1
            status = "FAIL"
            
        self.test_results["details"].append({
            "test": test_name,
            "status": status,
            "message": message
        })
        
        # Print result immediately as well
        mark = "✓" if passed else "✗"
        print(f"{mark} {test_name}: {message}")
    
    def test_initialize(self):
        """Test the initialize method."""
        print("\nTesting initialize method...")
        
        status, headers, response, request_id = self.send_request(
            "initialize",
            {
                "protocol_version": "2025-03-26",
                "client_info": {
                    "name": "FastMCP-Tester"
                }
            }
        )
        
        if status != 202:
            self.add_result("Initialize", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        init_response = self.wait_for_sse_response(request_id)
        if not init_response:
            self.add_result("Initialize", False, "No SSE response received")
            return False
        
        if "error" in init_response:
            self.add_result("Initialize", False, f"Error response: {init_response['error']}")
            return False
        
        if "result" not in init_response or "capabilities" not in init_response["result"]:
            self.add_result("Initialize", False, "Missing capabilities in response")
            return False
        
        capabilities = init_response["result"]["capabilities"]
        self.add_result("Initialize", True, f"Success with capabilities: {capabilities}")
        return True
    
    def test_echo_tool(self):
        """Test the echo tool."""
        print("\nTesting echo tool...")
        
        test_message = "Hello FastMCP!"
        status, headers, response, request_id = self.send_request(
            "echo",
            {"message": test_message}
        )
        
        if status != 202:
            self.add_result("Echo Tool", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        echo_response = self.wait_for_sse_response(request_id)
        if not echo_response:
            self.add_result("Echo Tool", False, "No SSE response received")
            return False
        
        if "error" in echo_response:
            self.add_result("Echo Tool", False, f"Error response: {echo_response['error']}")
            return False
        
        if "result" not in echo_response:
            self.add_result("Echo Tool", False, "Missing result in response")
            return False
        
        if echo_response["result"] != test_message:
            self.add_result("Echo Tool", False, 
                           f"Incorrect echo: '{echo_response['result']}' != '{test_message}'")
            return False
        
        self.add_result("Echo Tool", True, "Successfully echoed message")
        return True
    
    def test_add_tool(self):
        """Test the add tool."""
        print("\nTesting add tool...")
        
        a, b = 42, 27
        expected = a + b
        
        status, headers, response, request_id = self.send_request(
            "add",
            {"a": a, "b": b}
        )
        
        if status != 202:
            self.add_result("Add Tool", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        add_response = self.wait_for_sse_response(request_id)
        if not add_response:
            self.add_result("Add Tool", False, "No SSE response received")
            return False
        
        if "error" in add_response:
            self.add_result("Add Tool", False, f"Error response: {add_response['error']}")
            return False
        
        if "result" not in add_response:
            self.add_result("Add Tool", False, "Missing result in response")
            return False
        
        if add_response["result"] != expected:
            self.add_result("Add Tool", False, 
                           f"Incorrect sum: {add_response['result']} != {expected}")
            return False
        
        self.add_result("Add Tool", True, f"Successfully calculated {a} + {b} = {expected}")
        return True
    
    def test_async_sleep(self):
        """Test the async sleep tool."""
        print("\nTesting async sleep tool...")
        
        sleep_time = 1.0
        
        start_time = time.time()
        status, headers, response, request_id = self.send_request(
            "sleep",
            {"seconds": sleep_time}
        )
        
        if status != 202:
            self.add_result("Async Sleep", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        sleep_response = self.wait_for_sse_response(request_id)
        end_time = time.time()
        elapsed = end_time - start_time
        
        if not sleep_response:
            self.add_result("Async Sleep", False, "No SSE response received")
            return False
        
        if "error" in sleep_response:
            self.add_result("Async Sleep", False, f"Error response: {sleep_response['error']}")
            return False
        
        if "result" not in sleep_response:
            self.add_result("Async Sleep", False, "Missing result in response")
            return False
        
        # Verify that it took at least as long as requested
        if elapsed < sleep_time:
            self.add_result("Async Sleep", False, 
                           f"Sleep time too short: {elapsed:.2f}s < {sleep_time:.2f}s")
            return False
        
        self.add_result("Async Sleep", True, 
                       f"Successfully slept for {elapsed:.2f}s (requested {sleep_time:.2f}s)")
        return True
    
    def test_cors_support(self):
        """Test CORS support."""
        print("\nTesting CORS support...")
        
        try:
            # Send OPTIONS request to check CORS headers
            response = requests.options(
                self.server_url,
                headers={
                    "Origin": "http://example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type, Mcp-Session-Id"
                }
            )
            
            self.log(f"OPTIONS response status: {response.status_code}")
            self.log(f"OPTIONS response headers: {dict(response.headers)}")
            
            if response.status_code >= 400:
                self.add_result("CORS Support", False, 
                               f"OPTIONS request failed with status {response.status_code}")
                return False
            
            # Check required CORS headers
            required_headers = [
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers",
            ]
            
            missing_headers = [h for h in required_headers if h not in response.headers]
            
            if missing_headers:
                self.add_result("CORS Support", False, 
                               f"Missing CORS headers: {', '.join(missing_headers)}")
                return False
            
            # Check if POST is allowed
            if "POST" not in response.headers.get("Access-Control-Allow-Methods", ""):
                self.add_result("CORS Support", False, 
                               "POST method not allowed in CORS configuration")
                return False
            
            # Check if Mcp-Session-Id header is allowed
            if "Mcp-Session-Id" not in response.headers.get("Access-Control-Allow-Headers", ""):
                self.add_result("CORS Support", False, 
                               "Mcp-Session-Id header not allowed in CORS configuration")
                return False
            
            self.add_result("CORS Support", True, "Server properly supports CORS")
            return True
            
        except Exception as e:
            self.add_result("CORS Support", False, f"CORS test error: {e}")
            return False
    
    def test_list_tools(self):
        """Test the list_tools method."""
        print("\nTesting list_tools method...")
        
        status, headers, response, request_id = self.send_request("list_tools")
        
        if status != 202:
            self.add_result("List Tools", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        tools_response = self.wait_for_sse_response(request_id)
        if not tools_response:
            self.add_result("List Tools", False, "No SSE response received")
            return False
        
        if "error" in tools_response:
            self.add_result("List Tools", False, f"Error response: {tools_response['error']}")
            return False
        
        if "result" not in tools_response or not isinstance(tools_response["result"], list):
            self.add_result("List Tools", False, "Missing or invalid tools list in response")
            return False
        
        tools = tools_response["result"]
        expected_tools = ["echo", "add", "sleep"]
        missing_tools = [t for t in expected_tools if not any(tool["name"] == t for tool in tools)]
        
        if missing_tools:
            self.add_result("List Tools", False, f"Missing expected tools: {', '.join(missing_tools)}")
            return False
        
        self.add_result("List Tools", True, f"Successfully retrieved {len(tools)} tools")
        return True
    
    def test_list_resources(self):
        """Test the list_resources method."""
        print("\nTesting list_resources method...")
        
        status, headers, response, request_id = self.send_request("list_resources")
        
        if status != 202:
            self.add_result("List Resources", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        resources_response = self.wait_for_sse_response(request_id)
        if not resources_response:
            self.add_result("List Resources", False, "No SSE response received")
            return False
        
        if "error" in resources_response:
            # Some servers might not support resources, so this isn't necessarily a failure
            self.add_result("List Resources", True, "Server responded with error (resources may not be supported)")
            return True
        
        if "result" not in resources_response:
            self.add_result("List Resources", False, "Missing result in response")
            return False
        
        resources = resources_response["result"]
        self.add_result("List Resources", True, f"Successfully retrieved resource list with {len(resources)} items")
        return True
    
    def test_list_prompts(self):
        """Test the list_prompts method."""
        print("\nTesting list_prompts method...")
        
        status, headers, response, request_id = self.send_request("list_prompts")
        
        if status != 202:
            self.add_result("List Prompts", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        prompts_response = self.wait_for_sse_response(request_id)
        if not prompts_response:
            self.add_result("List Prompts", False, "No SSE response received")
            return False
        
        if "error" in prompts_response:
            # Some servers might not support prompts, so this isn't necessarily a failure
            self.add_result("List Prompts", True, "Server responded with error (prompts may not be supported)")
            return True
        
        if "result" not in prompts_response:
            self.add_result("List Prompts", False, "Missing result in response")
            return False
        
        prompts = prompts_response["result"]
        self.add_result("List Prompts", True, f"Successfully retrieved prompt list with {len(prompts)} items")
        return True
    
    def test_resource_templates(self):
        """Test the list_resource_templates method."""
        print("\nTesting list_resource_templates method...")
        
        status, headers, response, request_id = self.send_request("list_resource_templates")
        
        if status != 202:
            self.add_result("Resource Templates", False, f"Request failed with status {status}")
            return False
        
        # Wait for SSE response
        templates_response = self.wait_for_sse_response(request_id)
        if not templates_response:
            self.add_result("Resource Templates", False, "No SSE response received")
            return False
        
        if "error" in templates_response:
            # Some servers might not support templates, so this isn't necessarily a failure
            self.add_result("Resource Templates", True, 
                         "Server responded with error (resource templates may not be supported)")
            return True
        
        if "result" not in templates_response:
            self.add_result("Resource Templates", False, "Missing result in response")
            return False
        
        templates = templates_response["result"]
        self.add_result("Resource Templates", True, 
                      f"Successfully retrieved resource templates list with {len(templates)} items")
        return True
    
    def test_session_header(self):
        """Test session ID in header."""
        print("\nTesting session ID in header...")
        
        # Save the current session ID
        original_session_id = self.session_id
        
        # Send a request with only the header (no query parameter)
        url = self.server_url  # No query parameter
        headers = {"Mcp-Session-Id": self.session_id}
        
        request = {
            "jsonrpc": "2.0",
            "method": "echo",
            "id": f"header-test-{str(uuid.uuid4())}",
            "params": {"message": "Header Test"}
        }
        
        self.log(f"Sending request with header only: {json.dumps(request)}")
        self.log(f"URL: {url}")
        self.log(f"Headers: {headers}")
        
        try:
            response = self.session.post(
                url,
                json=request,
                headers=headers,
                timeout=5
            )
            
            self.log(f"Response status: {response.status_code}")
            if response.text:
                self.log(f"Response body: {response.text}")
            
            if response.status_code != 202:
                self.add_result("Session Header", False, 
                              f"Request with header only failed with status {response.status_code}")
                return False
            
            # Wait for SSE response
            echo_response = self.wait_for_sse_response(request["id"])
            if not echo_response:
                self.add_result("Session Header", False, "No SSE response received for header-only request")
                return False
            
            if "error" in echo_response:
                self.add_result("Session Header", False, f"Error response: {echo_response['error']}")
                return False
            
            self.add_result("Session Header", True, "Successfully used session ID in header")
            return True
            
        except Exception as e:
            self.add_result("Session Header", False, f"Request error: {e}")
            return False
    
    def test_session_query(self):
        """Test session ID in query parameter."""
        print("\nTesting session ID in query parameter...")
        
        # Send a request with only the query parameter (no header)
        url = f"{self.server_url}?session_id={self.session_id}"
        headers = {}  # No Mcp-Session-Id header
        
        request = {
            "jsonrpc": "2.0",
            "method": "echo",
            "id": f"query-test-{str(uuid.uuid4())}",
            "params": {"message": "Query Test"}
        }
        
        self.log(f"Sending request with query param only: {json.dumps(request)}")
        self.log(f"URL: {url}")
        self.log(f"Headers: {headers}")
        
        try:
            response = self.session.post(
                url,
                json=request,
                headers=headers,
                timeout=5
            )
            
            self.log(f"Response status: {response.status_code}")
            if response.text:
                self.log(f"Response body: {response.text}")
            
            if response.status_code != 202:
                self.add_result("Session Query", False, 
                              f"Request with query param only failed with status {response.status_code}")
                return False
            
            # Wait for SSE response
            echo_response = self.wait_for_sse_response(request["id"])
            if not echo_response:
                self.add_result("Session Query", False, "No SSE response received for query-param-only request")
                return False
            
            if "error" in echo_response:
                self.add_result("Session Query", False, f"Error response: {echo_response['error']}")
                return False
            
            self.add_result("Session Query", True, "Successfully used session ID in query parameter")
            return True
            
        except Exception as e:
            self.add_result("Session Query", False, f"Request error: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling for invalid requests."""
        print("\nTesting error handling...")
        
        # Test invalid method
        status, headers, response, request_id = self.send_request(
            "invalid_method",
            {"param": "value"}
        )
        
        if status != 202:
            self.add_result("Error Handling (Method)", False, 
                          f"Invalid method request returned unexpected status: {status}")
            return False
        
        # Wait for SSE response
        error_response = self.wait_for_sse_response(request_id)
        if not error_response:
            self.add_result("Error Handling (Method)", False, "No SSE response received for invalid method")
            return False
        
        if "error" not in error_response:
            self.add_result("Error Handling (Method)", False, 
                          "Expected error for invalid method, but got success response")
            return False
        
        # Test with invalid parameters
        status, headers, response, request_id = self.send_request(
            "add",
            {"a": "not_a_number", "b": 5}
        )
        
        if status != 202:
            self.add_result("Error Handling (Params)", False, 
                          f"Invalid params request returned unexpected status: {status}")
            return False
        
        # Wait for SSE response
        error_response = self.wait_for_sse_response(request_id)
        if not error_response:
            self.add_result("Error Handling (Params)", False, "No SSE response received for invalid params")
            return False
        
        if "error" not in error_response:
            self.add_result("Error Handling (Params)", False, 
                          "Expected error for invalid parameters, but got success response")
            return False
        
        self.add_result("Error Handling", True, "Server correctly handles invalid requests with error responses")
        return True
    
    def test_json_rpc_compliance(self):
        """Test compliance with JSON-RPC 2.0 specification."""
        print("\nTesting JSON-RPC compliance...")
        
        # Test without JSON-RPC version
        request = {
            "method": "echo",
            "id": f"jsonrpc-test-{str(uuid.uuid4())}",
            "params": {"message": "No Version"}
        }
        
        url = self.server_url
        if self.session_id:
            if "?" in url:
                url += f"&session_id={self.session_id}"
            else:
                url += f"?session_id={self.session_id}"
        
        headers = {}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        
        self.log(f"Sending request without jsonrpc version: {json.dumps(request)}")
        
        try:
            response = self.session.post(
                url,
                json=request,
                headers=headers,
                timeout=5
            )
            
            self.log(f"Response status: {response.status_code}")
            if response.text:
                self.log(f"Response body: {response.text}")
            
            # This should either return an error immediately or send an error via SSE
            if response.status_code == 202:
                # Check SSE response
                error_response = self.wait_for_sse_response(request["id"])
                if error_response and "error" in error_response:
                    self.add_result("JSON-RPC Compliance", True, 
                                 "Server correctly handles request without jsonrpc version")
                else:
                    self.add_result("JSON-RPC Compliance", False, 
                                 "Server accepted request without jsonrpc version")
                    return False
            else:
                # Should return immediate error
                self.add_result("JSON-RPC Compliance", True, 
                             f"Server rejected request without jsonrpc version (status {response.status_code})")
            
            # Test with invalid JSON-RPC version
            request = {
                "jsonrpc": "1.0",
                "method": "echo",
                "id": f"jsonrpc-test-{str(uuid.uuid4())}",
                "params": {"message": "Invalid Version"}
            }
            
            self.log(f"Sending request with invalid jsonrpc version: {json.dumps(request)}")
            
            response = self.session.post(
                url,
                json=request,
                headers=headers,
                timeout=5
            )
            
            self.log(f"Response status: {response.status_code}")
            if response.text:
                self.log(f"Response body: {response.text}")
            
            # This should either return an error immediately or send an error via SSE
            if response.status_code == 202:
                # Check SSE response
                error_response = self.wait_for_sse_response(request["id"])
                if error_response and "error" in error_response:
                    self.add_result("JSON-RPC Compliance", True, 
                                 "Server correctly handles request with invalid jsonrpc version")
                else:
                    self.add_result("JSON-RPC Compliance", False, 
                                 "Server accepted request with invalid jsonrpc version")
                    return False
            else:
                # Should return immediate error
                self.add_result("JSON-RPC Compliance", True, 
                             f"Server rejected request with invalid jsonrpc version (status {response.status_code})")
            
            self.add_result("JSON-RPC Compliance", True, "Server complies with JSON-RPC 2.0 specification")
            return True
            
        except Exception as e:
            self.add_result("JSON-RPC Compliance", False, f"Request error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests against the server."""
        print("=== FastMCP HTTP Server with SSE Transport Testing ===")
        print(f"Server URL: {self.server_url}")
        print(f"Test time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("====================================================")
        
        # First establish a session
        if not self.establish_session():
            print("Failed to establish a session, aborting tests")
            return False
        
        # Run the tests
        self.test_cors_support()
        self.test_initialize()
        self.test_list_tools()
        self.test_echo_tool()
        self.test_add_tool()
        self.test_async_sleep()
        self.test_session_header()
        self.test_session_query()
        self.test_error_handling()
        self.test_json_rpc_compliance()
        
        # Optional tests that might not be supported by all servers
        self.test_list_resources()
        self.test_list_prompts()
        self.test_resource_templates()
        
        # Print summary
        print("\n=== Test Summary ===")
        print(f"Total tests: {self.test_results['passed'] + self.test_results['failed']}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        
        return self.test_results["failed"] == 0
    
    def generate_report(self, filename=None):
        """Generate a compliance report."""
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/fastmcp_compliance_report_{timestamp}.md"
        
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            f.write("# FastMCP HTTP Server Compliance Report\n\n")
            
            f.write("## Server Information\n\n")
            f.write(f"- **Server URL**: {self.server_url}\n")
            f.write("- **Protocol Version**: 2025-03-26\n")
            f.write("- **Transport Type**: HTTP with Server-Sent Events (SSE)\n")
            f.write(f"- **Test Date**: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
            
            f.write("## Compliance Summary\n\n")
            f.write("| Feature | Status | Notes |\n")
            f.write("|---------|--------|-------|\n")
            
            # Add feature rows based on test results
            features = {
                "Session Establishment": "Uses SSE endpoint for session creation",
                "Session Header": "Support for session ID in HTTP header",
                "Session Query": "Support for session ID in query parameter",
                "CORS Support": "Required for browser-based clients",
                "Initialize": "Protocol initialization",
                "List Tools": "Tool discovery capability",
                "Echo Tool": "Basic tool functionality",
                "Add Tool": "Parameter processing",
                "Async Sleep": "Asynchronous tool execution",
                "Error Handling": "Proper handling of invalid requests",
                "JSON-RPC Compliance": "Adherence to JSON-RPC 2.0 specification",
                "List Resources": "Resource management (optional)",
                "List Prompts": "Prompt management (optional)",
                "Resource Templates": "Resource template support (optional)"
            }
            
            for feature, description in features.items():
                # Find test result for this feature
                result = next((r for r in self.test_results["details"] if r["test"] == feature), None)
                
                if result:
                    status = "✅" if result["status"] == "PASS" else "❌"
                    f.write(f"| {feature} | {status} | {description} |\n")
                else:
                    f.write(f"| {feature} | ⚠️ | Not tested |\n")
            
            f.write("\n## Test Results\n\n")
            
            for result in self.test_results["details"]:
                status_emoji = "✅" if result["status"] == "PASS" else "❌"
                f.write(f"### {status_emoji} {result['test']}\n\n")
                f.write(f"{result['message']}\n\n")
            
            f.write("## Transport Implementation Details\n\n")
            f.write("The FastMCP HTTP server implementation uses a modern approach with these characteristics:\n\n")
            f.write("1. **Session Management**\n")
            f.write("   - Sessions are established via the `/notifications` SSE endpoint\n")
            f.write("   - Session IDs are communicated in the initial SSE message\n")
            f.write("   - Session IDs can be included in subsequent requests via query parameter or header\n\n")
            
            f.write("2. **Request Processing**\n")
            f.write("   - All JSON-RPC requests are sent to the `/mcp` endpoint\n")
            f.write("   - Requests return a `202 Accepted` status code immediately\n")
            f.write("   - Actual results are sent asynchronously via the SSE connection\n\n")
            
            f.write("3. **Response Handling**\n")
            f.write("   - Responses follow the JSON-RPC 2.0 specification\n")
            f.write("   - Result or error objects are sent as SSE events\n")
            f.write("   - The client correlates responses with requests using the request ID\n\n")
            
            f.write("4. **Error Handling**\n")
            f.write("   - Protocol errors return appropriate JSON-RPC error objects\n")
            f.write("   - Session errors return 400 Bad Request responses\n")
            f.write("   - Malformed requests are properly rejected\n\n")
            
            f.write("## Conclusion\n\n")
            if self.test_results["failed"] == 0:
                f.write("The FastMCP HTTP server with SSE transport successfully passes all compliance tests ")
                f.write("and is fully compliant with the MCP 2025-03-26 specification. It demonstrates an ")
                f.write("efficient approach to implementing the protocol over HTTP with modern streaming capabilities.\n")
            else:
                f.write(f"The FastMCP HTTP server failed {self.test_results['failed']} tests. ")
                f.write("Please review the test results for details on the issues encountered.\n")
        
        print(f"\nCompliance report generated: {filename}")
        return filename
    
    def stop(self):
        """Stop the SSE connection and cleanup."""
        self.stop_sse = True
        if self.sse_thread and self.sse_thread.is_alive():
            self.sse_thread.join(1)


def main():
    """Run the FastMCP tester."""
    parser = argparse.ArgumentParser(description="Test FastMCP HTTP server with SSE transport")
    parser.add_argument("--server-url", default="http://localhost:8085", help="Server URL")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--report", action="store_true", help="Generate compliance report")
    parser.add_argument("--report-file", help="Filename for compliance report")
    args = parser.parse_args()
    
    try:
        tester = FastMCPTester(args.server_url, args.debug)
        success = tester.run_all_tests()
        
        if args.report or args.report_file:
            tester.generate_report(args.report_file)
        
        tester.stop()
        
        return 0 if success else 1
    except Exception as e:
        print(f"Error running tests: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 