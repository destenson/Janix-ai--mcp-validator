#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Prompts Tests

Tests for MCP prompts feature including listing and retrieval of prompts.
"""

import os
import json
import pytest
import requests
from jsonschema import validate
from tests.test_base import MCPBaseTest

# Get server URL from environment
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

class TestPrompts(MCPBaseTest):
    """Test suite for MCP prompts compliance."""
    
    def setup_method(self, method):
        """Set up the test by initializing the server."""
        # Call parent setup_method to initialize common attributes
        super().setup_method(method)
        
        # Initialize the server
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "init_prompts",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "prompts": {}
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
    
    @pytest.mark.requirement("M058")
    def test_prompts_capability(self):
        """Verify the server declares prompts capability correctly.
        
        Tests requirement M058: Servers supporting prompts MUST declare prompts capability
        """
        if "prompts" not in self.server_capabilities:
            pytest.skip("Server does not support prompts feature")
        
        # Check prompts capability structure
        prompts_capabilities = self.server_capabilities["prompts"]
        assert isinstance(prompts_capabilities, dict)
        
        # Check optional capabilities
        if "listChanged" in prompts_capabilities:
            assert isinstance(prompts_capabilities["listChanged"], bool)
    
    @pytest.mark.requirement(["M059", "M060"])
    def test_prompts_list(self):
        """Test the prompts/list method.
        
        Tests requirements:
        M059: Server response MUST include prompts array
        M060: Each prompt MUST include name
        """
        if "prompts" not in self.server_capabilities:
            pytest.skip("Server does not support prompts feature")
        
        # Send prompts/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompts_list",
            "method": "prompts/list"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "prompts" in data["result"]
        
        # Verify prompts list structure
        prompts = data["result"]["prompts"]
        assert isinstance(prompts, list)
        
        # If prompts are returned, verify their structure
        if prompts:
            for prompt in prompts:
                assert "name" in prompt
                
                # Optional fields
                if "description" in prompt:
                    assert isinstance(prompt["description"], str)
                if "arguments" in prompt:
                    assert isinstance(prompt["arguments"], dict)
    
    def test_prompts_list_pagination(self):
        """Test pagination for prompts/list method."""
        if "prompts" not in self.server_capabilities:
            pytest.skip("Server does not support prompts feature")
        
        # Send initial prompts/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompts_list_pagination",
            "method": "prompts/list",
            "params": {
                "limit": 1  # Request only one prompt to test pagination
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
                "id": "test_prompts_list_pagination_next",
                "method": "prompts/list",
                "params": {
                    "cursor": next_cursor
                }
            })
            
            assert next_response.status_code == 200
            next_data = next_response.json()
            assert "result" in next_data
            assert "prompts" in next_data["result"]
    
    @pytest.mark.requirement(["M061", "M062", "M063"])
    def test_get_prompt(self):
        """Test the prompts/get method.
        
        Tests requirements:
        M061: Server response MUST include messages array
        M062: Each message MUST include role and content
        M063: Content MUST be one of: text, image, audio, or resource
        """
        if "prompts" not in self.server_capabilities:
            pytest.skip("Server does not support prompts feature")
        
        # First, get a prompt name from the prompts/list endpoint
        list_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "list_for_get",
            "method": "prompts/list"
        })
        
        list_data = list_response.json()
        if not list_data["result"]["prompts"]:
            pytest.skip("No prompts available to test get")
        
        # Get the name of the first prompt
        prompt_name = list_data["result"]["prompts"][0]["name"]
        
        # Prepare arguments if required
        arguments = {}
        if "arguments" in list_data["result"]["prompts"][0]:
            # Try to build minimal arguments based on requirements
            schema = list_data["result"]["prompts"][0]["arguments"]
            try:
                if isinstance(schema, dict) and "properties" in schema:
                    for prop, details in schema["properties"].items():
                        # For required string properties, use empty string or defaults
                        if details.get("type") == "string":
                            arguments[prop] = details.get("default", "test_value")
                        # For required boolean properties, use false or defaults
                        elif details.get("type") == "boolean":
                            arguments[prop] = details.get("default", False)
                        # For required number properties, use 0 or defaults
                        elif details.get("type") in ["number", "integer"]:
                            arguments[prop] = details.get("default", 0)
            except Exception:
                # If there's any issue with the schema, just use an empty object
                arguments = {}
        
        # Test prompts/get with the name
        params = {"name": prompt_name}
        if arguments:
            params["arguments"] = arguments
            
        get_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_get_prompt",
            "method": "prompts/get",
            "params": params
        })
        
        assert get_response.status_code == 200
        get_data = get_response.json()
        
        # If it's an error response, we're done (that's valid)
        if "error" in get_data:
            return
            
        assert "result" in get_data
        assert "messages" in get_data["result"]
        
        # Verify messages structure
        messages = get_data["result"]["messages"]
        assert isinstance(messages, list)
        
        # Check each message
        for message in messages:
            assert "role" in message
            assert "content" in message
            
            # Check that content is one of the allowed types
            content = message["content"]
            assert isinstance(content, list)
            
            # Check each content item
            for item in content:
                # Content must be one of: text, image, audio, or resource
                content_types = ["text", "image", "audio", "resource"]
                assert any(content_type in item for content_type in content_types)
    
    @pytest.mark.requirement(["M064", "S024"])
    def test_prompts_list_changed_capability(self):
        """Test that the server declares list_changed capability if it uses the notification.
        
        Tests requirements:
        M064: Server MUST support listChanged capability to use this feature
        S024: Server SHOULD send notifications/prompts/list_changed when prompt list changes
        """
        if "prompts" not in self.server_capabilities:
            pytest.skip("Server does not support prompts feature")
        
        # Check if server declares listChanged capability
        list_changed_supported = self.server_capabilities.get("prompts", {}).get("listChanged", False)
        
        # We can't test if the notification is actually sent,
        # but we can verify the capability is declared if required
        
        # Note: We can't fully test this as we'd need to trigger a list change
        # and capture the notification, which requires async communication

    # Remove the _send_request method since it's now provided by the parent class 