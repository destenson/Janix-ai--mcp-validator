#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Custom MCP HTTP Server Tester for FastMCP

A simplified version of the HTTP tester specifically for testing FastMCP servers.
"""

import json
import uuid
import requests
import argparse
import sys
import time
from urllib.parse import urlparse, urljoin

class CustomMCPHttpTester:
    """Class to test a FastMCP HTTP server implementation."""
    
    def __init__(self, url, debug=False):
        """
        Initialize the tester with the server URL.
        
        Args:
            url: The URL of the MCP server
            debug: Whether to print debug information
        """
        # Ensure URL ends with a trailing slash to avoid redirects
        if not url.endswith('/'):
            url = url + '/'
        
        self.url = url
        self.debug = debug
        
        # Parse the URL
        parsed_url = urlparse(url)
        self.host = parsed_url.netloc
        self.path = parsed_url.path
        
        # Session information
        self.session_id = str(uuid.uuid4())
        self.initialized = False
        
        # Protocol information
        self.protocol_version = "2025-03-26"
        
        # Create a persistent session for all requests
        self.request_session = requests.Session()
        self.request_session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": self.session_id
        })
        
        if self.debug:
            print(f"[DEBUG] Custom MCP HTTP Tester initialized for {url}")
            print(f"[DEBUG] Host: {self.host}, Path: {self.path}")
            print(f"[DEBUG] Using session ID: {self.session_id}")
    
    def log(self, message):
        """Print a log message if debug is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def send_request(self, method, json_data=None):
        """
        Send a JSON-RPC request to the server using the requests library.
        
        Args:
            method: The JSON-RPC method to call
            json_data: Additional JSON data to include (optional)
            
        Returns:
            Response object or None if the request failed
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
        
        # Convert to JSON
        json_str = json.dumps(request)
        self.log(f"Request: {json_str}")
        
        try:
            # Send the request
            response = self.request_session.post(
                self.url,
                json=request,
                timeout=5  # 5 second timeout
            )
            
            status = response.status_code
            headers = dict(response.headers)
            
            self.log(f"Response Status: {status}")
            self.log(f"Response Headers: {headers}")
            
            # Try to parse JSON response
            try:
                body = response.json()
                self.log(f"Response Body: {json.dumps(body)}")
            except ValueError:
                body = response.text
                self.log(f"Response Body (text): {body}")
                
            return response
            
        except requests.RequestException as e:
            self.log(f"Request failed: {str(e)}")
            return None
    
    def check_server_connection(self):
        """Check if the server is accessible."""
        print(f"Checking if server at {self.url} is accessible...")
        
        try:
            response = requests.get(
                urljoin(self.url, "notifications"),
                timeout=2,
                headers={"Mcp-Session-Id": self.session_id}
            )
            
            if response.status_code < 500:  # Any response below 500 indicates server is running
                print(f"Server at {self.host} is accessible.")
                return True
            else:
                print(f"Server returned status code {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"Connection error: {str(e)}")
            return False
    
    def initialize(self):
        """Initialize the MCP session."""
        print("Testing server initialization...")
        
        # Prepare initialize parameters
        init_params = {
            "client_info": {
                "name": "Custom MCP HTTP Tester",
                "version": "1.0.0"
            },
            "protocol_version": self.protocol_version
        }
        
        # Send initialize request
        response = self.send_request("initialize", init_params)
        
        if not response:
            print("ERROR: Initialize request failed")
            return False
        
        if response.status_code != 200:
            print(f"ERROR: Initialize request failed with status {response.status_code}")
            return False
        
        try:
            response_json = response.json()
            if "result" in response_json:
                print("Initialize request successful")
                self.initialized = True
                return True
            else:
                print(f"ERROR: Invalid initialize response: {json.dumps(response_json)}")
                return False
        except ValueError:
            print(f"ERROR: Invalid JSON response: {response.text}")
            return False
    
    def test_echo_tool(self):
        """Test the echo tool."""
        if not self.initialized:
            print("ERROR: Session not initialized")
            return False
            
        print("Testing echo tool...")
        
        # Prepare test message
        test_message = f"Test message {uuid.uuid4()}"
        
        # Send request
        response = self.send_request("echo", {"message": test_message})
        
        if not response:
            print("ERROR: Echo request failed")
            return False
        
        if response.status_code != 200:
            print(f"ERROR: Echo request failed with status {response.status_code}")
            return False
        
        try:
            response_json = response.json()
            if "result" in response_json and response_json["result"] == test_message:
                print("Echo tool test successful")
                return True
            else:
                print(f"ERROR: Echo tool returned wrong result: {json.dumps(response_json)}")
                return False
        except ValueError:
            print(f"ERROR: Invalid JSON response: {response.text}")
            return False
    
    def test_add_tool(self):
        """Test the add tool."""
        if not self.initialized:
            print("ERROR: Session not initialized")
            return False
            
        print("Testing add tool...")
        
        # Prepare test numbers
        a = 5
        b = 7
        expected_result = a + b
        
        # Send request
        response = self.send_request("add", {"a": a, "b": b})
        
        if not response:
            print("ERROR: Add request failed")
            return False
        
        if response.status_code != 200:
            print(f"ERROR: Add request failed with status {response.status_code}")
            return False
        
        try:
            response_json = response.json()
            if "result" in response_json and response_json["result"] == expected_result:
                print("Add tool test successful")
                return True
            else:
                print(f"ERROR: Add tool returned wrong result: {json.dumps(response_json)}")
                return False
        except ValueError:
            print(f"ERROR: Invalid JSON response: {response.text}")
            return False
    
    def run_tests(self):
        """Run all tests."""
        # First check server connection
        if not self.check_server_connection():
            return False
        
        # Run tests
        tests = [
            self.initialize,
            self.test_echo_tool,
            self.test_add_tool
        ]
        
        success = True
        for test in tests:
            if not test():
                success = False
                break
        
        if success:
            print("All tests passed!")
        else:
            print("Some tests failed")
        
        return success

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run simplified MCP HTTP tests against a FastMCP server."
    )
    parser.add_argument(
        "--server-url", 
        default="http://localhost:8085/mcp/",
        help="URL of the MCP HTTP server to test (should end with a /)"
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
    
    # Create tester and run tests
    tester = CustomMCPHttpTester(args.server_url, args.debug)
    tester.protocol_version = args.protocol_version
    
    success = tester.run_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 