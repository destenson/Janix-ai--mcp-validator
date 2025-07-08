#!/usr/bin/env python3
"""
MCP HTTP Compliance Test

A comprehensive test suite for validating MCP HTTP servers against the specification.
This test script verifies that HTTP servers implement the protocol correctly according
to the 2025-06-18 specification.
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
import base64
import hashlib
import secrets
import urllib.parse
from urllib.parse import urlparse, urljoin

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-http-compliance-test")

# Standard JSON-RPC error codes
PARSE_ERROR = -32700  # Invalid JSON
INVALID_REQUEST = -32600  # Not a valid Request object
METHOD_NOT_FOUND = -32601  # Method doesn't exist/not available
INVALID_PARAMS = -32602  # Invalid method parameters
INTERNAL_ERROR = -32603  # Internal JSON-RPC error

# Server error codes
SERVER_ERROR = -32000  # Generic server error
SERVER_OVERLOADED = -32001  # Server temporarily unable to handle request
RATE_LIMIT_EXCEEDED = -32002  # Too many requests
SESSION_EXPIRED = -32003  # Session/auth expired

class McpHttpComplianceTest:
    """Tests MCP HTTP servers against the specification."""
    
    def __init__(self, server_url: str, debug: bool = False, test_oauth: bool = False):
        """Initialize the tester."""
        # Remove trailing /mcp if present to avoid double-appending
        self.server_url = server_url.rstrip("/").removesuffix("/mcp")
        self.debug = debug
        self.test_oauth = test_oauth
        self.client = httpx.Client(follow_redirects=True)
        self.session_id = None
        self.results = {}
        self.protocol_version = "2025-06-18"  # Default protocol version
        self.test_start_time = None
        
        # OAuth 2.1 support
        parsed_url = urlparse(server_url)
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.oauth_server_metadata = None
        self.bearer_token = None
        
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
        
        # Test 2: OAuth 2.1 authentication (if enabled)
        if self.test_oauth:
            if not self.test_oauth_authentication():
                success = False
        
        # Test 3: Basic tools functionality
        if not self.test_tools_functionality():
            success = False
        
        # Test 4: Error handling
        if not self.test_error_handling():
            success = False
        
        # Test 5: Batch requests
        if not self.test_batch_requests():
            success = False
        
        # Test 6: Session management
        if not self.test_session_management():
            success = False
        
        # Test 7: Protocol negotiation
        if not self.test_protocol_negotiation():
            success = False
            
        # Test 8: Ping utility
        if not self.test_ping():
            success = False
        
        return success
    
    def test_initialization(self) -> bool:
        """Test initialization according to specification."""
        logger.info("Testing initialization")
        
        try:
            # Send initialize request with camelCase parameter names
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {  # Changed from client_info
                        "name": "MCP HTTP Compliance Test",
                        "version": "1.0.0"
                    },
                    "clientCapabilities": {  # Changed from client_capabilities
                        "protocol_versions": [self.protocol_version]
                    }
                }
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            # Add MCP-Protocol-Version header for 2025-06-18
            if self.protocol_version == "2025-06-18":
                headers["MCP-Protocol-Version"] = self.protocol_version
            
            # Make the request to the mcp endpoint
            response = self.client.post(
                f"{self.server_url}/mcp",
                json=init_payload,
                headers=headers
            )
            
            # Validate response
            self.results["initialization"] = self.validate_initialization_response(response)
            
            return self.results["initialization"]["status"] == "success"
        
        except Exception as e:
            self.results["initialization"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during initialization test")
            return False
    
    def validate_initialization_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Validate the response from an initialize request."""
        
        if response.status_code != 200:
            return {
                "status": "failed",
                "error": f"Expected 200 status, got {response.status_code}",
                "response": response.text
            }
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "error": "Response is not valid JSON",
                "response": response.text
            }
            
        if "result" not in data:
            return {
                "status": "failed",
                "error": "Response missing 'result' object",
                "response": data
            }
        
        result = data["result"]
        protocol_version = result.get("protocolVersion")
        server_info = result.get("serverInfo")
        session_id = result.get("sessionId") or response.headers.get("mcp-session-id")

        if not all([protocol_version, server_info, session_id]):
            return {
                "status": "failed",
                "error": "Response missing one or more required fields (protocolVersion, serverInfo, sessionId)",
                "response": result
            }
            
        self.protocol_version = protocol_version
        self.session_id = session_id
        
        logger.info(f"Received session ID in header: {self.session_id}")
        
        return {
            "status": "success",
            "protocol_version": protocol_version,
            "server_info": server_info,
            "session_id": session_id
        }
    
    def fetch_oauth_server_metadata(self):
        """Fetch OAuth server metadata from .well-known/oauth-authorization-server."""
        logger.info("Fetching OAuth server metadata")
        try:
            well_known_url = urljoin(self.base_url, "/.well-known/oauth-authorization-server")
            logger.debug(f"Fetching OAuth server metadata from: {well_known_url}")
            
            response = self.client.get(well_known_url)
            if response.status_code == 200:
                metadata = response.json()
                self.oauth_server_metadata = metadata
                logger.debug(f"OAuth server metadata retrieved: {metadata}")
                return metadata
            else:
                logger.debug(f"OAuth server metadata not available, status: {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Failed to fetch OAuth server metadata: {str(e)}")
            return None
    
    def generate_pkce_challenge(self):
        """Generate PKCE code verifier and challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def handle_401_response(self, response):
        """Handle 401 Unauthorized responses according to OAuth 2.1 spec."""
        oauth_info = {
            "requires_auth": True,
            "www_authenticate": None,
            "oauth_metadata": None,
            "next_steps": []
        }
        
        # Parse WWW-Authenticate header
        www_authenticate = response.headers.get("WWW-Authenticate") or response.headers.get("www-authenticate")
        if www_authenticate:
            oauth_info["www_authenticate"] = www_authenticate
            logger.debug(f"Found WWW-Authenticate header: {www_authenticate}")
            
            # Parse Bearer challenge
            if "Bearer" in www_authenticate:
                oauth_info["scheme"] = "Bearer"
                challenge_params = {}
                parts = www_authenticate.replace("Bearer", "").strip().split(",")
                for part in parts:
                    if "=" in part:
                        key, value = part.strip().split("=", 1)
                        challenge_params[key.strip()] = value.strip().strip('"')
                oauth_info["challenge_params"] = challenge_params
                oauth_info["next_steps"].append("Parse Bearer challenge parameters")
        
        # Try to fetch OAuth server metadata
        if not self.oauth_server_metadata:
            metadata = self.fetch_oauth_server_metadata()
            if metadata:
                oauth_info["oauth_metadata"] = metadata
                oauth_info["next_steps"].append("Fetch OAuth server metadata")
        
        return oauth_info
    
    def test_oauth_authentication(self) -> bool:
        """Test OAuth 2.1 authentication compliance."""
        logger.info("Testing OAuth 2.1 authentication")
        
        test_payload = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 99 # Using a unique integer ID
        }
        
        base_headers = {
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self.protocol_version
        }

        try:
            # 1. Send request without any token, expect 401
            logger.debug("OAuth Test Step 1: No token")
            # Use the session-specific URL now that we are initialized
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            response = self.client.post(url, json=test_payload, headers=base_headers)
            if response.status_code != 401:
                self.results["oauth_authentication"] = {
                    "status": "failed", "details": f"Step 1 Failed: Expected 401 for no token, got {response.status_code}"
                }
                return False
            logger.debug("OAuth Test Step 1: Passed")

            # 2. Send request with a valid token, expect 200
            logger.debug("OAuth Test Step 2: Valid token")
            valid_headers = {**base_headers, "Authorization": "Bearer valid-test-token-123"}
            response = self.client.post(url, json=test_payload, headers=valid_headers)
            if response.status_code != 200:
                self.results["oauth_authentication"] = {
                    "status": "failed", "details": f"Step 2 Failed: Expected 200 for valid token, got {response.status_code}", "response": response.text
                }
                return False
            logger.debug("OAuth Test Step 2: Passed. Storing bearer token.")
            self.bearer_token = "valid-test-token-123"

            # 3. Send request with an invalid token, expect 401
            logger.debug("OAuth Test Step 3: Invalid token")
            invalid_headers = {**base_headers, "Authorization": "Bearer invalid-token"}
            response = self.client.post(url, json=test_payload, headers=invalid_headers)
            if response.status_code != 401:
                self.results["oauth_authentication"] = {
                    "status": "failed", "details": f"Step 3 Failed: Expected 401 for invalid token, got {response.status_code}"
                }
                return False
            logger.debug("OAuth Test Step 3: Passed")

            self.results["oauth_authentication"] = {"status": "success"}
            return True

        except Exception as e:
            logger.exception("Exception during OAuth authentication test")
            self.results["oauth_authentication"] = {"status": "error", "error": str(e)}
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if a bearer token is available."""
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

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
            
            headers = self._get_auth_headers()
            
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
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
            
            # Store available tools
            tool_names = [tool.get("name") for tool in tools]
            self.results["tools_functionality"] = {
                "status": "success",
                "available_tools": tool_names,
                "count": len(tool_names)
            }
            
            # Test the first available tool if any exist
            if tools:
                test_tool = tools[0]
                tool_name = test_tool.get("name")
                
                # Generate test parameters based on schema
                test_params = {}
                if "parameters" in test_tool:  # 2025-03-26
                    schema = test_tool["parameters"]
                    if "properties" in schema:
                        for prop_name, prop_details in schema["properties"].items():
                            prop_type = prop_details.get("type", "string")
                            if prop_type == "string":
                                test_params[prop_name] = "test_value"
                            elif prop_type in ["number", "integer"]:
                                test_params[prop_name] = 42
                            elif prop_type == "boolean":
                                test_params[prop_name] = True
                            elif prop_type == "array":
                                test_params[prop_name] = []
                            elif prop_type == "object":
                                test_params[prop_name] = {}
                elif "inputSchema" in test_tool:  # 2024-11-05
                    schema = test_tool["inputSchema"]
                    if "properties" in schema:
                        for prop_name, prop_details in schema["properties"].items():
                            prop_type = prop_details.get("type", "string")
                            if prop_type == "string":
                                test_params[prop_name] = "test_value"
                            elif prop_type in ["number", "integer"]:
                                test_params[prop_name] = 42
                            elif prop_type == "boolean":
                                test_params[prop_name] = True
                            elif prop_type == "array":
                                test_params[prop_name] = []
                            elif prop_type == "object":
                                test_params[prop_name] = {}
                
                tool_call_payload = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": test_params
                    }
                }
                
                tool_response = self.client.post(
                    url,
                    json=tool_call_payload,
                    headers=self._get_auth_headers()
                )
                
                if tool_response.status_code != 200:
                    self.results["tools_functionality"].update({
                        "status": "failed",
                        "error": f"Tool call expected 200 status, got {tool_response.status_code}",
                        "response": tool_response.text
                    })
                    return False
                
                tool_data = tool_response.json()
                
                if "result" not in tool_data:
                    self.results["tools_functionality"].update({
                        "status": "failed",
                        "error": "Tool response missing 'result'",
                        "response": tool_data
                    })
                    return False
                
                # Store successful tool test result
                self.results["tools_functionality"].update({
                    "tested_tool": tool_name,
                    "test_status": "success"
                })
            
            return True
        
        except Exception as e:
            self.results["tools_functionality"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during tools functionality test")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling according to specification."""
        logger.info("Testing error handling")
        
        if not self.session_id:
            self.results["error_handling"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        error_tests = {
            "parse_error": {
                "payload": "invalid json{",
                "expected_code": 400,
                "expected_error": -32700
            },
            "invalid_request": {
                "payload": {"not_jsonrpc": "2.0", "method": "test", "id": 1},
                "expected_code": 400,
                "expected_error": -32600
            },
            "method_not_found": {
                "payload": {
                    "jsonrpc": "2.0",
                    "method": "non_existent_method",
                    "id": 1
                },
                "expected_code": 200,  # Changed from 404 to 200 per JSON-RPC 2.0
                "expected_error": -32601
            },
            "invalid_params": {
                "payload": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",  # Changed from tools/execute to tools/call
                    "params": {"invalid": "params"},
                    "id": 1
                },
                "expected_code": 400,
                "expected_error": -32602
            },
            "session_expired": {
                "payload": {
                    "jsonrpc": "2.0",
                    "method": "ping",
                    "id": 1
                },
                "expected_code": 401,
                "expected_error": -32003,
                "use_invalid_session": True
            }
        }
        
        test_results = {}
        all_passed = True
        
        for test_name, test_config in error_tests.items():
            logger.info(f"Running error test: {test_name}")
            try:
                headers = self._get_auth_headers()
                
                # For session_expired test, we need to send an invalid session ID
                session_id = self.session_id
                if test_name == "session_expired":
                    session_id = "invalid-session-id"
                    headers["Mcp-Session-Id"] = session_id

                url = f"{self.server_url}/mcp"
                if session_id:
                     url += f"?session_id={session_id}"

                if isinstance(test_config["payload"], str):
                    response = self.client.post(
                        url,
                        content=test_config["payload"],
                        headers=headers
                    )
                else:
                    response = self.client.post(
                        url,
                        json=test_config["payload"],
                        headers=headers
                    )
                
                # Check status code
                status_matches = response.status_code == test_config["expected_code"]
                
                # For successful responses (200), check error code in response
                error_code_matches = False
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if "error" in response_data:
                            error_code_matches = response_data["error"].get("code") == test_config["expected_error"]
                    except:
                        error_code_matches = False
                else:
                    # For non-200 responses, we only care about the status code
                    error_code_matches = True
                
                test_passed = status_matches and error_code_matches
                
                if test_passed:
                    test_results[test_name] = {
                        "status": "success",
                        "details": f"Correct {test_config['expected_code']} response"
                    }
                    logger.debug(f"✅ {test_name} test passed")
                else:
                    test_results[test_name] = {
                        "status": "failed",
                        "details": f"Expected {test_config['expected_code']}, got {response.status_code}"
                    }
                    logger.debug(f"❌ {test_name} test failed")
                    if response.status_code == 200:
                        logger.debug(f"Response body: {response.text}")
                    all_passed = False
                
            except Exception as e:
                test_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.exception(f"Exception during {test_name} test")
                all_passed = False
        
        self.results["error_handling"] = {
            "status": "success" if all_passed else "failed",
            "tests": test_results
        }
        
        return all_passed
    
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
            # Send a batch request (array of requests)
            batch_request = [
                {"jsonrpc": "2.0", "method": "ping", "id": "1"},
                {"jsonrpc": "2.0", "method": "ping", "id": "2"}
            ]

            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            response = self.client.post(
                url,
                json=batch_request,
                headers=self._get_auth_headers()
            )
            
            # For 2025-06-18, batch requests are not supported and MUST return 400
            if self.protocol_version == "2025-06-18":
                if response.status_code == 400:
                    # Check that the error message mentions batching not supported
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "")
                        if "batch" in error_message.lower() and "not supported" in error_message.lower():
                            self.results["batch_requests"] = {
                                "status": "success",
                                "note": "Batch requests correctly rejected for 2025-06-18"
                            }
                            return True
                    except:
                        pass
                
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"2025-06-18 should reject batch requests with 400 status, got {response.status_code}",
                    "response": response.text
                }
                return False
            
            # For older protocol versions, batch requests should work
            if response.status_code != 200:
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"Batch request expected 200 status, got {response.status_code}",
                    "response": response.text
                }
                return False
            
            batch_data = response.json()
            
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
            if "1" not in response_ids or "2" not in response_ids:
                self.results["batch_requests"] = {
                    "status": "failed",
                    "error": f"Response IDs don't match request IDs, expected ['1', '2'], got {response_ids}",
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
        """Test session management capabilities."""
        logger.info("Testing session management")
        self.results["session_management"] = {}
        all_tests_passed = True
        
        # This test assumes a session has already been established
        if not self.session_id:
            self.results["session_management"] = {
                "status": "skipped",
                "reason": "No session ID available for testing"
            }
            return False
        
        try:
            # Test with no session ID
            no_session_response = self.client.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "ping"
                },
                headers=self._get_auth_headers()
            )
            
            # The server should respond with 400 Bad Request or 401 Unauthorized
            # if a session is required for the method
            if no_session_response.status_code not in [200, 400, 401]:
                self.results["session_management"]["no_session_test"] = {
                    "status": "failed",
                    "error": f"Expected 200, 400 or 401 status for no session, got {no_session_response.status_code}",
                    "response": no_session_response.text
                }
                all_tests_passed = False
            else:
                self.results["session_management"]["no_session_test"] = {
                    "status": "success",
                    "details": f"Server responded with {no_session_response.status_code} as expected"
                }

            # Test with invalid session ID
            invalid_session_id = str(uuid.uuid4())
            invalid_session_response = self.client.post(
                f"{self.server_url}/mcp?session_id={invalid_session_id}",
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "ping"
                },
                headers=self._get_auth_headers()
            )
            
            # Should be 401 Unauthorized as per 2025-06-18
            if invalid_session_response.status_code != 401:
                self.results["session_management"]["invalid_session_test"] = {
                    "status": "failed",
                    "error": f"Expected 401 status for invalid session, got {invalid_session_response.status_code}",
                    "response": invalid_session_response.text
                }
                all_tests_passed = False
            else:
                self.results["session_management"]["invalid_session_test"] = {
                    "status": "success",
                    "details": "Server responded with 401 as expected"
                }
        
        except Exception as e:
            self.results["session_management"] = {
                "status": "error",
                "error": str(e)
            }
            logger.exception("Exception during session management test")
            return False
        
        self.results["session_management"] = {
            "status": "success" if all_tests_passed else "failed",
            "tests": self.results["session_management"]
        }
        return all_tests_passed
    
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
                    "clientInfo": {  # Changed from client_info
                        "name": "MCP HTTP Compliance Test",
                        "version": "1.0.0"
                    },
                    "clientCapabilities": {  # Changed from client_capabilities
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
                f"{self.server_url}/mcp",
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
                    server_version = response_data["result"].get("protocolVersion") # Changed from protocol_version
                    
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
        """Test the simple ping utility."""
        logger.info("Testing ping utility")
        
        if not self.session_id:
            self.results["ping"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
            
        try:
            ping_payload = {
                "jsonrpc": "2.0",
                "id": "ping-test",
                "method": "ping"
            }
            
            start_time = time.time()
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            
            ping_response = self.client.post(
                url,
                json=ping_payload,
                headers=self._get_auth_headers()
            )
            
            elapsed = time.time() - start_time
            
            if ping_response.status_code != 200:
                self.results["ping"] = {
                    "status": "failed",
                    "error": f"Ping expected 200 status, got {ping_response.status_code}",
                    "response": ping_response.text
                }
                return False
                
            ping_response_data = ping_response.json()
            if "result" not in ping_response_data or "timestamp" not in ping_response_data["result"]:
                self.results["ping"] = {
                    "status": "failed",
                    "error": f"Ping response missing 'result' with 'timestamp', got {ping_response_data}"
                }
                return False
            
            self.results["ping"] = {
                "status": "success",
                "response_time": elapsed
            }
            
            logger.info(f"Ping successful, RTT: {elapsed:.3f} seconds")
            return True
            
        except Exception as e:
            logger.exception("Exception during ping test")
            self.results["ping"] = {
                "status": "error",
                "error": str(e)
            }
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
                    print(f"  Protocol Version: {result.get('protocol_version')}") # Changed from protocol_version
                    print(f"  Server Info: {result.get('server_info')}")
                    print(f"  Session ID: {result.get('session_id')}") # Changed from session_id
                elif test_name == "tools_functionality":
                    print(f"  Available Tools: {', '.join(result.get('available_tools', []))}")
                elif test_name == "ping":
                    print(f"  Response Time: {result.get('response_time', 0):.3f} seconds")
                elif test_name == "oauth_authentication":
                    tests = result.get('tests', {})
                    print(f"  OAuth Server Metadata: {'✅' if tests.get('oauth_metadata_available') else '❌'}")
                    print(f"  WWW-Authenticate Header: {'✅' if tests.get('www_authenticate_header') else '❌'}")
                    print(f"  Authorization Code Flow: {'✅' if tests.get('authorization_code_flow') else '❌'}")
                    print(f"  PKCE Support: {'✅' if tests.get('pkce_support') else '❌'}")
                    print(f"  Error Handling: {'✅' if tests.get('error_handling') else '❌'}")
                    
                    # Print details if available
                    if result.get('details'):
                        print("  Details:")
                        for detail in result.get('details', [])[:3]:  # Show first 3 details
                            print(f"    • {detail}")
                        if len(result.get('details', [])) > 3:
                            print(f"    ... and {len(result.get('details', [])) - 3} more")
        
        # Summary
        success_count = sum(1 for result in self.results.values() if result.get("status") == "success")
        total_count = len(self.results)
        skipped_count = sum(1 for result in self.results.values() if result.get("status") == "skipped")
        
        print(f"\nSummary: {success_count}/{total_count} tests passed ({skipped_count} skipped)")

    def generate_report(self, output_dir: str = "reports") -> str:
        """Generate a detailed compliance report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"http_compliance_test_{timestamp}.md")
        
        os.makedirs(output_dir, exist_ok=True)
        
        with open(report_file, "w") as f:
            f.write("# MCP HTTP Compliance Test Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Server: {self.server_url}\n")
            f.write(f"Protocol Version: {self.protocol_version}\n\n")
            
            # Write test results
            for test_name, result in self.results.items():
                f.write(f"## {test_name.replace('_', ' ').title()}\n\n")
                
                # Handle different result formats
                if isinstance(result, dict):
                    status = result.get("status", "unknown")
                    test_status = "✅" if status == "success" else "❌"
                    f.write(f"Status: {test_status} {status.title()}\n\n")
                    
                    # Write details if present
                    if "details" in result:
                        if isinstance(result["details"], list):
                            for detail in result["details"]:
                                f.write(f"- {detail}\n")
                        else:
                            f.write(f"{result['details']}\n")
                    
                    # Write error if present
                    if "error" in result:
                        f.write(f"\nError: {result['error']}\n")
                    
                    # Write test-specific details
                    if test_name == "initialization":
                        if "result" in result:
                            init_result = result["result"]
                            if "sessionId" in init_result:
                                f.write(f"\nSession ID: {init_result['sessionId']}\n")
                            if "protocolVersion" in init_result:
                                f.write(f"Protocol Version: {init_result['protocolVersion']}\n")
                            if "serverInfo" in init_result:
                                f.write(f"Server Info: {init_result['serverInfo']}\n")
                    
                    # Write sub-tests if present
                    if "tests" in result:
                        f.write("\nSub-tests:\n")
                        for sub_name, sub_result in result["tests"].items():
                            if isinstance(sub_result, dict):
                                sub_status = "✅" if sub_result.get("status") == "success" else "❌"
                                f.write(f"- {sub_name}: {sub_status} {sub_result.get('details', '')}\n")
                            else:
                                # Handle boolean sub-test results
                                sub_status = "✅" if sub_result else "❌"
                                f.write(f"- {sub_name}: {sub_status}\n")
                    
                else:
                    # Legacy format
                    test_status = "✅" if result else "❌"
                    f.write(f"Status: {test_status}\n\n")
                
                f.write("\n")
            
            # Write summary
            total_tests = len(self.results)
            passed_tests = sum(1 for r in self.results.values() if isinstance(r, dict) and r.get("status") == "success")
            f.write(f"\n## Summary\n\n")
            f.write(f"- Total Tests: {total_tests}\n")
            f.write(f"- Passed: {passed_tests}\n")
            f.write(f"- Failed: {total_tests - passed_tests}\n")
            
            if self.test_oauth:
                f.write("\n### OAuth 2.1 Support\n")
                oauth_result = self.results.get("oauth_authentication", {})
                if oauth_result.get("status") == "success":
                    f.write("✅ OAuth 2.1 authentication is fully supported\n")
                else:
                    f.write("❌ OAuth 2.1 authentication is not fully supported\n")
                    if "details" in oauth_result:
                        f.write("\nDetails:\n")
                        for detail in oauth_result["details"]:
                            f.write(f"- {detail}\n")
        
        logger.info(f"Compliance report generated: {report_file}")
        return report_file

def main():
    """Run the tests."""
    parser = argparse.ArgumentParser(description="Test MCP HTTP server for specification compliance")
    parser.add_argument("--server-url", default="http://localhost:8088", help="URL of the MCP server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    parser.add_argument("--oauth", action="store_true", help="Enable OAuth 2.1 authentication testing")
    args = parser.parse_args()
    
    # Create and run the tester
    tester = McpHttpComplianceTest(args.server_url, args.debug, args.oauth)
    
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