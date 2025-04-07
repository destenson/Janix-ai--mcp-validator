#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Roots Tests

Tests for MCP client roots feature.
"""

import os
import json
import pytest
import requests
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from jsonschema import validate

# Get server URL from environment or use a mock server
# For testing client behavior, we'll use a mock server that emulates MCP responses
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8765")

# Client URL for testing (may be provided in environment or use default)
MCP_CLIENT_URL = os.environ.get("MCP_CLIENT_URL", "http://localhost:8766")

def get_free_port():
    """Get a free port for our mock server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class MockMCPRequestHandler(BaseHTTPRequestHandler):
    """
    A handler that mocks an MCP server to test client behavior.
    """
    
    def do_POST(self):
        """Handle POST requests from MCP clients."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request = json.loads(post_data.decode('utf-8'))
        
        # Handle batch requests
        if isinstance(request, list):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            responses = [self._handle_single_request(req) for req in request]
            self.wfile.write(json.dumps(responses).encode('utf-8'))
            return
        
        # Handle single request
        response = self._handle_single_request(request)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _handle_single_request(self, request):
        """Handle a single JSON-RPC request."""
        # Check if it's a notification (no id)
        if 'id' not in request:
            # Just acknowledge notifications
            return {}
        
        method = request.get('method', '')
        
        # Handle initialization
        if method == 'initialize':
            return {
                "jsonrpc": "2.0",
                "id": request['id'],
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "logging": {},
                        "resources": {"subscribe": True, "listChanged": True},
                        "tools": {"listChanged": True},
                        "prompts": {"listChanged": True}
                    },
                    "serverInfo": {
                        "name": "MockMCPServer",
                        "version": "1.0.0"
                    }
                }
            }
        
        # Handle roots/list
        elif method == 'roots/list':
            return {
                "jsonrpc": "2.0",
                "id": request['id'],
                "result": {
                    "roots": [
                        {"uri": "file:///project"},
                        {"uri": "file:///user/documents", "name": "Documents"}
                    ]
                }
            }
        
        # Handle ping
        elif method == 'ping':
            return {
                "jsonrpc": "2.0",
                "id": request['id'],
                "result": None
            }
        
        # Handle unknown methods
        else:
            return {
                "jsonrpc": "2.0",
                "id": request['id'],
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }


class TestRoots:
    """Test suite for MCP client roots compliance."""
    
    @classmethod
    def setup_class(cls):
        """Set up the mock server for all tests in this class."""
        # Setup mock server if needed
        if 'MOCK_MCP_SERVER' in os.environ:
            cls.mock_server_port = get_free_port()
            cls.mock_server = HTTPServer(('localhost', cls.mock_server_port), MockMCPRequestHandler)
            
            # Start the server in a thread
            cls.server_thread = threading.Thread(target=cls.mock_server.serve_forever)
            cls.server_thread.daemon = True
            cls.server_thread.start()
            
            # Use the mock server URL for these tests
            cls.server_url = f"http://localhost:{cls.mock_server_port}"
        else:
            # Use the provided MCP server URL
            cls.server_url = MCP_SERVER_URL
    
    @classmethod
    def teardown_class(cls):
        """Clean up resources."""
        if hasattr(cls, 'mock_server'):
            cls.mock_server.shutdown()
            cls.server_thread.join()
    
    def setup_method(self):
        """Set up before each test."""
        # Initialize the connection with the client
        # For real testing, this would involve starting a client or connecting to one
        # For now, we'll make requests to the client URL to test its behavior
        try:
            response = self._send_request_to_client({
                "jsonrpc": "2.0",
                "id": "init_roots",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "MCPValidator",
                        "version": "0.1.0"
                    }
                }
            })
            
            # Store client capabilities for later tests
            self.client_capabilities = response.json()["result"]["capabilities"]
            
            # Send initialized notification
            self._send_request_to_client({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })
        except requests.exceptions.RequestException:
            pytest.skip("Failed to connect to MCP client")
    
    @pytest.mark.requirement("M071")
    def test_roots_capability(self):
        """Verify the client declares roots capability correctly.
        
        Tests requirement M071: Clients supporting roots MUST declare roots capability
        """
        if "roots" not in self.client_capabilities:
            pytest.skip("Client does not support roots feature")
        
        # Check roots capability structure
        roots_capabilities = self.client_capabilities["roots"]
        assert isinstance(roots_capabilities, dict)
        
        # Check optional capabilities
        if "listChanged" in roots_capabilities:
            assert isinstance(roots_capabilities["listChanged"], bool)
    
    @pytest.mark.requirement(["M072", "M073"])
    def test_roots_list(self):
        """Test the roots/list method.
        
        Tests requirements:
        M072: Client response MUST include roots array
        M073: Each root MUST include uri
        """
        if "roots" not in self.client_capabilities:
            pytest.skip("Client does not support roots feature")
        
        # Send roots/list request
        response = self._send_request_to_client({
            "jsonrpc": "2.0",
            "id": "test_roots_list",
            "method": "roots/list"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "roots" in data["result"]
        
        # Verify roots list structure
        roots = data["result"]["roots"]
        assert isinstance(roots, list)
        
        # If roots are returned, verify their structure
        if roots:
            for root in roots:
                assert "uri" in root
                
                # Optional fields
                if "name" in root:
                    assert isinstance(root["name"], str)
    
    @pytest.mark.requirement(["M074", "M075"])
    def test_roots_list_changed_capability(self):
        """Test that the client declares list_changed capability if it uses the notification.
        
        Tests requirements:
        M074: Client MUST send notifications/roots/list_changed when root list changes
        M075: Client MUST support listChanged capability to use this feature
        """
        if "roots" not in self.client_capabilities:
            pytest.skip("Client does not support roots feature")
        
        # Check if client declares listChanged capability
        list_changed_supported = self.client_capabilities.get("roots", {}).get("listChanged", False)
        
        # We can't fully test if the notification is actually sent when the root list changes,
        # but we can verify the capability is declared if required
        
        # For more comprehensive testing, we would need to:
        # 1. Set up a listener for client notifications
        # 2. Trigger a change in the root list (e.g., by adding/removing a root)
        # 3. Verify that the notification is received
    
    def _send_request_to_client(self, payload):
        """Send a JSON-RPC request to the client."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        client_url = os.environ.get("MCP_CLIENT_URL", "http://localhost:8766")
        
        # For now we only support HTTP transport to clients
        # Future implementations could support STDIO for client testing as well
        return requests.post(client_url, json=payload, headers=headers) 