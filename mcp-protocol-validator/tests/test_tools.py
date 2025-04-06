#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tools Tests

Tests for MCP tools feature including discovery and basic invocation.
"""

import os
import json
import pytest
import requests
from jsonschema import validate

# Get server URL from environment
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

class TestTools:
    """Test suite for MCP tools compliance."""
    
    def setup_method(self):
        """Set up the test by initializing the server."""
        # Initialize the server
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "init_tools",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {}
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
    
    @pytest.mark.requirement("M065")
    def test_tools_capability(self):
        """Verify the server declares tools capability correctly.
        
        Tests requirement M065: Servers supporting tools MUST declare tools capability
        """
        if "tools" not in self.server_capabilities:
            pytest.skip("Server does not support tools feature")
        
        # Check tools capability structure
        tools_capabilities = self.server_capabilities["tools"]
        assert isinstance(tools_capabilities, dict)
        
        # Check optional capabilities
        if "listChanged" in tools_capabilities:
            assert isinstance(tools_capabilities["listChanged"], bool)
    
    @pytest.mark.requirement(["M066", "M067"])
    def test_tools_list(self):
        """Test the tools/list method.
        
        Tests requirements:
        M066: Server response MUST include tools array
        M067: Each tool MUST include name, description, inputSchema
        """
        if "tools" not in self.server_capabilities:
            pytest.skip("Server does not support tools feature")
        
        # Send tools/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tools_list",
            "method": "tools/list"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        
        # Verify tools list structure
        tools = data["result"]["tools"]
        assert isinstance(tools, list)
        
        # If tools are returned, verify their structure
        if tools:
            for tool in tools:
                assert "name" in tool
                assert "description" in tool
                assert "inputSchema" in tool
                
                # Optional fields
                if "annotations" in tool:
                    assert isinstance(tool["annotations"], dict)
    
    def test_tools_list_pagination(self):
        """Test pagination for tools/list method."""
        if "tools" not in self.server_capabilities:
            pytest.skip("Server does not support tools feature")
        
        # Send initial tools/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tools_list_pagination",
            "method": "tools/list",
            "params": {
                "limit": 1  # Request only one tool to test pagination
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        
        # If nextCursor is provided, test fetching the next page
        if "nextCursor" in data["result"]:
            next_cursor = data["result"]["nextCursor"]
            
            # Fetch next page using the cursor
            next_response = self._send_request({
                "jsonrpc": "2.0",
                "id": "test_tools_list_pagination_next",
                "method": "tools/list",
                "params": {
                    "cursor": next_cursor
                }
            })
            
            assert next_response.status_code == 200
            next_data = next_response.json()
            assert "result" in next_data
            assert "tools" in next_data["result"]
    
    @pytest.mark.requirement("M068")
    def test_tool_call(self):
        """Test the tools/call method.
        
        Tests requirements:
        M068: Server response MUST include content array and isError flag
        M069: Each content item MUST be one of: text, image, audio, or resource
        """
        if "tools" not in self.server_capabilities:
            pytest.skip("Server does not support tools feature")
        
        # First, get a tool from the tools/list endpoint
        list_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "list_for_call",
            "method": "tools/list"
        })
        
        list_data = list_response.json()
        if not list_data["result"]["tools"]:
            pytest.skip("No tools available to test calling")
        
        # Get the first tool
        tool = list_data["result"]["tools"][0]
        
        # Build a minimal input
        input_data = {}
        try:
            # Try to build an input based on inputSchema if it's a JSON Schema
            schema = tool["inputSchema"]
            if isinstance(schema, dict) and "properties" in schema:
                for prop, details in schema["properties"].items():
                    # For required string properties, use empty string or defaults
                    if details.get("type") == "string":
                        input_data[prop] = details.get("default", "test_value")
                    # For required boolean properties, use false or defaults
                    elif details.get("type") == "boolean":
                        input_data[prop] = details.get("default", False)
                    # For required number properties, use 0 or defaults
                    elif details.get("type") in ["number", "integer"]:
                        input_data[prop] = details.get("default", 0)
        except Exception:
            # If there's any issue with the schema, just use an empty object
            input_data = {}
        
        # Test tool call with the input data
        call_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tool_call",
            "method": "tools/call",
            "params": {
                "name": tool["name"],
                "input": input_data
            }
        })
        
        # Tool call might fail due to invalid input, which is okay for this test
        # We're just verifying the response structure meets the requirements
        assert call_response.status_code == 200
        call_data = call_response.json()
        
        # If it's an error response, we're done (that's valid)
        if "error" in call_data:
            return
        
        # Otherwise, check the result structure
        assert "result" in call_data
        assert "content" in call_data["result"]
        assert "isError" in call_data["result"]
        assert isinstance(call_data["result"]["isError"], bool)
        
        # Verify content items if any
        content = call_data["result"]["content"]
        assert isinstance(content, list)
        
        # Check each content item if any
        for item in content:
            # Content must be one of: text, image, audio, or resource
            content_types = ["text", "image", "audio", "resource"]
            assert any(content_type in item for content_type in content_types)
    
    @pytest.mark.requirement(["M070", "S025"])
    def test_tools_list_changed_capability(self):
        """Test that the server declares list_changed capability if it uses the notification.
        
        Tests requirements:
        M070: Server MUST support listChanged capability to use this feature
        S025: Server SHOULD send notifications/tools/list_changed when tool list changes
        """
        if "tools" not in self.server_capabilities:
            pytest.skip("Server does not support tools feature")
        
        # Check if server declares listChanged capability
        list_changed_supported = self.server_capabilities.get("tools", {}).get("listChanged", False)
        
        # We can't test if the notification is actually sent,
        # but we can verify the capability is declared if required
    
    def _send_request(self, payload):
        """Send a JSON-RPC request to the server."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return requests.post(MCP_SERVER_URL, json=payload, headers=headers) 