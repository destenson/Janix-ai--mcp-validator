#!/usr/bin/env python3
"""
HTTP-specific MCP compliance testing script

This script runs compliance tests against an HTTP MCP server,
handling the session ID requirements correctly.
"""

import argparse
import asyncio
import json
import logging
import uuid
import sys
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import requests
import sseclient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("http_compliance")


class HttpComplianceTester:
    """Test MCP compliance for HTTP servers."""
    
    def __init__(self, server_url: str, debug: bool = False):
        """Initialize the tester with server URL."""
        self.server_url = server_url.rstrip('/')
        self.debug = debug
        self.session_id = str(uuid.uuid4())
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Mcp-Session-Id": self.session_id  # Add as header
        })
        
        # Also add session ID to URL as query parameter
        if "?" in self.server_url:
            self.request_url = f"{self.server_url}&session_id={self.session_id}"
        else:
            self.request_url = f"{self.server_url}?session_id={self.session_id}"
        
        # SSE connection
        self.sse_connected = False
        self.sse_thread = None
        self.stop_sse = False
        self.sse_responses = {}  # Store SSE responses by request ID
        self.sse_response_event = threading.Event()  # Event to signal when a response is received
        
        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"Created tester with session ID: {self.session_id}")
            logger.debug(f"Request URL: {self.request_url}")
            logger.debug(f"Headers: {self.session.headers}")
    
    def log(self, message: str):
        """Log a message if debug is enabled."""
        if self.debug:
            logger.debug(message)
    
    def _sse_reader_thread(self):
        """Background thread to maintain SSE connection."""
        sse_url = f"{self.server_url}/notifications?session_id={self.session_id}"
        self.log(f"SSE thread connecting to: {sse_url}")
        
        try:
            # Use a dedicated requests session for the SSE connection.  Using the same
            # session object concurrently from multiple threads can cause the underlying
            # socket to be closed unexpectedly (``requests`` sessions are **not** thread
            # safe).  By using our own session instance we avoid interfering with the
            # main thread's POST requests.
            sse_session = requests.Session()
            headers = {
                "Accept": "text/event-stream",
                "Mcp-Session-Id": self.session_id,
                "Cache-Control": "no-cache",
            }
            response = sse_session.get(sse_url, stream=True, headers=headers, timeout=None)
            
            if response.status_code != 200:
                logger.error(f"SSE connection failed: {response.status_code}")
                self.sse_connected = False
                return
                
            self.sse_connected = True
            self.log("SSE connection established successfully")
            
            # Extract session ID from the response headers if available
            for header, value in response.headers.items():
                if header.lower() == 'mcp-session-id':
                    self.session_id = value
                    self.log(f"Updated session ID from headers: {self.session_id}")
                    # Update request URL and headers
                    if "?" in self.server_url:
                        self.request_url = f"{self.server_url}&session_id={self.session_id}"
                    else:
                        self.request_url = f"{self.server_url}?session_id={self.session_id}"
                    self.session.headers["Mcp-Session-Id"] = self.session_id
                    break
            
            # Create SSE client
            client = sseclient.SSEClient(response)
            
            # Event loop to process SSE events
            for event in client.events():
                if self.stop_sse:
                    break
                
                try:
                    # Log the event
                    event_data = event.data
                    self.log(f"SSE event: {event_data}")
                    
                    # Check if the event data contains a session ID
                    if "session_id=" in event_data:
                        # Try to extract session ID from the event data
                        import re
                        session_match = re.search(r'session_id=([a-f0-9]+)', event_data)
                        if session_match:
                            server_session_id = session_match.group(1)
                            self.log(f"Found session ID in SSE event: {server_session_id}")
                            
                            # Update our session ID to match the server's
                            self.session_id = server_session_id
                            
                            # Update request URL
                            if "?" in self.server_url:
                                self.request_url = f"{self.server_url}&session_id={self.session_id}"
                            else:
                                self.request_url = f"{self.server_url}?session_id={self.session_id}"
                                
                            # Update headers
                            self.session.headers["Mcp-Session-Id"] = self.session_id
                            
                            self.log(f"Updated session ID: {self.session_id}")
                            self.log(f"Updated request URL: {self.request_url}")
                    
                    # Check if the event data is a JSON-RPC response
                    elif event_data.startswith('{') and '"jsonrpc"' in event_data:
                        try:
                            # Parse the JSON response
                            json_data = json.loads(event_data)
                            
                            # Check if it's a valid JSON-RPC response with an ID
                            if "jsonrpc" in json_data and "id" in json_data:
                                request_id = json_data["id"]
                                self.log(f"Received response for request ID: {request_id}")
                                
                                # Store the response
                                self.sse_responses[request_id] = json_data
                                
                                # Signal that a response has been received
                                self.sse_response_event.set()
                        except json.JSONDecodeError:
                            self.log(f"Failed to parse JSON from event: {event_data}")
                except Exception as e:
                    self.log(f"Error processing SSE event: {str(e)}")
                
        except Exception as e:
            logger.error(f"SSE connection error: {str(e)}")
            self.sse_connected = False
            
        finally:
            self.log("SSE connection closed")
            self.sse_connected = False
    
    def send_request_and_wait_for_response(self, method: str, params: Optional[Dict[str, Any]] = None, 
                                            timeout: float = 5.0) -> Tuple[int, Dict[str, Any]]:
        """Send a request and wait for the response to come through SSE."""
        # Clear any previous responses
        self.sse_response_event.clear()
        
        # Generate a request ID we can track
        request_id = str(uuid.uuid4())
        
        # Build request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params is not None:
            request["params"] = params
        
        self.log(f"Sending request: {json.dumps(request)}")
        self.log(f"Using session ID: {self.session_id}")
        self.log(f"Request URL: {self.request_url}")
        
        # Ensure the SSE listener is running.  FastMCP may silently close idle
        # SSE streams after a response; if that happened we transparently
        # reconnect so subsequent requests still get their responses.
        if not self.sse_connected:
            self.log("SSE connection not active – attempting to reconnect")
            self.start_sse_connection()
        
        try:
            # Send request
            response = self.session.post(
                self.request_url,
                json=request,
                timeout=5
            )
            
            status_code = response.status_code
            self.log(f"Initial HTTP response: {status_code}")
            
            # For FastMCP SSE, we expect 202 Accepted and the actual response comes via SSE
            if status_code == 202:
                # Wait for SSE response with our request ID
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Check if we received a response
                    if request_id in self.sse_responses:
                        json_response = self.sse_responses[request_id]
                        del self.sse_responses[request_id]  # Clean up
                        return 200, json_response  # Convert 202 to 200 if we got a proper response
                    
                    # Wait for new response event, timeout after 0.1 seconds
                    self.sse_response_event.wait(0.1)
                    self.sse_response_event.clear()
                
                # Timeout waiting for response
                logger.warning(f"Timeout waiting for SSE response for request ID: {request_id}")
                return 408, {"error": {"message": "Timeout waiting for SSE response"}}
            
            # For non-202 responses, try to handle them directly
            try:
                json_response = response.json()
                self.log(f"Response body: {json.dumps(json_response)}")
                return status_code, json_response
            except ValueError:
                self.log(f"Response text: {response.text}")
                return status_code, {"error": {"message": response.text}}
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return 500, {"error": {"message": str(e)}}
    
    def test_initialize(self) -> bool:
        """Test the initialize request."""
        logger.info("Testing initialize...")
        
        params = {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "MCP HTTP Compliance Tester",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        }
        
        status, response = self.send_request_and_wait_for_response("initialize", params)
        
        if status != 200:
            logger.error(f"Initialize failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        logger.info("Initialize test passed")
        return True
    
    def test_tools_list(self) -> bool:
        """Test the tools/list request."""
        logger.info("Testing tools/list...")
        
        status, response = self.send_request_and_wait_for_response("tools/list")
        
        if status != 200:
            logger.error(f"tools/list failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        result = response["result"]
        
        if "tools" not in result or not isinstance(result["tools"], list):
            logger.error("Result missing 'tools' array")
            return False
        
        tools = result["tools"]
        logger.info(f"Server returned {len(tools)} tools")
        self.tools = tools
        
        logger.info("tools/list test passed")
        return True
    
    def test_echo_tool(self) -> bool:
        """Test the echo tool."""
        logger.info("Testing tools/call with echo tool...")
        
        # Check if echo tool exists
        if not hasattr(self, 'tools'):
            logger.error("Tools have not been listed yet")
            return False
        
        echo_tool = next((tool for tool in self.tools if tool.get('name') == 'echo'), None)
        if not echo_tool:
            logger.warning("echo tool not found, skipping test")
            return True
        
        params = {
            "name": "echo",
            "parameters": {
                "message": "Hello, MCP!"
            }
        }
        
        status, response = self.send_request_and_wait_for_response("tools/call", params)
        
        if status != 200:
            logger.error(f"tools/call echo failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        result = response["result"]
        if result != "Hello, MCP!":
            logger.error(f"Unexpected echo result: {result}")
            return False
        
        logger.info("Echo tool test passed")
        return True
    
    def test_add_tool(self) -> bool:
        """Test the add tool."""
        logger.info("Testing tools/call with add tool...")
        
        # Check if add tool exists
        if not hasattr(self, 'tools'):
            logger.error("Tools have not been listed yet")
            return False
        
        add_tool = next((tool for tool in self.tools if tool.get('name') == 'add'), None)
        if not add_tool:
            logger.warning("add tool not found, skipping test")
            return True
        
        params = {
            "name": "add",
            "parameters": {
                "a": 40,
                "b": 2
            }
        }
        
        status, response = self.send_request_and_wait_for_response("tools/call", params)
        
        if status != 200:
            logger.error(f"tools/call add failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        result = response["result"]
        if result != 42:
            logger.error(f"Unexpected add result: {result}")
            return False
        
        logger.info("Add tool test passed")
        return True
    
    def test_async_sleep(self) -> bool:
        """Test async sleep tool."""
        logger.info("Testing async sleep tool...")
        
        # Check if sleep tool exists
        if not hasattr(self, 'tools'):
            logger.error("Tools have not been listed yet")
            return False
        
        sleep_tool = next((tool for tool in self.tools if tool.get('name') == 'sleep'), None)
        if not sleep_tool:
            logger.warning("sleep tool not found, skipping test")
            return True
        
        # First call the tool asynchronously
        params = {
            "name": "sleep",
            "parameters": {
                "seconds": 1
            }
        }
        
        status, response = self.send_request_and_wait_for_response("tools/call-async", params)
        
        if status != 200:
            logger.error(f"tools/call-async failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        result = response["result"]
        if "id" not in result:
            logger.error("Result missing task ID")
            return False
        
        task_id = result["id"]
        logger.info(f"Async task ID: {task_id}")
        
        # Wait a bit for the task to finish
        logger.info("Waiting for task to complete...")
        time.sleep(2)
        
        # Check the task result
        params = {
            "id": task_id
        }
        
        status, response = self.send_request_and_wait_for_response("tools/result", params)
        
        if status != 200:
            logger.error(f"tools/result failed with status {status}")
            return False
        
        if "result" not in response:
            logger.error("Response missing 'result' field")
            return False
        
        result = response["result"]
        if "status" not in result:
            logger.error("Result missing status")
            return False
        
        if result["status"] != "completed":
            logger.error(f"Unexpected task status: {result['status']}")
            return False
        
        if "result" not in result:
            logger.error("Result missing actual result")
            return False
        
        logger.info("Async sleep test passed")
        return True
    
    def run_all_tests(self) -> bool:
        """Run all compliance tests."""
        tests = [
            self.test_initialize,
            self.test_tools_list,
            self.test_echo_tool,
            self.test_add_tool,
            self.test_async_sleep
        ]
        
        passed = 0
        failed = 0
        
        logger.info("Starting HTTP compliance tests...")
        logger.info(f"Testing server: {self.server_url}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Request URL: {self.request_url}")
        
        # Start SSE connection
        logger.info("Starting SSE connection...")
        if not self.start_sse_connection():
            logger.error("Failed to establish SSE connection, tests may fail")
        else:
            logger.info("SSE connection established successfully")
        
        try:
            # Run each test
            for test in tests:
                try:
                    if test():
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Test {test.__name__} raised exception: {str(e)}")
                    failed += 1
            
            # Print summary
            logger.info("\n=== TEST SUMMARY ===")
            logger.info(f"Total tests: {len(tests)}")
            logger.info(f"Passed: {passed}")
            logger.info(f"Failed: {failed}")
            
            return failed == 0
            
        finally:
            # Clean up
            self.stop_sse_connection()

    # New methods to manage the SSE background thread
    def start_sse_connection(self, timeout: float = 5.0) -> bool:
        """Start the SSE reader thread and wait until the connection is established.

        Returns
        -------
        bool
            True if the SSE connection was successfully established, False otherwise.
        """
        # If we already have a running thread and it is connected, nothing to do
        if self.sse_thread and self.sse_thread.is_alive():
            return self.sse_connected

        # Reset the stop flag
        self.stop_sse = False
        self.sse_connected = False

        # Launch the background thread
        self.sse_thread = threading.Thread(target=self._sse_reader_thread, daemon=True)
        self.sse_thread.start()

        # Wait for the connection to be marked as established or timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.sse_connected:
                return True
            time.sleep(0.1)

        # Timed out waiting for connection
        logger.warning("Timed out waiting for SSE connection to establish")
        return False

    def stop_sse_connection(self):
        """Signal the SSE reader thread to stop and wait for it to exit."""
        self.stop_sse = True

        # Wake up any waiters so the thread can exit promptly
        self.sse_response_event.set()

        # If the thread is running, join it briefly so it can cleanly exit
        if self.sse_thread and self.sse_thread.is_alive():
            try:
                self.sse_thread.join(timeout=2.0)
            except RuntimeError:
                # Thread cannot be joined (never started or already finished)
                pass

        self.sse_thread = None
        self.sse_connected = False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run HTTP compliance tests for MCP")
    parser.add_argument("--server-url", default="http://localhost:8080", help="MCP server URL")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    tester = HttpComplianceTester(args.server_url, args.debug)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 