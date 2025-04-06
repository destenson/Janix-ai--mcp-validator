#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later


"""
Base Protocol Tests

Tests for MCP protocol initialization, capabilities negotiation, and JSON-RPC compliance.
"""

import os
import json
import pytest
import requests
from jsonschema import validate
from tests.test_base import MCPBaseTest

# Get server URL from environment (for backward compatibility)
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

# Check if running in STDIO-only mode
STDIO_ONLY = os.environ.get("MCP_STDIO_ONLY", "0").lower() in ("1", "true", "yes")

class TestBaseProtocol(MCPBaseTest):
    """Test suite for MCP base protocol compliance."""
    
    @pytest.mark.requirement("M001")
    @pytest.mark.http_only
    def test_jsonrpc_version(self):
        """Verify the server requires and responds with JSON-RPC 2.0.
        
        Tests requirement M001: All messages MUST follow JSON-RPC 2.0 specification.
        """
        # Test with correct version
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_jsonrpc_version_1",
            "method": "ping"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        
        # Test with incorrect version (should be rejected)
        response = self._send_request({
            "jsonrpc": "1.0",
            "id": "test_jsonrpc_version_2",
            "method": "ping"
        })
        assert response.status_code in [400, 200]
        # If 200, the response should contain an error
        if response.status_code == 200:
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid request
    
    @pytest.mark.requirement(["M002", "M003"])
    @pytest.mark.http_only
    def test_request_with_invalid_id(self):
        """Verify the server handles requests with invalid ID format.
        
        Tests requirements:
        M002: Requests MUST include a string or integer ID (not null)
        M003: Request IDs MUST NOT be null
        """
        # Test with object ID (not allowed)
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": {"invalid": "id"},
            "method": "ping"
        })
        assert response.status_code in [400, 200]
        # If 200, the response should contain an error
        if response.status_code == 200:
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid request
        
        # Test with null ID (not allowed)
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": None,
            "method": "ping"
        })
        assert response.status_code in [400, 200]
        # If 200, the response should contain an error
        if response.status_code == 200:
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32600  # Invalid request
    
    @pytest.mark.requirement(["M005", "M039", "M040", "M041", "M042", "M043", "M044", "M045", "M046", "M047"])
    def test_initialization(self):
        """Test the initialization process and version negotiation.
        
        Tests requirements:
        M005: Requests MUST include a method string
        M039: Client MUST send initialize request as first interaction
        M040: Initialize request MUST include protocol version, client capabilities, and client info
        M041: Initialize request MUST NOT be part of a JSON-RPC batch
        M042: Server MUST respond with protocol version, server capabilities, and server info
        M043: After successful initialization, client MUST send initialized notification
        M044: Client MUST send a protocol version it supports
        M045: If server supports requested version, it MUST respond with same version
        M046: Otherwise, server MUST respond with another supported version
        M047: Client and server MUST declare capabilities during initialization
        """
        # Send initialize request
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_initialization_1",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        assert init_response.status_code == 200
        init_data = init_response.json()
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        assert "capabilities" in init_data["result"]
        assert "serverInfo" in init_data["result"]
        
        # Verify the server responds with a supported version
        protocol_version = init_data["result"]["protocolVersion"]
        assert protocol_version in ["2025-03-26", "2024-11-05"]
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        assert init_notification.status_code in [200, 202]
        
        # Test request after initialization
        ping_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_initialization_2",
            "method": "ping"
        })
        assert ping_response.status_code == 200
        ping_data = ping_response.json()
        assert "result" in ping_data
    
    @pytest.mark.requirement("M047")
    def test_capabilities_negotiation(self):
        """Test that the server correctly reports its capabilities.
        
        Tests requirement M047: Client and server MUST declare capabilities during initialization
        """
        # Send initialize request
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_capabilities",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        assert init_response.status_code == 200
        init_data = init_response.json()
        assert "result" in init_data
        
        # Check for required capabilities structure
        capabilities = init_data["result"]["capabilities"]
        assert isinstance(capabilities, dict)
        
        # Check for optional capabilities
        if "resources" in capabilities:
            assert isinstance(capabilities["resources"], dict)
            if "subscribe" in capabilities["resources"]:
                assert isinstance(capabilities["resources"]["subscribe"], bool)
            if "listChanged" in capabilities["resources"]:
                assert isinstance(capabilities["resources"]["listChanged"], bool)
        
        if "tools" in capabilities:
            assert isinstance(capabilities["tools"], dict)
            if "listChanged" in capabilities["tools"]:
                assert isinstance(capabilities["tools"]["listChanged"], bool)
        
        if "prompts" in capabilities:
            assert isinstance(capabilities["prompts"], dict)
            if "listChanged" in capabilities["prompts"]:
                assert isinstance(capabilities["prompts"]["listChanged"], bool)
    
    @pytest.mark.requirement("M005")
    @pytest.mark.http_only
    def test_method_not_found(self):
        """Test that the server responds with method not found for invalid methods.
        
        Tests requirement M005: Requests MUST include a method string
        """
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_method_not_found",
            "method": "invalid_method_that_does_not_exist"
        })
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
    
    @pytest.mark.requirement(["M009", "M010"])
    @pytest.mark.http_only
    def test_notification_handling(self):
        """Test that the server correctly handles notifications (no response expected).
        
        Tests requirements:
        M009: Notifications MUST NOT include an ID
        M010: Notifications MUST include a method string
        """
        response = self._send_request({
            "jsonrpc": "2.0",
            "method": "notifications/example"
        })
        
        # Notifications should not return a response entity, but the HTTP code may vary
        # Some servers return 202 (Accepted), others return 200 (OK) with empty body
        assert response.status_code in [200, 202, 204]
        
    @pytest.mark.requirement("M011")
    @pytest.mark.http_only
    def test_batch_handling(self):
        """Test that the server correctly handles batch requests.
        
        Tests requirement M011: Implementations MUST support receiving JSON-RPC batches
        """
        batch_request = [
            {
                "jsonrpc": "2.0",
                "id": "batch_1",
                "method": "ping"
            },
            {
                "jsonrpc": "2.0",
                "id": "batch_2",
                "method": "ping"
            }
        ]
        response = self._send_request(batch_request)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "batch_1"
        assert data[1]["id"] == "batch_2" 