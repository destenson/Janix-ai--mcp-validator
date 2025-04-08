#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP HTTP Session Validator

A specialized script for testing session handling in MCP HTTP servers.
This script performs a series of targeted tests to validate proper session management.
"""

import argparse
import json
import requests
import sys
import time
import uuid
from urllib.parse import urlparse

class MCPSessionValidator:
    """Class to test session management in MCP HTTP servers."""
    
    def __init__(self, url, debug=False):
        """
        Initialize the session validator with the server URL.
        
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
        
        # Protocol information
        self.protocol_version = "2025-03-26"
        
        # Create a persistent session for all requests
        self.request_session = requests.Session()
        self.request_session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        })
        
        print(f"Session Validator initialized for {url}")
        print(f"Host: {self.host}, Path: {self.path}")
    
    def log(self, message):
        """Print a log message if debug is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def send_request_with_session(self, method, session_id=None, json_data=None):
        """
        Send a JSON-RPC request to the server with an optional session ID.
        
        Args:
            method: The JSON-RPC method to call
            session_id: The session ID to use (None to not include a session ID)
            json_data: Additional JSON data to include (optional)
            
        Returns:
            Tuple of (status_code, headers, body)
        """
        # Build the request
        if json_data is None:
            json_data = {}
        
        # Build a JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": str(uuid.uuid4())
        }
        
        # Add params if provided
        if json_data:
            request["params"] = json_data
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Add session ID if provided
        if session_id:
            headers["Mcp-Session-Id"] = session_id
            self.log(f"Adding session ID to request: {session_id}")
        
        try:
            # Send the request
            self.log(f"Sending request: {json.dumps(request)}")
            response = requests.post(
                self.url,
                json=request,
                headers=headers,
                timeout=5  # 5 second timeout
            )
            
            status = response.status_code
            resp_headers = dict(response.headers)
            
            self.log(f"Response Status: {status}")
            self.log(f"Response Headers: {resp_headers}")
            
            # Try to parse JSON response
            try:
                body = response.json()
                self.log(f"Response Body: {json.dumps(body)}")
            except ValueError:
                body = response.text
                self.log(f"Response Body (text): {body}")
                
            return status, resp_headers, body
            
        except requests.RequestException as e:
            self.log(f"Request failed: {str(e)}")
            raise
    
    def initialize_and_get_session(self):
        """Initialize the server and get a session ID."""
        print("\n=== Test: Initialize and get session ID ===")
        
        params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": {
                "name": "MCP Session Validator",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        }
        
        try:
            status, headers, body = self.send_request_with_session("initialize", None, params)
            
            if status != 200:
                print(f"ERROR: Initialize request failed with status {status}")
                return None
            
            # Check for session ID in headers (preferred location)
            if 'mcp-session-id' in headers:
                session_id = headers['mcp-session-id']
                print(f"✅ Success: Session ID found in headers: {session_id}")
                return session_id
            
            # Check for session ID in body (alternative location)
            if isinstance(body, dict) and 'result' in body and 'sessionId' in body['result']:
                session_id = body['result']['sessionId']
                print(f"✅ Success: Session ID found in response body: {session_id}")
                return session_id
            
            print("❌ Failure: No session ID found in response")
            return None
            
        except Exception as e:
            print(f"ERROR: Initialize request raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_no_session_id(self, session_id):
        """Test how the server behaves with no session ID."""
        print("\n=== Test: Request without Session ID ===")
        
        try:
            status, headers, body = self.send_request_with_session("server/info")
            
            # Check for error response
            if isinstance(body, dict) and 'error' in body:
                error = body['error']
                if "session" in error.get('message', '').lower():
                    print("✅ Success: Server correctly rejected request without session ID")
                    print(f"Error message: {error.get('message', '')}")
                    return True
                print(f"⚠️ Warning: Server rejected request but not clearly due to session ID: {error}")
                return True
            
            print("❌ Failure: Server did not reject request without session ID")
            return False
            
        except Exception as e:
            print(f"ERROR: Request without session ID raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_invalid_session_id(self, session_id):
        """Test how the server behaves with an invalid session ID."""
        print("\n=== Test: Request with Invalid Session ID ===")
        
        invalid_session = f"invalid-{uuid.uuid4()}"
        
        try:
            status, headers, body = self.send_request_with_session("server/info", invalid_session)
            
            # Check for error response
            if isinstance(body, dict) and 'error' in body:
                error = body['error']
                if "session" in error.get('message', '').lower() or "invalid" in error.get('message', '').lower():
                    print("✅ Success: Server correctly rejected request with invalid session ID")
                    print(f"Error message: {error.get('message', '')}")
                    return True
                print(f"⚠️ Warning: Server rejected request but not clearly due to invalid session ID: {error}")
                return True
            
            print("❌ Failure: Server did not reject request with invalid session ID")
            return False
            
        except Exception as e:
            print(f"ERROR: Request with invalid session ID raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_valid_session_id(self, session_id):
        """Test how the server behaves with a valid session ID."""
        print("\n=== Test: Request with Valid Session ID ===")
        
        try:
            status, headers, body = self.send_request_with_session("server/info", session_id)
            
            # Check for successful response
            if status == 200 and isinstance(body, dict) and 'result' in body:
                print("✅ Success: Server accepted request with valid session ID")
                return True
            
            print(f"❌ Failure: Server rejected request with valid session ID: {body}")
            return False
            
        except Exception as e:
            print(f"ERROR: Request with valid session ID raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_tools_list_with_session(self, session_id):
        """Test listing tools with a valid session ID."""
        print("\n=== Test: List Tools with Session ID ===")
        
        try:
            status, headers, body = self.send_request_with_session("tools/list", session_id)
            
            # Check for successful response
            if status == 200 and isinstance(body, dict) and 'result' in body:
                if 'tools' in body['result'] and isinstance(body['result']['tools'], list):
                    print(f"✅ Success: Server returned tools list with valid session ID")
                    print(f"Found {len(body['result']['tools'])} tools")
                    return True
                
                print(f"⚠️ Warning: Server response doesn't contain tools array: {body}")
                return False
            
            print(f"❌ Failure: Server rejected tools/list request with valid session ID: {body}")
            return False
            
        except Exception as e:
            print(f"ERROR: tools/list request raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_tool_call_with_session(self, session_id):
        """Test calling a tool with a valid session ID."""
        print("\n=== Test: Call Tool with Session ID ===")
        
        try:
            params = {
                "name": "echo",
                "parameters": {
                    "message": "Hello with session ID!"
                }
            }
            
            status, headers, body = self.send_request_with_session("tools/call", session_id, params)
            
            # Check for successful response
            if status == 200 and isinstance(body, dict) and 'result' in body:
                print(f"✅ Success: Server accepted tool call with valid session ID")
                print(f"Response: {body['result']}")
                return True
            
            print(f"❌ Failure: Server rejected tool call with valid session ID: {body}")
            return False
            
        except Exception as e:
            print(f"ERROR: Tool call request raised exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """Run all session validation tests."""
        print("Starting MCP HTTP Session Validation Tests")
        
        # Initialize and get a session ID
        session_id = self.initialize_and_get_session()
        if not session_id:
            print("\n❌ Session validation FAILED: Could not obtain a session ID")
            return False
        
        # Run tests with and without session ID
        results = []
        
        # Test 1: No session ID
        results.append(self.test_no_session_id(session_id))
        
        # Test 2: Invalid session ID
        results.append(self.test_invalid_session_id(session_id))
        
        # Test 3: Valid session ID
        results.append(self.test_valid_session_id(session_id))
        
        # Test 4: List tools with session ID
        results.append(self.test_tools_list_with_session(session_id))
        
        # Test 5: Call tool with session ID
        results.append(self.test_tool_call_with_session(session_id))
        
        # Summarize results
        print("\n=== Session Validation Test Results ===")
        passed = sum(1 for r in results if r)
        failed = len(results) - passed
        
        print(f"Tests passed: {passed}/{len(results)}")
        print(f"Tests failed: {failed}/{len(results)}")
        
        if failed == 0:
            print("\n✅ All session validation tests PASSED")
            return True
        else:
            print(f"\n❌ Session validation FAILED: {failed} tests failed")
            return False


def main():
    """Main entry point for the session validator."""
    parser = argparse.ArgumentParser(
        description="Validate session handling in an MCP HTTP server."
    )
    parser.add_argument(
        "--url", 
        default="http://localhost:8888/mcp",
        help="URL of the MCP HTTP server to test"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="MCP protocol version to test"
    )
    
    args = parser.parse_args()
    
    # Run the validator
    validator = MCPSessionValidator(args.url, args.debug)
    validator.protocol_version = args.protocol_version
    success = validator.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 