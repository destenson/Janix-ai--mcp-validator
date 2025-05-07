#!/usr/bin/env python3
"""
MCP HTTP Compliance Test

A comprehensive test suite for validating MCP HTTP servers against the specification.
This test script verifies that HTTP servers implement the protocol correctly according
to the 2025-03-26 specification.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import uuid
import os

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-http-compliance-test")

class McpHttpComplianceTest:
    """Tests MCP HTTP servers against the specification."""
    
    def __init__(self, server_url: str, debug: bool = False):
        """Initialize the tester."""
        self.server_url = server_url.rstrip("/")
        self.debug = debug
        self.client = httpx.Client(follow_redirects=True)
        self.session_id = None
        self.results = {}
        self.protocol_version = "2025-03-26"  # Default protocol version
        self.test_start_time = None
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
    
    def run_tests(self) -> bool:
        """Run all compliance tests."""
        self.test_start_time = time.time()
        success = True
        
        # Test 1: Initialization
        if not self.test_initialization():
            success = False
            # Initialization failed, can't continue
            return success
        
        # Test 2: Basic tools functionality
        if not self.test_tools_functionality():
            success = False
        
        # Test 3: Error handling
        if not self.test_error_handling():
            success = False
        
        # Test 4: Batch requests
        if not self.test_batch_requests():
            success = False
        
        # Test 5: Session management
        if not self.test_session_management():
            success = False
        
        # Test 6: Protocol negotiation
        if not self.test_protocol_negotiation():
            success = False
            
        # Test 7: Ping utility
        if not self.test_ping():
            success = False
        
        return success
    
    def test_initialization(self) -> bool:
        """Test initialization according to specification."""
        logger.info("Testing initialization")
        
        try:
            # Send initialize request
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "client_info": {
                        "name": "MCP HTTP Compliance Test",
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
            
            # Make the request to the messages endpoint
            response = self.client.post(
                f"{self.server_url}/messages",
                json=init_payload,
                headers=headers
            )
            
            # Check response status code
            if response.status_code != 200:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": f"Expected 200 status, got {response.status_code}",
                    "response": response.text
                }
                return False
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": "Failed to parse JSON response",
                    "response": response.text
                }
                return False
            
            logger.debug(f"Initialize response: {response_data}")
            
            # Check for JSONRPC format
            if "jsonrpc" not in response_data or response_data["jsonrpc"] != "2.0":
                self.results["initialization"] = {
                    "status": "failed",
                    "error": "Response missing 'jsonrpc': '2.0' field",
                    "response": response_data
                }
                return False
            
            # Check for matching ID
            if "id" not in response_data or response_data["id"] != 1:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": f"Response ID mismatch or missing, expected 1, got {response_data.get('id')}",
                    "response": response_data
                }
                return False
            
            # Check for result
            if "result" not in response_data:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": "Response missing 'result' field",
                    "response": response_data
                }
                return False
            
            # Check for required fields in result
            result = response_data["result"]
            required_fields = ["protocol_version", "server_info", "server_capabilities"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": f"Response missing required fields: {missing_fields}",
                    "response": response_data
                }
                return False
            
            # Check protocol version
            if result["protocol_version"] != self.protocol_version:
                self.results["initialization"] = {
                    "status": "failed",
                    "error": f"Protocol version mismatch: expected {self.protocol_version}, got {result['protocol_version']}",
                    "response": response_data
                }
                return False
            
            # Extract session ID from headers
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]
                logger.info(f"Received session ID in header: {self.session_id}")
            else:
                # Session ID might be in the response body
                self.session_id = result.get("session_id")
                if self.session_id:
                    logger.info(f"Received session ID in response body: {self.session_id}")
                else:
                    logger.warning("No session ID received from server")
            
            # Send initialized notification
            if self.session_id:
                initialized_payload = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                
                initialized_url = f"{self.server_url}/messages?session_id={self.session_id}"
                initialized_response = self.client.post(
                    initialized_url,
                    json=initialized_payload,
                    headers=headers
                )
                
                if initialized_response.status_code != 202:
                    logger.warning(f"Expected 202 for initialized notification, got {initialized_response.status_code}")
            
            self.results["initialization"] = {
                "status": "success",
                "protocol_version": result["protocol_version"],
                "server_info": result["server_info"],
                "session_id": self.session_id,
                "server_capabilities": result["server_capabilities"]
            }
            
            return True
        
        except Exception as e:
            self.results["initialization"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during initialization test")
            return False
    
    def test_tools_functionality(self) -> bool:
        """Test basic tools functionality."""
        logger.info("Testing tools functionality")
        
        if not self.session_id:
            self.results["tools_functionality"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        try:
            # Test tools/list
            tools_list_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            url = f"{self.server_url}/messages?session_id={self.session_id}"
            
            tools_list_response = self.client.post(
                url,
                json=tools_list_payload,
                headers=headers
            )
            
            if tools_list_response.status_code != 200:
                self.results["tools_functionality"] = {
                    "status": "failed",
                    "error": f"tools/list expected 200 status, got {tools_list_response.status_code}",
                    "response": tools_list_response.text
                }
                return False
            
            tools_list_data = tools_list_response.json()
            
            if "result" not in tools_list_data or "tools" not in tools_list_data["result"]:
                self.results["tools_functionality"] = {
                    "status": "failed",
                    "error": "tools/list missing required fields in response",
                    "response": tools_list_data
                }
                return False
            
            tools = tools_list_data["result"]["tools"]
            
            # Check if we have the basic required tools
            tool_names = [tool.get("name") for tool in tools]
            required_tools = ["echo"]
            missing_tools = [tool for tool in required_tools if tool not in tool_names]
            
            if missing_tools:
                logger.warning(f"Server missing recommended tools: {missing_tools}")
            
            # Try to call the echo tool if available
            if "echo" in tool_names:
                echo_message = f"Test message at {datetime.now().isoformat()}"
                echo_payload = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "echo",
                        "arguments": {
                            "message": echo_message
                        }
                    }
                }
                
                echo_response = self.client.post(
                    url,
                    json=echo_payload,
                    headers=headers
                )
                
                if echo_response.status_code != 200:
                    self.results["tools_functionality"] = {
                        "status": "failed",
                        "error": f"echo tool call expected 200 status, got {echo_response.status_code}",
                        "response": echo_response.text
                    }
                    return False
                
                echo_data = echo_response.json()
                
                if "result" not in echo_data:
                    self.results["tools_functionality"] = {
                        "status": "failed",
                        "error": "echo tool response missing 'result'",
                        "response": echo_data
                    }
                    return False
                
                echo_result = echo_data["result"]
                
                if "output" not in echo_result or echo_result["output"] != echo_message:
                    self.results["tools_functionality"] = {
                        "status": "failed",
                        "error": f"Echo tool output mismatch: sent '{echo_message}', received '{echo_result.get('output')}'",
                        "response": echo_data
                    }
                    return False
            
            self.results["tools_functionality"] = {
                "status": "success",
                "available_tools": tool_names,
                "echo_test": "echo" in tool_names
            }
            
            return True
        
        except Exception as e:
            self.results["tools_functionality"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during tools functionality test")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling."""
        logger.info("Testing error handling")
        
        if not self.session_id:
            self.results["error_handling"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        try:
            url = f"{self.server_url}/messages?session_id={self.session_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            # Test 1: Invalid method
            invalid_method_payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "non_existent_method"
            }
            
            invalid_method_response = self.client.post(
                url,
                json=invalid_method_payload,
                headers=headers
            )
            
            # Should still return 200 but with error in response
            if invalid_method_response.status_code != 200:
                logger.warning(f"Invalid method expected 200 status, got {invalid_method_response.status_code}")
            
            invalid_method_data = invalid_method_response.json()
            
            if "error" not in invalid_method_data:
                self.results["error_handling"] = {
                    "status": "failed",
                    "error": "Server did not return error for invalid method",
                    "response": invalid_method_data
                }
                return False
            
            error = invalid_method_data["error"]
            if "code" not in error or error["code"] != -32601:  # Method not found
                logger.warning(f"Expected error code -32601 for method not found, got {error.get('code')}")
            
            # Test 2: Invalid params
            if "echo" in self.results.get("tools_functionality", {}).get("available_tools", []):
                invalid_params_payload = {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "echo",
                        # Missing required 'arguments' field
                    }
                }
                
                invalid_params_response = self.client.post(
                    url,
                    json=invalid_params_payload,
                    headers=headers
                )
                
                invalid_params_data = invalid_params_response.json()
                
                if "error" not in invalid_params_data:
                    self.results["error_handling"] = {
                        "status": "failed",
                        "error": "Server did not return error for invalid params",
                        "response": invalid_params_data
                    }
                    return False
                
                error = invalid_params_data["error"]
                if "code" not in error or error["code"] != -32602:  # Invalid params
                    logger.warning(f"Expected error code -32602 for invalid params, got {error.get('code')}")
            
            # Test 3: Invalid JSON
            invalid_json_response = self.client.post(
                url,
                content="{ this is not valid JSON",
                headers=headers
            )
            
            # Should return 400 Bad Request for invalid JSON
            if invalid_json_response.status_code != 400:
                logger.warning(f"Invalid JSON expected 400 status, got {invalid_json_response.status_code}")
            
            self.results["error_handling"] = {
                "status": "success",
                "tests_passed": 3
            }
            
            return True
        
        except Exception as e:
            self.results["error_handling"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during error handling test")
            return False
    
    def test_batch_requests(self) -> bool:
        """Test batch requests."""
        logger.info("Testing batch requests")
        
        if not self.session_id:
            self.results["batch_requests"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        try:
            url = f"{self.server_url}/messages?session_id={self.session_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            # Create a batch with two requests
            batch_payload = [
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "ping"
                },
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/list"
                }
            ]
            
            batch_response = self.client.post(
                url,
                json=batch_payload,
                headers=headers
            )
            
            if batch_response.status_code != 200:
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"Batch request expected 200 status, got {batch_response.status_code}",
                    "response": batch_response.text
                }
                return False
            
            batch_data = batch_response.json()
            
            if not isinstance(batch_data, list):
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": "Batch response is not a list",
                    "response": batch_data
                }
                return False
            
            if len(batch_data) != 2:
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"Expected 2 responses in batch, got {len(batch_data)}",
                    "response": batch_data
                }
                return False
            
            # Check IDs match requests
            response_ids = [resp.get("id") for resp in batch_data]
            if 6 not in response_ids or 7 not in response_ids:
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"Response IDs don't match request IDs, expected [6, 7], got {response_ids}",
                    "response": batch_data
                }
                return False
            
            self.results["batch_requests"] = {
                "status": "success"
            }
            
            return True
        
        except Exception as e:
            self.results["batch_requests"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during batch requests test")
            return False
    
    def test_session_management(self) -> bool:
        """Test session management."""
        logger.info("Testing session management")
        
        try:
            # Request without session ID should fail or create a new session
            no_session_payload = {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "ping"
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            no_session_response = self.client.post(
                f"{self.server_url}/messages",
                json=no_session_payload,
                headers=headers
            )
            
            # Should either return 400 (required session) or 200 (auto-session)
            if no_session_response.status_code not in [200, 400]:
                self.results["session_management"] = {
                    "status": "failed",
                    "error": f"Expected 200 or 400 status for no session, got {no_session_response.status_code}",
                    "response": no_session_response.text
                }
                return False
            
            # Test invalid session ID
            invalid_session_url = f"{self.server_url}/messages?session_id=invalid-session-id-{uuid.uuid4()}"
            invalid_session_response = self.client.post(
                invalid_session_url,
                json=no_session_payload,
                headers=headers
            )
            
            # Should return 404 Not Found for invalid session
            if invalid_session_response.status_code != 404:
                logger.warning(f"Invalid session expected 404 status, got {invalid_session_response.status_code}")
            
            self.results["session_management"] = {
                "status": "success",
                "no_session_response": no_session_response.status_code,
                "invalid_session_response": invalid_session_response.status_code
            }
            
            return True
        
        except Exception as e:
            self.results["session_management"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during session management test")
            return False
    
    def test_protocol_negotiation(self) -> bool:
        """Test protocol version negotiation."""
        logger.info("Testing protocol negotiation")
        
        try:
            # Try with an unsupported protocol version
            unsupported_version = "3000-01-01"
            
            init_payload = {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "initialize",
                "params": {
                    "client_info": {
                        "name": "MCP HTTP Compliance Test",
                        "version": "1.0.0"
                    },
                    "client_capabilities": {
                        "protocol_versions": [unsupported_version]
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Create a new client for this test to avoid session ID issues
            test_client = httpx.Client(follow_redirects=True)
            
            response = test_client.post(
                f"{self.server_url}/messages",
                json=init_payload,
                headers=headers
            )
            
            test_client.close()
            
            # Server should either:
            # 1. Return an error (preferred)
            # 2. Return a different supported version
            
            if response.status_code == 200:
                response_data = response.json()
                
                if "result" in response_data:
                    server_version = response_data["result"].get("protocol_version")
                    
                    if server_version == unsupported_version:
                        self.results["protocol_negotiation"] = {
                            "status": "failed",
                            "error": f"Server accepted unsupported version {unsupported_version}",
                            "response": response_data
                        }
                        return False
                    else:
                        logger.info(f"Server negotiated to supported version: {server_version}")
                elif "error" in response_data:
                    logger.info("Server correctly rejected unsupported version")
                else:
                    self.results["protocol_negotiation"] = {
                        "status": "failed",
                        "error": "Unexpected response format",
                        "response": response_data
                    }
                    return False
            else:
                logger.warning(f"Unexpected status code for protocol negotiation: {response.status_code}")
            
            self.results["protocol_negotiation"] = {
                "status": "success"
            }
            
            return True
        
        except Exception as e:
            self.results["protocol_negotiation"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during protocol negotiation test")
            return False
    
    def test_ping(self) -> bool:
        """Test ping utility."""
        logger.info("Testing ping utility")
        
        if not self.session_id:
            self.results["ping"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        try:
            url = f"{self.server_url}/messages?session_id={self.session_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            ping_payload = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "ping"
            }
            
            start_time = time.time()
            ping_response = self.client.post(
                url,
                json=ping_payload,
                headers=headers
            )
            elapsed = time.time() - start_time
            
            if ping_response.status_code != 200:
                self.results["ping"] = {
                    "status": "failed",
                    "error": f"Ping expected 200 status, got {ping_response.status_code}",
                    "response": ping_response.text
                }
                return False
            
            ping_data = ping_response.json()
            
            if "result" not in ping_data:
                self.results["ping"] = {
                    "status": "failed",
                    "error": "Ping response missing 'result'",
                    "response": ping_data
                }
                return False
            
            self.results["ping"] = {
                "status": "success",
                "elapsed_seconds": elapsed
            }
            
            return True
        
        except Exception as e:
            self.results["ping"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during ping test")
            return False
    
    def print_results(self):
        """Print test results."""
        print("\n=== MCP HTTP Compliance Test Results ===")
        print(f"Server: {self.server_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Protocol Version: {self.protocol_version}")
        
        # Print results for each test
        for test_name, result in self.results.items():
            status = result.get("status", "unknown")
            
            if status == "success":
                status_display = "✅ Success"
            elif status == "failed":
                status_display = "❌ Failed"
            elif status == "skipped":
                status_display = "⚠️ Skipped"
            elif status == "error":
                status_display = "❌ Error"
            else:
                status_display = "? Unknown"
            
            print(f"\n{test_name.replace('_', ' ').title()}:")
            print(f"  Status: {status_display}")
            
            # Print additional details based on test
            if status == "failed" or status == "error":
                print(f"  Error: {result.get('error', 'Unknown error')}")
            elif status == "skipped":
                print(f"  Reason: {result.get('reason', 'Unknown reason')}")
            else:
                # Print test-specific successful results
                if test_name == "initialization":
                    print(f"  Protocol Version: {result.get('protocol_version')}")
                    print(f"  Server Info: {result.get('server_info')}")
                    print(f"  Session ID: {result.get('session_id')}")
                elif test_name == "tools_functionality":
                    print(f"  Available Tools: {', '.join(result.get('available_tools', []))}")
                elif test_name == "ping":
                    print(f"  Response Time: {result.get('elapsed_seconds', 0):.3f} seconds")
        
        # Summary
        success_count = sum(1 for result in self.results.values() if result.get("status") == "success")
        total_count = len(self.results)
        skipped_count = sum(1 for result in self.results.values() if result.get("status") == "skipped")
        
        print(f"\nSummary: {success_count}/{total_count} tests passed ({skipped_count} skipped)")

    def generate_report(self, output_dir: str = "reports") -> str:
        """Generate a detailed markdown report of the test results."""
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for the report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"http_compliance_test_{timestamp}.md")
        
        # Calculate test duration
        duration = time.time() - self.test_start_time if self.test_start_time else 0
        
        # Count successful tests
        success_count = sum(1 for result in self.results.values() if result.get("status") == "success")
        total_count = len(self.results)
        skipped_count = sum(1 for result in self.results.values() if result.get("status") == "skipped")
        
        # Generate markdown content
        lines = [
            "# MCP HTTP Server Compliance Report",
            "",
            "## Test Information",
            "",
            f"- **Server URL**: `{self.server_url}`",
            f"- **Protocol Version**: {self.protocol_version}",
            f"- **Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Test Duration**: {duration:.2f} seconds",
            "",
            "## Test Results Summary",
            "",
            f"- **Total Tests**: {total_count}",
            f"- **Passed**: {success_count}",
            f"- **Failed**: {total_count - success_count - skipped_count}",
            f"- **Skipped**: {skipped_count}",
            f"- **Success Rate**: {(success_count / (total_count - skipped_count) * 100):.1f}%",
            "",
            "## Detailed Results",
            ""
        ]
        
        # Add detailed results for each test
        for test_name, result in self.results.items():
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
            
            lines.extend([
                f"### {test_name.replace('_', ' ').title()}",
                "",
                f"**Status**: {status_icon} {status.title()}"
            ])
            
            # Add test-specific details
            if status == "success":
                if test_name == "initialization":
                    lines.extend([
                        "",
                        "**Details**:",
                        f"- Protocol Version: {result.get('protocol_version')}",
                        f"- Server Info: {result.get('server_info')}",
                        f"- Session ID: {result.get('session_id')}"
                    ])
                elif test_name == "tools_functionality":
                    lines.extend([
                        "",
                        "**Details**:",
                        f"- Available Tools: {', '.join(result.get('available_tools', []))}"
                    ])
                elif test_name == "ping":
                    lines.extend([
                        "",
                        "**Details**:",
                        f"- Response Time: {result.get('elapsed_seconds', 0):.3f} seconds"
                    ])
            elif status in ["failed", "error"]:
                lines.extend([
                    "",
                    "**Error Details**:",
                    f"```",
                    f"{result.get('error', 'No error details available')}",
                    f"```"
                ])
            
            lines.append("")  # Add blank line between sections
        
        # Write the report
        with open(report_file, "w") as f:
            f.write("\n".join(lines))
        
        return report_file

def main():
    """Run the tests."""
    parser = argparse.ArgumentParser(description="Test MCP HTTP server for specification compliance")
    parser.add_argument("--server-url", default="http://localhost:8088", help="URL of the MCP server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    args = parser.parse_args()
    
    # Create and run the tester
    tester = McpHttpComplianceTest(args.server_url, args.debug)
    
    # Run the tests
    success = tester.run_tests()
    
    # Print results to console
    tester.print_results()
    
    # Generate markdown report
    report_file = tester.generate_report(args.output_dir)
    logger.info(f"Compliance report generated: {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 