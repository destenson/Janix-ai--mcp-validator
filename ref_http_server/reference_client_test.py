#!/usr/bin/env python3
"""
MCP Reference Client Test

A client for testing MCP servers that follows the specification correctly.
It obtains a session ID from the server during initialization, without generating one in advance.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-reference-client")

class McpReferenceClient:
    """MCP reference client implementation that follows the specification."""

    def __init__(self, server_url: str, debug: bool = False):
        """Initialize the client."""
        self.server_url = server_url.rstrip("/")
        self.debug = debug
        self.client = httpx.Client(follow_redirects=True)
        self.session_id = None  # Will be obtained from server during initialization
        self.server_capabilities = None
        self.protocol_version = "2025-03-26"  # Default protocol version
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
    
    def initialize(self) -> bool:
        """Initialize the connection to the MCP server.
        
        According to the specification, this sends an initialize request and
        receives a session ID from the server.
        """
        logger.info(f"Initializing connection to MCP server at {self.server_url}")
        
        try:
            # Send initialize request
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "client_info": {
                        "name": "MCP Reference Client Test",
                        "version": "1.0.0"
                    },
                    "client_capabilities": {
                        "protocol_versions": [self.protocol_version]
                    }
                }
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            # Make the request to the mcp endpoint
            response = self.client.post(
                f"{self.server_url}/mcp",
                json=init_payload,
                headers=headers
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"Failed to initialize: {response.status_code} {response.text}")
                return False
            
            # Parse response
            response_data = response.json()
            logger.debug(f"Initialize response: {response_data}")
            
            if "error" in response_data:
                logger.error(f"Initialize error: {response_data['error']}")
                return False
            
            if "result" not in response_data:
                logger.error("No result in initialize response")
                return False
            
            # Extract session ID and server capabilities
            result = response_data["result"]
            self.session_id = result.get("session_id")
            self.server_capabilities = result.get("server_capabilities", {})
            
            if not self.session_id:
                logger.error("No session_id in initialize response")
                return False
            
            logger.info(f"Received session ID: {self.session_id}")
            logger.info(f"Server capabilities: {self.server_capabilities}")
            
            # Check if server supports our protocol version
            server_protocols = self.server_capabilities.get("protocol_versions", [])
            if self.protocol_version not in server_protocols:
                logger.error(f"Server does not support protocol version {self.protocol_version}")
                logger.error(f"Server supports: {server_protocols}")
                return False
            
            # Send initialized notification
            initialized_payload = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            initialized_url = f"{self.server_url}/mcp?session_id={self.session_id}"
            initialized_response = self.client.post(
                initialized_url,
                json=initialized_payload,
                headers=headers
            )
            
            if initialized_response.status_code != 202:
                logger.warning(f"Expected 202 for initialized notification, got {initialized_response.status_code}")
            
            logger.info("Successfully initialized connection")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing connection: {e}")
            return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools on the server."""
        logger.info("Listing available tools")
        
        if not self.session_id:
            logger.error("Not initialized: No session ID available")
            return []
        
        try:
            # Create request
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Include session ID as query parameter
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            # Make the request
            response = self.client.post(
                url,
                json=payload,
                headers=headers
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"Failed to list tools: {response.status_code} {response.text}")
                return []
            
            # Parse response
            response_data = response.json()
            logger.debug(f"List tools response: {response_data}")
            
            if "error" in response_data:
                logger.error(f"List tools error: {response_data['error']}")
                return []
            
            if "result" not in response_data:
                logger.error("No result in list_tools response")
                return []
            
            # Extract tools
            tools = response_data["result"].get("tools", [])
            logger.info(f"Found {len(tools)} tools")
            for tool in tools:
                logger.info(f"Tool: {tool.get('name')} - {tool.get('description')}")
            
            return tools
        
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call a tool on the server."""
        logger.info(f"Calling tool {tool_name} with params {params}")
        
        if not self.session_id:
            logger.error("Not initialized: No session ID available")
            return None
        
        try:
            # Create request
            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Include session ID as query parameter
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            # Make the request
            response = self.client.post(
                url,
                json=payload,
                headers=headers
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"Failed to call tool: {response.status_code} {response.text}")
                return None
            
            # Parse response
            response_data = response.json()
            logger.debug(f"Call tool response: {response_data}")
            
            if "error" in response_data:
                logger.error(f"Call tool error: {response_data['error']}")
                return None
            
            if "result" not in response_data:
                logger.error("No result in call_tool response")
                return None
            
            # Extract result
            result = response_data["result"].get("output")
            logger.info(f"Tool result: {result}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error calling tool: {e}")
            return None
    
    def send_batch_request(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send a batch of requests to the server."""
        logger.info(f"Sending batch of {len(requests)} requests")
        
        if not self.session_id:
            logger.error("Not initialized: No session ID available")
            return []
        
        try:
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Include session ID as query parameter
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            # Make the request
            response = self.client.post(
                url,
                json=requests,
                headers=headers
            )
            
            # Check response
            if response.status_code != 200:
                logger.error(f"Failed to send batch request: {response.status_code} {response.text}")
                return []
            
            # Parse response
            response_data = response.json()
            
            if not isinstance(response_data, list):
                logger.error(f"Batch response is not a list: {response_data}")
                return []
            
            logger.info(f"Received {len(response_data)} responses for batch request")
            return response_data
        
        except Exception as e:
            logger.error(f"Error sending batch request: {e}")
            return []
    
    def ping(self) -> bool:
        """Send a ping to test server connectivity."""
        logger.info("Sending ping")
        
        if not self.session_id:
            logger.error("Not initialized: No session ID available")
            return False
        
        try:
            # Create request
            payload = {
                "jsonrpc": "2.0",
                "id": "ping-1",
                "method": "ping"
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Include session ID as query parameter
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            # Record start time
            start_time = time.time()
            
            # Make the request
            response = self.client.post(
                url,
                json=payload,
                headers=headers
            )
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Check response
            if response.status_code != 200:
                logger.error(f"Failed to ping: {response.status_code} {response.text}")
                return False
            
            # Parse response
            response_data = response.json()
            
            if "error" in response_data:
                logger.error(f"Ping error: {response_data['error']}")
                return False
            
            logger.info(f"Ping successful in {elapsed:.3f} seconds")
            return True
        
        except Exception as e:
            logger.error(f"Error pinging server: {e}")
            return False
    
    def get_stream(self) -> Optional[httpx.Response]:
        """Get a Server-Sent Events stream from the server."""
        logger.info("Opening SSE stream")
        
        if not self.session_id:
            logger.error("Not initialized: No session ID available")
            return None
        
        try:
            # Set headers
            headers = {
                "Accept": "text/event-stream"
            }
            
            # Include session ID as query parameter
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            # Make the request
            response = self.client.get(
                url,
                headers=headers,
                timeout=None  # Don't timeout, this is a long-lived connection
            )
            
            # Check response content type
            if response.status_code != 200 or "text/event-stream" not in response.headers.get("Content-Type", ""):
                logger.error(f"Failed to open SSE stream: {response.status_code} {response.headers.get('Content-Type', 'unknown')}")
                return None
            
            logger.info("Successfully opened SSE stream")
            return response
        
        except Exception as e:
            logger.error(f"Error opening SSE stream: {e}")
            return None
    
    def close(self):
        """Close the connection to the server."""
        self.client.close()


class McpTester:
    """Tests an MCP server using the reference client."""
    
    def __init__(self, server_url: str, debug: bool = False):
        """Initialize the tester."""
        self.server_url = server_url
        self.debug = debug
        self.client = None
        self.results = {}
    
    def run_tests(self) -> bool:
        """Run all tests."""
        # Create client
        self.client = McpReferenceClient(self.server_url, self.debug)
        
        # Run tests
        success = True
        
        # Initialize
        if not self.client.initialize():
            self.results["initialize"] = {
                "status": "failed",
                "error": "Failed to initialize connection"
            }
            success = False
            self.client.close()
            return success
        
        self.results["initialize"] = {
            "status": "success",
            "session_id": self.client.session_id
        }
        
        # List tools
        tools = self.client.list_tools()
        if not tools:
            self.results["tools"] = {
                "status": "failed",
                "error": "Failed to list tools"
            }
            success = False
        else:
            self.results["tools"] = {
                "status": "success",
                "count": len(tools),
                "names": [t.get("name") for t in tools]
            }
            
            # Run tool tests if we have tools
            tool_names = [t.get("name") for t in tools]
            
            # Test echo tool
            if "echo" in tool_names:
                success = self.test_echo() and success
            else:
                self.results["echo"] = {
                    "status": "skipped",
                    "reason": "Tool not available"
                }
            
            # Test add tool
            if "add" in tool_names:
                success = self.test_add() and success
            else:
                self.results["add"] = {
                    "status": "skipped",
                    "reason": "Tool not available"
                }
            
            # Test sleep tool
            if "sleep" in tool_names:
                success = self.test_sleep() and success
            else:
                self.results["sleep"] = {
                    "status": "skipped",
                    "reason": "Tool not available"
                }
        
        # Test batch requests
        success = self.test_batch_request() and success
        
        # Test ping
        success = self.test_ping() and success
        
        # Test server-side events stream
        success = self.test_sse_stream() and success
        
        # Close connection
        self.client.close()
        
        return success
    
    def test_echo(self) -> bool:
        """Test the echo tool."""
        try:
            # Send a unique message
            message = f"Hello from MCP Reference Client! Test at {datetime.now().isoformat()}"
            
            # Record time for performance testing
            start_time = time.time()
            
            # Call the echo tool
            result = self.client.call_tool("echo", {"message": message})
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Check the result
            if result == message:
                self.results["echo"] = {
                    "status": "success",
                    "message": message,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
                return True
            else:
                self.results["echo"] = {
                    "status": "failed",
                    "message": message,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
                return False
        except Exception as e:
            self.results["echo"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def test_add(self) -> bool:
        """Test the add tool."""
        try:
            # Use floating point numbers to test precision
            a, b = 42.5, 13.25
            expected = a + b
            
            # Record time for performance testing
            start_time = time.time()
            
            # Call the add tool
            result = self.client.call_tool("add", {"a": a, "b": b})
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Check the result
            if result is not None and abs(float(result) - expected) < 0.0001:
                self.results["add"] = {
                    "status": "success",
                    "a": a,
                    "b": b,
                    "expected": expected,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
                return True
            else:
                self.results["add"] = {
                    "status": "failed",
                    "a": a,
                    "b": b,
                    "expected": expected,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
                return False
        except Exception as e:
            self.results["add"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def test_sleep(self) -> bool:
        """Test the sleep tool."""
        try:
            # Short sleep to avoid long test times
            seconds = 1.0
            
            # Record time for performance testing
            start_time = time.time()
            
            # Call the sleep tool
            result = self.client.call_tool("sleep", {"seconds": seconds})
            
            # Calculate actual elapsed time
            elapsed = time.time() - start_time
            
            # Check if the elapsed time is reasonable (at least the sleep duration)
            if elapsed >= seconds:
                self.results["sleep"] = {
                    "status": "success",
                    "seconds": seconds,
                    "result": result,
                    "elapsed_seconds": elapsed
                }
                return True
            else:
                self.results["sleep"] = {
                    "status": "warning",
                    "seconds": seconds,
                    "result": result,
                    "elapsed_seconds": elapsed,
                    "reason": f"Elapsed time {elapsed:.2f}s is less than requested {seconds}s"
                }
                return False
        except Exception as e:
            self.results["sleep"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def test_batch_request(self) -> bool:
        """Test batch requests."""
        try:
            # Create a batch with a ping and tools/list
            batch_requests = [
                {
                    "jsonrpc": "2.0",
                    "id": "batch-ping",
                    "method": "ping"
                },
                {
                    "jsonrpc": "2.0",
                    "id": "batch-tools-list",
                    "method": "tools/list"
                }
            ]
            
            # Record time for performance testing
            start_time = time.time()
            
            # Send the batch request
            results = self.client.send_batch_request(batch_requests)
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Check the results
            if len(results) == 2:
                # Check if the IDs match
                response_ids = [r.get("id") for r in results]
                
                if "batch-ping" in response_ids and "batch-tools-list" in response_ids:
                    self.results["batch"] = {
                        "status": "success",
                        "responses": len(results),
                        "elapsed_seconds": elapsed
                    }
                    return True
                else:
                    self.results["batch"] = {
                        "status": "failed",
                        "reason": f"Response IDs don't match request IDs. Got: {response_ids}",
                        "elapsed_seconds": elapsed
                    }
                    return False
            else:
                self.results["batch"] = {
                    "status": "failed",
                    "reason": f"Expected 2 responses, got {len(results)}",
                    "elapsed_seconds": elapsed
                }
                return False
        except Exception as e:
            self.results["batch"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def test_ping(self) -> bool:
        """Test the ping utility."""
        try:
            # Record time for performance testing
            start_time = time.time()
            
            # Send ping
            success = self.client.ping()
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            if success:
                self.results["ping"] = {
                    "status": "success",
                    "elapsed_seconds": elapsed
                }
                return True
            else:
                self.results["ping"] = {
                    "status": "failed",
                    "reason": "Ping failed",
                    "elapsed_seconds": elapsed
                }
                return False
        except Exception as e:
            self.results["ping"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def test_sse_stream(self) -> bool:
        """Test Server-Sent Events stream."""
        try:
            # Try to open an SSE stream
            stream = self.client.get_stream()
            
            if stream is not None:
                # Just test that we can open the stream, don't wait for events
                stream.close()
                
                self.results["sse"] = {
                    "status": "success",
                    "message": "Successfully opened SSE stream"
                }
                return True
            else:
                self.results["sse"] = {
                    "status": "failed",
                    "reason": "Failed to open SSE stream"
                }
                return False
        except Exception as e:
            self.results["sse"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    def print_results(self):
        """Print test results."""
        print("\n=== MCP Reference Client Test Results ===")
        print(f"Server: {self.server_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Initialization
        init_result = self.results.get("initialize", {})
        print("\nInitialization:")
        if init_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Session ID: {init_result.get('session_id')}")
        else:
            print(f"  Status: ❌ Failed - {init_result.get('error')}")
        
        # Tools
        tools_result = self.results.get("tools", {})
        print("\nTools:")
        if tools_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Count: {tools_result.get('count')}")
            print(f"  Available: {', '.join(tools_result.get('names', []))}")
        else:
            print(f"  Status: ❌ Failed - {tools_result.get('error')}")
        
        # Echo test results
        print("\nEcho Tool Test:")
        echo_result = self.results.get("echo", {})
        if echo_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Message: \"{echo_result.get('message')}\"")
            print(f"  Response time: {echo_result.get('elapsed_seconds', 0):.3f} seconds")
        elif echo_result.get("status") == "skipped":
            print(f"  Status: ⚠️ Skipped - {echo_result.get('reason')}")
        else:
            print(f"  Status: ❌ Failed - {echo_result.get('error')}")
        
        # Add test results
        print("\nAdd Tool Test:")
        add_result = self.results.get("add", {})
        if add_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Operation: {add_result.get('a')} + {add_result.get('b')} = {add_result.get('result')}")
            print(f"  Response time: {add_result.get('elapsed_seconds', 0):.3f} seconds")
        elif add_result.get("status") == "skipped":
            print(f"  Status: ⚠️ Skipped - {add_result.get('reason')}")
        else:
            print(f"  Status: ❌ Failed - {add_result.get('error')}")
        
        # Sleep test results
        print("\nSleep Tool Test:")
        sleep_result = self.results.get("sleep", {})
        if sleep_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Requested sleep: {sleep_result.get('seconds')} seconds")
            print(f"  Actual duration: {sleep_result.get('elapsed_seconds', 0):.3f} seconds")
        elif sleep_result.get("status") == "warning":
            print(f"  Status: ⚠️ Warning - {sleep_result.get('reason')}")
            print(f"  Requested sleep: {sleep_result.get('seconds')} seconds")
            print(f"  Actual duration: {sleep_result.get('elapsed_seconds', 0):.3f} seconds")
        elif sleep_result.get("status") == "skipped":
            print(f"  Status: ⚠️ Skipped - {sleep_result.get('reason')}")
        else:
            print(f"  Status: ❌ Failed - {sleep_result.get('error')}")
        
        # Batch test results
        print("\nBatch Request Test:")
        batch_result = self.results.get("batch", {})
        if batch_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Responses: {batch_result.get('responses')}")
            print(f"  Response time: {batch_result.get('elapsed_seconds', 0):.3f} seconds")
        else:
            print(f"  Status: ❌ Failed - {batch_result.get('reason', batch_result.get('error'))}")
        
        # Ping test results
        print("\nPing Test:")
        ping_result = self.results.get("ping", {})
        if ping_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Response time: {ping_result.get('elapsed_seconds', 0):.3f} seconds")
        else:
            print(f"  Status: ❌ Failed - {ping_result.get('reason', ping_result.get('error'))}")
        
        # SSE stream test results
        print("\nServer-Sent Events Stream Test:")
        sse_result = self.results.get("sse", {})
        if sse_result.get("status") == "success":
            print(f"  Status: ✅ Success")
            print(f"  Message: {sse_result.get('message')}")
        else:
            print(f"  Status: ❌ Failed - {sse_result.get('reason', sse_result.get('error'))}")
        
        # Summary
        success_count = sum(1 for k, v in self.results.items() 
                           if v.get("status") == "success")
        total_count = len(self.results)
        
        print(f"\nSummary: {success_count}/{total_count} tests passed")

def main():
    """Run the tests."""
    parser = argparse.ArgumentParser(description="Test MCP server using the reference client")
    parser.add_argument("--server-url", default="http://localhost:8088", help="URL of the MCP server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Create and run the tester
    tester = McpTester(args.server_url, args.debug)
    
    # Run the tests
    success = tester.run_tests()
    
    # Print results
    tester.print_results()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 