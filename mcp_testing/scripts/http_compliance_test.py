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
            
            # Make the request to the mcp endpoint
            response = self.client.post(
                f"{self.server_url}/mcp",
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
                
                initialized_url = f"{self.server_url}/mcp?session_id={self.session_id}"
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
    
    def fetch_oauth_server_metadata(self):
        """Fetch OAuth server metadata from .well-known/oauth-authorization-server."""
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
        
        test_results = {
            "basic_flow": False,
            "www_authenticate_header": False,
            "oauth_metadata_available": False,
            "authorization_code_flow": False,
            "pkce_support": False,
            "error_handling": False,
            "details": []
        }
        
        try:
            # Send request without authentication to trigger 401
            test_payload = {
                "jsonrpc": "2.0",
                "method": "ping",
                "id": str(uuid.uuid4())
            }
            
            response = self.client.post(
                f"{self.server_url}/mcp",
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                test_results["basic_flow"] = True
                test_results["details"].append("Server properly returns 401 for unauthenticated requests")
                logger.debug("✅ Server properly returns 401 for unauthenticated requests")
                
                # Handle the 401 response
                oauth_info = self.handle_401_response(response)
                
                # Check WWW-Authenticate header
                if oauth_info["www_authenticate"]:
                    test_results["www_authenticate_header"] = True
                    test_results["details"].append("Server provides WWW-Authenticate header")
                    logger.debug("✅ Server provides WWW-Authenticate header")
                    
                    # Check for Bearer scheme
                    if oauth_info.get("scheme") == "Bearer":
                        test_results["details"].append("Server uses Bearer authentication scheme")
                        logger.debug("✅ Server uses Bearer authentication scheme")
                    else:
                        test_results["details"].append("Server doesn't use Bearer authentication scheme")
                        logger.debug("⚠️  Server doesn't use Bearer authentication scheme")
                else:
                    test_results["details"].append("Server doesn't provide WWW-Authenticate header (acceptable per spec)")
                    logger.debug("ℹ️  Server doesn't provide WWW-Authenticate header (acceptable per spec)")
                
                # Check for OAuth server metadata
                if oauth_info["oauth_metadata"]:
                    test_results["oauth_metadata_available"] = True
                    test_results["details"].append("OAuth server metadata available")
                    logger.debug("✅ OAuth server metadata available")
                    
                    metadata = oauth_info["oauth_metadata"]
                    required_fields = ["authorization_endpoint", "token_endpoint", "issuer"]
                    
                    all_fields_present = True
                    for field in required_fields:
                        if field in metadata:
                            test_results["details"].append(f"OAuth metadata contains {field}")
                            logger.debug(f"✅ OAuth metadata contains {field}")
                        else:
                            test_results["details"].append(f"OAuth metadata missing {field}")
                            logger.debug(f"❌ OAuth metadata missing {field}")
                            all_fields_present = False
                    
                    if all_fields_present:
                        test_results["authorization_code_flow"] = True
                        test_results["details"].append("Authorization code flow supported")
                        logger.debug("✅ Authorization code flow supported")
                    
                    # Check PKCE support
                    pkce_methods = metadata.get("code_challenge_methods_supported", [])
                    if "S256" in pkce_methods:
                        test_results["pkce_support"] = True
                        test_results["details"].append("PKCE S256 method supported")
                        logger.debug("✅ PKCE S256 method supported")
                    else:
                        test_results["details"].append("PKCE S256 method not explicitly supported")
                        logger.debug("⚠️  PKCE S256 method not explicitly supported")
                    
                    # Test error handling by making invalid token request
                    if "token_endpoint" in metadata:
                        try:
                            invalid_token_response = self.client.post(
                                metadata["token_endpoint"],
                                data={
                                    "grant_type": "authorization_code",
                                    "code": "invalid_code",
                                    "client_id": "test_client"
                                }
                            )
                            
                            if invalid_token_response.status_code in [400, 401]:
                                test_results["error_handling"] = True
                                test_results["details"].append("OAuth error handling works properly")
                                logger.debug("✅ OAuth error handling works properly")
                            else:
                                test_results["details"].append(f"Unexpected error response: {invalid_token_response.status_code}")
                                logger.debug(f"⚠️  Unexpected error response: {invalid_token_response.status_code}")
                        except Exception as e:
                            test_results["details"].append(f"Error testing OAuth error handling: {str(e)}")
                            logger.debug(f"ℹ️  Error testing OAuth error handling: {str(e)}")
                
                else:
                    test_results["details"].append("OAuth server metadata not available")
                    logger.debug("⚠️  OAuth server metadata not available")
                
            elif response.status_code == 200:
                test_results["basic_flow"] = True
                test_results["details"].append("Server doesn't require authentication")
                logger.debug("ℹ️  Server doesn't require authentication")
                
            else:
                test_results["details"].append(f"Unexpected status code: {response.status_code}")
                logger.debug(f"❌ Unexpected status code: {response.status_code}")
            
            # Calculate overall success
            oauth_success = (
                test_results["basic_flow"] and
                (test_results["oauth_metadata_available"] or response.status_code == 200)
            )
            
            self.results["oauth_authentication"] = {
                "status": "success" if oauth_success else "failed",
                "details": test_results["details"],
                "tests": test_results
            }
            
            return oauth_success
            
        except Exception as e:
            logger.exception("Exception during OAuth authentication test")
            self.results["oauth_authentication"] = {
                "status": "error",
                "error": str(e)
            }
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
                    headers=headers
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
        """Test error handling according to JSON-RPC 2.0 and HTTP standards."""
        logger.info("Testing error handling")
        
        if not self.session_id:
            self.results["error_handling"] = {
                "status": "skipped",
                "reason": "No session ID available"
            }
            return False
        
        try:
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            tests = [
                {
                    "name": "parse_error",
                    "payload": "{ this is not valid JSON",
                    "expected_code": 400,  # Bad Request for malformed JSON
                    "expected_json_rpc_error": PARSE_ERROR,  # -32700
                    "headers": {"Content-Type": "application/json"}
                },
                {
                    "name": "invalid_request", 
                    "payload": {"jsonrpc": "2.0", "id": 1},  # Missing method
                    "expected_code": 400,  # Bad Request for invalid request structure
                    "expected_json_rpc_error": INVALID_REQUEST,  # -32600
                    "headers": {"Content-Type": "application/json"}
                },
                {
                    "name": "method_not_found",
                    "payload": {"jsonrpc": "2.0", "id": 1, "method": "unknown_method"},
                    "expected_code": 404,  # Not Found for unknown method
                    "expected_json_rpc_error": METHOD_NOT_FOUND,  # -32601
                    "headers": {"Content-Type": "application/json"}
                },
                {
                    "name": "invalid_params",
                    "payload": {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": "invalid"},
                    "expected_code": 400,  # Bad Request for invalid parameters
                    "expected_json_rpc_error": INVALID_PARAMS,  # -32602
                    "headers": {"Content-Type": "application/json"}
                },
                {
                    "name": "session_expired",
                    "payload": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    "expected_code": 401,  # Unauthorized for invalid/expired session
                    "expected_json_rpc_error": SESSION_EXPIRED,  # -32003
                    "headers": {"Content-Type": "application/json", "Mcp-Session-Id": "invalid-session-id"}
                }
            ]
            
            all_passed = True
            test_results = []
            
            for test in tests:
                logger.info(f"Running error test: {test['name']}")
                
                # Special URL for session_expired test
                test_url = f"{self.server_url}/mcp" if test["name"] == "session_expired" else url
                test_headers = test.get("headers", headers)
                
                try:
                    if isinstance(test["payload"], str):
                        # Raw string payload (invalid JSON)
                        response = self.client.post(
                            test_url,
                            content=test["payload"],
                            headers=test_headers
                        )
                    else:
                        # JSON payload
                        response = self.client.post(
                            test_url,
                            json=test["payload"],
                            headers=test_headers
                        )
                    
                    # Check HTTP status code
                    status_passed = response.status_code == test["expected_code"]
                    
                    # Try to parse JSON response and check error code
                    json_rpc_passed = True
                    try:
                        response_json = response.json()
                        if "error" in response_json:
                            actual_error_code = response_json["error"].get("code")
                            json_rpc_passed = actual_error_code == test["expected_json_rpc_error"]
                    except:
                        # If we can't parse JSON, just check HTTP status
                        pass
                    
                    test_passed = status_passed and json_rpc_passed
                    test_results.append({
                        "name": test["name"],
                        "passed": test_passed,
                        "expected_code": test["expected_code"],
                        "actual_code": response.status_code,
                        "expected_json_rpc": test["expected_json_rpc_error"],
                        "response": response_json if 'response_json' in locals() else None
                    })
                    
                    if not test_passed:
                        all_passed = False
                        logger.warning(f"Error test {test['name']} failed: expected HTTP {test['expected_code']}, got {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error test {test['name']} raised exception: {e}")
                    all_passed = False
                    test_results.append({
                        "name": test["name"],
                        "passed": False,
                        "error": str(e)
                    })
            
            self.results["error_handling"] = {
                "status": "success" if all_passed else "failed",
                "tests": test_results,
                "total_tests": len(tests),
                "passed_tests": sum(1 for t in test_results if t.get("passed", False))
            }
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Exception during error handling test: {e}")
            self.results["error_handling"] = {
                "status": "error", 
                "error": str(e)
            }
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
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
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
            
            # In 2025-06-18, batch requests should be rejected
            if self.protocol_version == "2025-06-18":
                if batch_response.status_code == 400:
                    # Check that the error message mentions batching not supported
                    try:
                        error_data = batch_response.json()
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
                    "error": f"2025-06-18 should reject batch requests with 400 status, got {batch_response.status_code}",
                    "response": batch_response.text
                }
                return False
            
            # For older protocol versions, batch requests should work
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
                f"{self.server_url}/mcp",
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
            invalid_session_url = f"{self.server_url}/mcp?session_id=invalid-session-id-{uuid.uuid4()}"
            invalid_session_response = self.client.post(
                invalid_session_url,
                json=no_session_payload,
                headers=headers
            )
            
            # Should return 401 Unauthorized for invalid session (following JSON-RPC over HTTP standards)
            if invalid_session_response.status_code != 401:
                logger.warning(f"Invalid session expected 401 status, got {invalid_session_response.status_code}")
            
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
            url = f"{self.server_url}/mcp?session_id={self.session_id}"
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
        """Generate a detailed compliance test report."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.fromtimestamp(self.test_start_time).strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"http_compliance_test_{timestamp}.md")
        
        with open(report_file, "w") as f:
            f.write("# MCP HTTP Compliance Test Report\n\n")
            f.write(f"**Server**: {self.server_url}\n")
            f.write(f"**Timestamp**: {datetime.fromtimestamp(self.test_start_time).isoformat()}\n")
            f.write(f"**Protocol Version**: {self.protocol_version}\n\n")
            
            for test_name, result in self.results.items():
                f.write(f"## {test_name.replace('_', ' ').title()}\n\n")
                
                status = result.get("status", "unknown")
                if isinstance(status, bool):
                    status = "success" if status else "failed"
                
                status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
                f.write(f"**Status**: {status_icon} {status.title()}\n\n")
                
                if "error" in result:
                    f.write(f"**Error**: {result['error']}\n\n")
                elif "reason" in result:
                    f.write(f"**Reason**: {result['reason']}\n\n")
                else:
                    # Add specific details for each test type
                    if test_name == "initialization":
                        if "session_id" in result:
                            f.write(f"**Session ID**: {result['session_id']}\n")
                        if "protocol_version" in result:
                            f.write(f"**Protocol Version**: {result['protocol_version']}\n")
                        if "server_info" in result:
                            f.write(f"**Server Info**: {result['server_info']}\n")
                    elif test_name == "tools_functionality":
                        if "tools" in result:
                            f.write(f"**Available Tools**: {', '.join(result['tools'])}\n")
                    elif test_name == "error_handling":
                        if "tests" in result:
                            f.write(f"**Tests Passed**: {result.get('passed_tests', 0)}/{result.get('total_tests', 0)}\n\n")
                            for test in result["tests"]:
                                test_status = "✅" if test.get("passed", False) else "❌"
                                f.write(f"- {test_status} **{test['name']}**: ")
                                if test.get("passed", False):
                                    f.write(f"HTTP {test.get('actual_code', 'N/A')}\n")
                                else:
                                    f.write(f"Expected HTTP {test.get('expected_code', 'N/A')}, got {test.get('actual_code', 'N/A')}\n")
                    elif test_name == "ping":
                        if "response_time" in result:
                            f.write(f"**Response Time**: {result['response_time']:.3f} seconds\n")
                
                f.write("\n")
            
            # Summary
            total_tests = len([r for r in self.results.values() if r.get("status") not in ["skipped", "unknown"]])
            passed_tests = len([r for r in self.results.values() if r.get("status") == "success"])
            skipped_tests = len([r for r in self.results.values() if r.get("status") == "skipped"])
            
            f.write(f"## Summary\n\n")
            f.write(f"**Total Tests**: {total_tests}\n")
            f.write(f"**Passed**: {passed_tests}\n")
            f.write(f"**Failed**: {total_tests - passed_tests}\n")
            f.write(f"**Skipped**: {skipped_tests}\n")
            f.write(f"**Success Rate**: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%\n")
        
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