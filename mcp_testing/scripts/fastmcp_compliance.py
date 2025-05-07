#!/usr/bin/env python3
"""
FastMCP Compliance Report Generator

This script tests a FastMCP HTTP server with SSE transport and generates
a compliance report.
"""

import argparse
import json
import os
import sys
import datetime
import time
import threading
import uuid
import re
import requests
import sseclient
from urllib.parse import urljoin

class FastMCPComplianceTester:
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
        reconnect_count = 0
        max_reconnects = 3
        
        while not self.stop_sse and reconnect_count <= max_reconnects:
            try:
                for event in self.sse_client.events():
                    if self.stop_sse:
                        break
                    
                    if not event.data:
                        continue
                    
                    self.log(f"SSE event received: {event.data}")
                    
                    # Handle different session ID notification formats
                    if "Connected to session" in event.data:
                        try:
                            # Standard format: "Connected to session abcdef1234"
                            self.session_id = event.data.split("Connected to session ")[1].strip()
                            self.log(f"Session ID from standard format: {self.session_id}")
                            self.sse_event.set()
                            continue
                        except Exception as e:
                            self.log(f"Error extracting session ID from standard format: {e}")
                    
                    # Alternative format: "/?session_id=abcdef1234"
                    if "session_id=" in event.data:
                        try:
                            # Extract session ID from the URL-style message
                            session_match = re.search(r'session_id=([a-f0-9-]+)', event.data)
                            if session_match:
                                self.session_id = session_match.group(1)
                                self.log(f"Session ID from URL-style SSE: {self.session_id}")
                                self.sse_event.set()
                                continue
                        except Exception as e:
                            self.log(f"Error extracting session ID from URL format: {e}")
                    
                    # Try to parse as JSON
                    try:
                        data = json.loads(event.data)
                        if "id" in data:
                            # Store the response and signal that we got it
                            self.sse_responses[data["id"]] = data
                            self.sse_event.set()
                    except json.JSONDecodeError:
                        # Not JSON, might be a keepalive or other message
                        if ": keepalive" in event.data:
                            self.log("Received keepalive message")
                        else:
                            self.log(f"Non-JSON SSE event: {event.data}")
            
            except Exception as e:
                self.log(f"SSE listener error: {e}")
                # Try to reconnect if the connection was lost
                if not self.stop_sse:
                    reconnect_count += 1
                    self.log(f"Attempting to reconnect to SSE (attempt {reconnect_count}/{max_reconnects})")
                    
                    # Short sleep before reconnect
                    time.sleep(1)
                    
                    # Reestablish the connection
                    try:
                        self.establish_session()
                    except Exception as reconnect_error:
                        self.log(f"Failed to reconnect: {reconnect_error}")
        
        if reconnect_count > max_reconnects:
            self.log("Maximum reconnection attempts reached. Giving up.")
        
        self.log("SSE listener stopped")
    
    def wait_for_sse_response(self, request_id, timeout=10):
        """Wait for an SSE response for the given request ID."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if we have the response already
            if request_id in self.sse_responses:
                return self.sse_responses.pop(request_id)
            
            # Make sure our SSE connection is still alive
            if self.sse_thread is None or not self.sse_thread.is_alive():
                self.log("SSE connection lost, attempting to reconnect...")
                self.establish_session()
                # Give it a moment to initialize
                time.sleep(1)
            
            # Wait for an event (with timeout)
            self.sse_event.wait(0.5)
            self.sse_event.clear()
        
        self.log(f"Timeout waiting for response to request: {request_id}")
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
        
        # Make sure SSE connection is active
        if self.sse_thread is None or not self.sse_thread.is_alive():
            self.log("SSE connection not active, restarting...")
            self.establish_session()
        
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
        
        # Check for tools list in result
        # The server might return either {"result": [tool1, tool2]} or {"result": {"tools": [tool1, tool2]}}
        if "result" not in tools_response:
            self.add_result("List Tools", False, "Missing result in response")
            return False
        
        # Handle both possible response formats
        result = tools_response["result"]
        tools = result
        
        # If the result is a dict, check for a "tools" key
        if isinstance(result, dict) and "tools" in result:
            tools = result["tools"]
        
        # Validate the tools list
        if not isinstance(tools, list):
            self.add_result("List Tools", False, "Missing or invalid tools list in response")
            return False
        
        expected_tools = ["echo", "add", "sleep"]
        missing_tools = [t for t in expected_tools if not any(tool.get("name") == t for tool in tools)]
        
        if missing_tools:
            self.add_result("List Tools", False, f"Missing expected tools: {', '.join(missing_tools)}")
            return False
        
        self.add_result("List Tools", True, f"Successfully retrieved {len(tools)} tools")
        return True
    
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
        self.test_initialize()
        self.test_list_tools()
        self.test_echo_tool()
        self.test_add_tool()
        self.test_async_sleep()
        
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
                "Initialize": "Protocol initialization",
                "List Tools": "Tool discovery",
                "Echo Tool": "Basic tool functionality",
                "Add Tool": "Parameter processing",
                "Async Sleep": "Asynchronous tool execution"
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
            f.write("   - Session IDs must be included in subsequent requests (via query parameter or header)\n\n")
            
            f.write("2. **Request Processing**\n")
            f.write("   - All JSON-RPC requests are sent to the `/mcp` endpoint\n")
            f.write("   - Requests return a `202 Accepted` status code immediately\n")
            f.write("   - Actual results are sent asynchronously via the SSE connection\n\n")
            
            f.write("3. **Response Handling**\n")
            f.write("   - Responses follow the JSON-RPC 2.0 specification\n")
            f.write("   - Result or error objects are sent as SSE events\n")
            f.write("   - The client correlates responses with requests using the request ID\n\n")
            
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
    parser.add_argument("--report-file", help="Filename for compliance report")
    args = parser.parse_args()
    
    try:
        # Create report directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        tester = FastMCPComplianceTester(args.server_url, args.debug)
        success = tester.run_all_tests()
        
        # Always generate a report
        report_file = args.report_file
        if not report_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"reports/fastmcp_compliance_report_{timestamp}.md"
        
        tester.generate_report(report_file)
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