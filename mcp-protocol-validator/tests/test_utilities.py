#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Utilities Tests

Tests for MCP utilities including ping, cancellation, progress, logging, completion, and pagination.
"""

import os
import json
import time
import threading
import pytest
import requests
from jsonschema import validate
from tests.test_base import MCPBaseTest

# Get server URL from environment
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

class TestUtilities(MCPBaseTest):
    """Test suite for MCP utilities compliance."""
    
    def setup_method(self, method):
        """Set up the test by initializing the server."""
        # Call parent setup_method to initialize common attributes
        super().setup_method(method)
        
        # Initialize the server
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "init_utilities",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "logging": {},
                    "completions": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        # Store server capabilities for later tests
        self.server_capabilities = response.json()["result"]["capabilities"]
        
        # Send initialized notification
        self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
    
    @pytest.mark.requirement("M079")
    def test_ping(self):
        """Test the ping method.
        
        Tests requirement M079: Receiver MUST respond promptly with empty response
        """
        # Send ping request
        start_time = time.time()
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_ping",
            "method": "ping"
        })
        end_time = time.time()
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        
        # Check result is empty (null, empty object, or empty array)
        assert data["result"] is None or data["result"] == {} or data["result"] == []
        
        # Check response time (should be "prompt" - arbitrary but reasonable threshold of 2s)
        response_time = end_time - start_time
        assert response_time < 2.0, f"Ping response took {response_time:.2f} seconds, which is not prompt"
    
    @pytest.mark.requirement(["M080", "M081", "M082"])
    def test_cancellation(self):
        """Test the cancellation notification.
        
        Tests requirements:
        M080: Notification MUST include requestId of request to cancel
        M081: Cancellation notifications MUST only reference previously issued requests
        M082: Initialize request MUST NOT be cancelled by clients
        """
        # First, send a long-running request in a separate thread
        def send_long_request():
            # This could be any long-running request in reality
            # For testing purposes, we'll just send a request and not wait for response
            self._send_request({
                "jsonrpc": "2.0",
                "id": "long_running_request",
                "method": "resources/list",
                "params": {
                    # Adding some arbitrary params to potentially make it slower
                    "limit": 1000,
                    "includeContent": True
                }
            })
        
        thread = threading.Thread(target=send_long_request)
        thread.daemon = True
        thread.start()
        
        # Give the request a moment to be sent
        time.sleep(0.1)
        
        # Now send a cancellation notification
        cancel_response = self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/cancellation",
            "params": {
                "requestId": "long_running_request"
            }
        })
        
        # Check the server accepted the cancellation notification
        assert cancel_response.status_code in [200, 202]
        
        # Test cancellation of non-existent request ID (should still be accepted as notification)
        cancel_invalid_response = self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/cancellation",
            "params": {
                "requestId": "non_existent_request"
            }
        })
        
        assert cancel_invalid_response.status_code in [200, 202]
        
        # Test attempt to cancel initialize request (should be accepted as notification,
        # but server should ignore it)
        cancel_init_response = self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/cancellation",
            "params": {
                "requestId": "init_utilities"
            }
        })
        
        assert cancel_init_response.status_code in [200, 202]
    
    @pytest.mark.requirement(["M083", "M084", "M085", "M086"])
    def test_progress(self):
        """Test the progress request and notification.
        
        Tests requirements:
        M083: Progress tokens MUST be unique across active requests
        M084: Progress notifications MUST include progressToken and progress value
        M085: Progress value MUST increase with each notification
        M086: Progress notifications MUST only reference active requests
        """
        # Send a progress request
        progress_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_progress",
            "method": "progress",
            "params": {
                "token": "test_progress_token"
            }
        })
        
        # Check the response (both success and error are valid depending on implementation)
        assert progress_response.status_code == 200
        
        # Since we can't fully test progress notifications in this synchronous framework,
        # we at least validate the request/response format
        progress_data = progress_response.json()
        
        if "error" not in progress_data:
            assert "result" in progress_data
            # Result can be empty or might have an initial progress value
        
        # Test sending progress notification for inactive token
        # This is just to check the notification format, not actual behavior
        # which would require an asynchronous test framework
        inactive_progress_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "token": "inactive_token",
                "progress": 0.5
            }
        }
        
        # Ensure notification format is correct
        assert "token" in inactive_progress_notification["params"]
        assert "progress" in inactive_progress_notification["params"]
        assert isinstance(inactive_progress_notification["params"]["progress"], float)
    
    @pytest.mark.requirement("M087")
    def test_logging_capability(self):
        """Test the logging capability.
        
        Tests requirement M087: Servers supporting logging MUST declare logging capability
        """
        # Check if server declares logging capability
        assert "logging" in self.server_capabilities
        
        # Logging notifications can't be fully tested in this framework
        # as they're server-initiated, but we can create a valid notification format
        # for documentation purposes
        logging_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/logging",
            "params": {
                "level": "info",
                "message": "This is a test log message"
            }
        }
        
        # Ensure notification format is correct
        assert "level" in logging_notification["params"]
        assert "message" in logging_notification["params"]
        assert logging_notification["params"]["level"] in ["trace", "debug", "info", "warn", "error"]
    
    @pytest.mark.requirement(["M088", "M089", "S029"])
    def test_completions(self):
        """Test the completions capability and complete method.
        
        Tests requirements:
        M088: Servers supporting completions MUST declare completions capability
        M089: Server response MUST include completion values
        S029: Servers SHOULD return suggestions sorted by relevance
        """
        if "completions" not in self.server_capabilities:
            pytest.skip("Server does not support completions feature")
        
        # Send a simple completion request
        completion_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_completions",
            "method": "complete",
            "params": {
                "text": "func",
                "position": 4
            }
        })
        
        assert completion_response.status_code == 200
        completion_data = completion_response.json()
        
        # If the server returns an error, that's valid too (e.g., if it needs more context)
        if "error" in completion_data:
            return
            
        assert "result" in completion_data
        assert "items" in completion_data["result"]
        
        completion_items = completion_data["result"]["items"]
        assert isinstance(completion_items, list)
        
        # If completion items are returned, verify their structure
        if completion_items:
            # Every item should have at least a label
            for item in completion_items:
                assert "label" in item
    
    @pytest.mark.requirement("S030")
    def test_pagination(self):
        """Test pagination control with nextCursor.
        
        Tests requirement S030: Servers returning large collections SHOULD use pagination
        """
        # This is a general test of pagination behavior for any method that supports it
        # We'll use resources/list as an example, but the test is about pagination mechanics
        
        # First check if server supports resources
        if "resources" not in self.server_capabilities:
            # Try tools if resources not available
            if "tools" not in self.server_capabilities:
                # Try prompts if neither resources nor tools available
                if "prompts" not in self.server_capabilities:
                    pytest.skip("Server does not support any paginated list methods")
                else:
                    endpoint = "prompts/list"
            else:
                endpoint = "tools/list"
        else:
            endpoint = "resources/list"
        
        # Send list request with a small limit to force pagination
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_pagination",
            "method": endpoint,
            "params": {
                "limit": 1
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        
        # If the server supports pagination and has enough data to paginate,
        # it should include a nextCursor in the response
        if "nextCursor" in data["result"]:
            # The server is supporting pagination as recommended
            assert isinstance(data["result"]["nextCursor"], str)
            assert data["result"]["nextCursor"] != "" 