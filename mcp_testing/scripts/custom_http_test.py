#!/usr/bin/env python3
"""
Custom HTTP test for FastMCP server.

This script tests the FastMCP server with SSE transport.
"""

import argparse
import json
import requests
import threading
import time
import uuid
import sseclient
from urllib.parse import urljoin
import re

class FastMCPTest:
    """Test client for FastMCP HTTP servers."""
    
    def __init__(self, server_url, debug=False):
        """Initialize the test client."""
        self.server_url = server_url
        self.debug = debug
        self.session_id = None
        self.sse_client = None
        self.sse_thread = None
        self.sse_responses = {}
        self.sse_event = threading.Event()
        self.stop_sse = False
        
        # Create session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        if debug:
            print(f"[DEBUG] Testing server at {server_url}")
    
    def log(self, message):
        """Log a debug message."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def start_sse_connection(self):
        """Establish SSE connection to the server."""
        base_url = self.server_url.rsplit("/mcp", 1)[0]
        notifications_url = urljoin(base_url, "/notifications")
        
        if self.session_id:
            notifications_url += f"?session_id={self.session_id}"
        
        self.log(f"Connecting to SSE endpoint: {notifications_url}")
        
        try:
            response = requests.get(notifications_url, stream=True)
            if response.status_code != 200:
                print(f"Error connecting to SSE endpoint: {response.status_code}")
                return False
            
            self.sse_client = sseclient.SSEClient(response)
            self.stop_sse = False
            
            # Start thread to listen for SSE events
            self.sse_thread = threading.Thread(target=self._sse_listener)
            self.sse_thread.daemon = True
            self.sse_thread.start()
            
            # Wait for first event (should contain session ID)
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Error establishing SSE connection: {e}")
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
                
                # Check if this is a session ID notification
                if "Connected to session" in event.data:
                    try:
                        # Extract session ID from message
                        self.session_id = event.data.split("Connected to session ")[1].strip()
                        self.log(f"Session ID from SSE: {self.session_id}")
                        self.sse_event.set()
                        continue
                    except Exception:
                        pass
                
                # Alternative format: /?session_id=xxxxxxxx
                if "session_id=" in event.data:
                    try:
                        # Extract session ID using regex
                        session_match = re.search(r'session_id=([a-f0-9]+)', event.data)
                        if session_match:
                            self.session_id = session_match.group(1)
                            self.log(f"Session ID from URL format: {self.session_id}")
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
            request_id = str(uuid.uuid4())
        
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
        
        # Make sure SSE connection is active
        if self.sse_thread is None or not self.sse_thread.is_alive():
            self.log("SSE connection not active, restarting...")
            self.start_sse_connection()
        
        response = self.session.post(
            url,
            json=request,
            headers=headers,
            timeout=5
        )
        
        self.log(f"Response status: {response.status_code}")
        if response.text:
            self.log(f"Response body: {response.text}")
        
        return response.status_code, response.headers, response.text
    
    def test_server(self):
        """Run tests against the server."""
        print("Testing FastMCP HTTP server with SSE transport")
        print("=============================================")
        
        # Test 1: Establish SSE connection
        print("\nTest 1: Establishing SSE connection...")
        if not self.start_sse_connection():
            print("FAIL: Could not establish SSE connection")
            return False
        
        print(f"SUCCESS: SSE connection established, session ID: {self.session_id}")
        
        # Test 2: Initialize
        print("\nTest 2: Testing initialize method...")
        init_id = "init-" + str(uuid.uuid4())
        status, headers, response = self.send_request(
            "initialize",
            {
                "protocol_version": "2025-03-26",
                "client_info": {
                    "name": "custom-test"
                }
            },
            init_id
        )
        
        if status != 202:
            print(f"FAIL: Initialize request returned status {status}")
            return False
        
        print("Server accepted initialize request")
        
        # Wait for SSE response
        init_response = self.wait_for_sse_response(init_id)
        if not init_response:
            print("FAIL: No SSE response received for initialize")
            return False
        
        if "error" in init_response:
            print(f"FAIL: Initialize error: {init_response['error']}")
            return False
        
        print(f"SUCCESS: Server initialized with capabilities: {init_response['result']['capabilities']}")
        
        # Test 3: Echo tool
        print("\nTest 3: Testing echo tool...")
        echo_id = "echo-" + str(uuid.uuid4())
        echo_message = "Hello FastMCP!"
        
        status, headers, response = self.send_request(
            "echo",
            {"message": echo_message},
            echo_id
        )
        
        if status != 202:
            print(f"FAIL: Echo request returned status {status}")
            return False
        
        print("Server accepted echo request")
        
        # Wait for SSE response
        echo_response = self.wait_for_sse_response(echo_id)
        if not echo_response:
            print("FAIL: No SSE response received for echo")
            return False
        
        if "error" in echo_response:
            print(f"FAIL: Echo error: {echo_response['error']}")
            return False
        
        if echo_response["result"] != echo_message:
            print(f"FAIL: Echo response mismatch: '{echo_response['result']}' != '{echo_message}'")
            return False
        
        print(f"SUCCESS: Echo tool returned correct message: '{echo_response['result']}'")
        
        # Test 4: Add tool
        print("\nTest 4: Testing add tool...")
        add_id = "add-" + str(uuid.uuid4())
        a, b = 42, 27
        
        status, headers, response = self.send_request(
            "add",
            {"a": a, "b": b},
            add_id
        )
        
        if status != 202:
            print(f"FAIL: Add request returned status {status}")
            return False
        
        print("Server accepted add request")
        
        # Wait for SSE response
        add_response = self.wait_for_sse_response(add_id)
        if not add_response:
            print("FAIL: No SSE response received for add")
            return False
        
        if "error" in add_response:
            print(f"FAIL: Add error: {add_response['error']}")
            return False
        
        expected_sum = a + b
        if add_response["result"] != expected_sum:
            print(f"FAIL: Add response mismatch: {add_response['result']} != {expected_sum}")
            return False
        
        print(f"SUCCESS: Add tool calculated correct sum: {add_response['result']} = {a} + {b}")
        
        # Test 5: Sleep tool (async)
        print("\nTest 5: Testing sleep tool (async)...")
        sleep_id = "sleep-" + str(uuid.uuid4())
        sleep_time = 1.0
        
        status, headers, response = self.send_request(
            "sleep",
            {"seconds": sleep_time},
            sleep_id
        )
        
        if status != 202:
            print(f"FAIL: Sleep request returned status {status}")
            return False
        
        print("Server accepted sleep request")
        start_time = time.time()
        
        # Wait for SSE response
        sleep_response = self.wait_for_sse_response(sleep_id)
        elapsed_time = time.time() - start_time
        
        if not sleep_response:
            print("FAIL: No SSE response received for sleep")
            return False
        
        if "error" in sleep_response:
            print(f"FAIL: Sleep error: {sleep_response['error']}")
            return False
        
        if elapsed_time < sleep_time:
            print(f"FAIL: Sleep tool returned too quickly: {elapsed_time}s < {sleep_time}s")
            return False
        
        print(f"SUCCESS: Sleep tool executed asynchronously ({elapsed_time:.2f}s)")
        print(f"Sleep message: {sleep_response['result']}")
        
        # Test complete
        print("\nAll tests passed successfully!")
        return True
    
    def stop(self):
        """Stop the SSE connection."""
        self.stop_sse = True
        if self.sse_thread and self.sse_thread.is_alive():
            self.sse_thread.join(timeout=2.0)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test FastMCP HTTP server")
    parser.add_argument(
        "--server-url",
        default="http://localhost:8085/mcp",
        help="URL of the FastMCP server"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    tester = FastMCPTest(args.server_url, args.debug)
    try:
        success = tester.test_server()
        return 0 if success else 1
    finally:
        tester.stop()

if __name__ == "__main__":
    import sys
    sys.exit(main()) 