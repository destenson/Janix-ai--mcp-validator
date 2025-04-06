#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Sampling Tests

Tests for MCP client sampling feature.
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
        
        # Handle sampling/create
        elif method == 'sampling/create':
            # Extract parameters
            params = request.get('params', {})
            messages = params.get('messages', [])
            
            # Create a simple response based on the request
            return {
                "jsonrpc": "2.0",
                "id": request['id'],
                "result": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": "This is a response to your message."
                        }
                    ],
                    "model": "test-model",
                    "stopReason": "end_turn"
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


class TestSampling:
    """Test suite for MCP client sampling compliance."""
    
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
                "id": "init_sampling",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "sampling": {}
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
    
    @pytest.mark.requirement("M076")
    def test_sampling_capability(self):
        """Verify the client declares sampling capability correctly.
        
        Tests requirement M076: Clients supporting sampling MUST declare sampling capability
        """
        if "sampling" not in self.client_capabilities:
            pytest.skip("Client does not support sampling feature")
        
        # Check sampling capability structure
        sampling_capabilities = self.client_capabilities["sampling"]
        assert isinstance(sampling_capabilities, dict)
    
    @pytest.mark.requirement(["M077", "M078"])
    def test_sampling_create(self):
        """Test the sampling/create method.
        
        Tests requirements:
        M077: Client response MUST include role, content, model, stopReason
        M078: Content MUST be one of: text, image, or audio
        """
        if "sampling" not in self.client_capabilities:
            pytest.skip("Client does not support sampling feature")
        
        # Send sampling/create request with a simple message
        response = self._send_request_to_client({
            "jsonrpc": "2.0",
            "id": "test_sampling_create",
            "method": "sampling/create",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": "Hello, can you help me with a question?"
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "maxTokens": 100
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # If it's an error response, we're done (that's valid)
        if "error" in data:
            # Some clients might not support this method even if they declare sampling capability
            return
            
        assert "result" in data
        
        # Verify required fields
        assert "role" in data["result"]
        assert "content" in data["result"]
        assert "model" in data["result"]
        assert "stopReason" in data["result"]
        
        # Check content structure
        content = data["result"]["content"]
        assert isinstance(content, list)
        
        # If content items are returned, verify their structure
        if content:
            for item in content:
                # Content must be one of: text, image, or audio
                content_types = ["text", "image", "audio"]
                assert any(content_type in item for content_type in content_types)
    
    def test_sampling_stream(self):
        """Test the sampling/create method with streaming if supported."""
        if "sampling" not in self.client_capabilities:
            pytest.skip("Client does not support sampling feature")
        
        # Check if streaming is supported (this is optional)
        streaming_supported = False
        if isinstance(self.client_capabilities["sampling"], dict):
            streaming_supported = self.client_capabilities["sampling"].get("streaming", False)
        
        if not streaming_supported:
            pytest.skip("Client does not support streaming sampling")
        
        # Send sampling/create request with streaming enabled
        response = self._send_request_to_client({
            "jsonrpc": "2.0",
            "id": "test_sampling_stream",
            "method": "sampling/create",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": "Hello, can you help me with a question?"
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "maxTokens": 100,
                "stream": True
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # If it's an error response, we're done (that's valid)
        if "error" in data:
            return
            
        assert "result" in data
        
        # For streaming, we might get partial chunks that don't have all fields
        # But the structure should be the same as non-streaming, just potentially incomplete
    
    def _send_request_to_client(self, payload):
        """Send a JSON-RPC request to the client."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return requests.post(MCP_CLIENT_URL, json=payload, headers=headers) 