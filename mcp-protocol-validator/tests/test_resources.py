#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Resources Tests

Tests for MCP resources feature including listing and reading resources.
"""

import os
import json
import pytest
import requests
from jsonschema import validate
from tests.test_base import MCPBaseTest

# Get server URL from environment (for backward compatibility)
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

class TestResources(MCPBaseTest):
    """Test suite for MCP resources compliance."""
    
    def __init__(self):
        """Initialize the test class."""
        super().__init__()
    
    def setup_method(self):
        """Set up the test by initializing the server."""
        # Initialize the server
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "init_resources",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "resources": {}
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
    
    @pytest.mark.requirement("M048")
    def test_resources_capability(self):
        """Verify the server declares resources capability correctly.
        
        Tests requirement M048: Servers supporting resources MUST declare resources capability
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # Check resources capability structure
        resources_capabilities = self.server_capabilities["resources"]
        assert isinstance(resources_capabilities, dict)
        
        # Check optional capabilities
        if "subscribe" in resources_capabilities:
            assert isinstance(resources_capabilities["subscribe"], bool)
        if "listChanged" in resources_capabilities:
            assert isinstance(resources_capabilities["listChanged"], bool)
    
    @pytest.mark.requirement(["M049", "M050"])
    def test_resources_list(self):
        """Test the resources/list method.
        
        Tests requirements:
        M049: Server response MUST include resources array
        M050: Each resource MUST include uri and name
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # Send resources/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_resources_list",
            "method": "resources/list"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "resources" in data["result"]
        
        # Verify resources list structure
        resources = data["result"]["resources"]
        assert isinstance(resources, list)
        
        # If resources are returned, verify their structure
        if resources:
            for resource in resources:
                assert "uri" in resource
                assert "name" in resource
                
                # Optional fields
                if "description" in resource:
                    assert isinstance(resource["description"], str)
                if "mimeType" in resource:
                    assert isinstance(resource["mimeType"], str)
                if "size" in resource:
                    assert isinstance(resource["size"], int)
                    assert resource["size"] >= 0
    
    def test_resources_list_pagination(self):
        """Test pagination for resources/list method."""
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # Send initial resources/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_resources_list_pagination",
            "method": "resources/list",
            "params": {
                "limit": 1  # Request only one resource to test pagination
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
                "id": "test_resources_list_pagination_next",
                "method": "resources/list",
                "params": {
                    "cursor": next_cursor
                }
            })
            
            assert next_response.status_code == 200
            next_data = next_response.json()
            assert "result" in next_data
            assert "resources" in next_data["result"]
    
    @pytest.mark.requirement(["M051", "M052", "S022"])
    def test_resources_read(self):
        """Test the resources/read method.
        
        Tests requirements:
        M051: Server response MUST include contents array
        M052: Each content item MUST include uri and either text or blob
        S022: Each content item SHOULD include mimeType
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # First, get a resource URI from the resources/list endpoint
        list_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "list_for_read",
            "method": "resources/list"
        })
        
        list_data = list_response.json()
        if not list_data["result"]["resources"]:
            pytest.skip("No resources available to test reading")
        
        # Get the URI of the first resource
        resource_uri = list_data["result"]["resources"][0]["uri"]
        
        # Test resources/read with the URI
        read_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_resources_read",
            "method": "resources/read",
            "params": {
                "uri": resource_uri
            }
        })
        
        assert read_response.status_code == 200
        read_data = read_response.json()
        assert "result" in read_data
        assert "contents" in read_data["result"]
        
        # Verify contents structure
        contents = read_data["result"]["contents"]
        assert isinstance(contents, list)
        
        # Check each content item
        for content in contents:
            assert "uri" in content
            
            # Content must have either text or blob
            assert "text" in content or "blob" in content
            
            # Optional mimeType
            if "mimeType" in content:
                assert isinstance(content["mimeType"], str)
    
    @pytest.mark.requirement(["M053", "M054"])
    def test_resource_templates(self):
        """Test the resources/templates/list method.
        
        Tests requirements:
        M053: Server response MUST include resourceTemplates array
        M054: Each template MUST include uriTemplate
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # Send resources/templates/list request
        response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_resource_templates",
            "method": "resources/templates/list"
        })
        
        # This is an optional feature, so we accept either success or method not found
        if response.status_code == 200:
            data = response.json()
            
            # If the method is supported, verify response structure
            if "result" in data:
                assert "resourceTemplates" in data["result"]
                templates = data["result"]["resourceTemplates"]
                
                # If templates are returned, verify their structure
                if templates:
                    for template in templates:
                        assert "uriTemplate" in template
                        
                        # Optional fields
                        if "name" in template:
                            assert isinstance(template["name"], str)
                        if "description" in template:
                            assert isinstance(template["description"], str)
                        if "mimeType" in template:
                            assert isinstance(template["mimeType"], str)
    
    @pytest.mark.requirement(["M055", "M056"])
    def test_resource_subscribe(self):
        """Test resource subscription if supported.
        
        Tests requirements:
        M055: Server MUST send notifications/resources/updated when resource changes
        M056: Server MUST support subscribe capability to use this feature
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        if not self.server_capabilities.get("resources", {}).get("subscribe", False):
            pytest.skip("Server does not support resource subscriptions")
        
        # First, get a resource URI from the resources/list endpoint
        list_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "list_for_subscribe",
            "method": "resources/list"
        })
        
        list_data = list_response.json()
        if not list_data["result"]["resources"]:
            pytest.skip("No resources available to test subscription")
        
        # Get the URI of the first resource
        resource_uri = list_data["result"]["resources"][0]["uri"]
        
        # Test resources/subscribe with the URI
        subscribe_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_resource_subscribe",
            "method": "resources/subscribe",
            "params": {
                "uri": resource_uri
            }
        })
        
        assert subscribe_response.status_code == 200
        subscribe_data = subscribe_response.json()
        assert "result" in subscribe_data
        
        # Note: We can't test notifications in this synchronous test framework
        # A real test would need to set up a listener for notifications
    
    @pytest.mark.requirement(["M057", "S023"])
    def test_resource_list_changed_capability(self):
        """Test that the server declares list_changed capability if it uses the notification.
        
        Tests requirements:
        M057: Server MUST support listChanged capability to use this feature
        S023: Server SHOULD send notifications/resources/list_changed when resource list changes
        """
        if "resources" not in self.server_capabilities:
            pytest.skip("Server does not support resources feature")
        
        # Check if server declares listChanged capability
        list_changed_supported = self.server_capabilities.get("resources", {}).get("listChanged", False)
        
        # We can't test if the notification is actually sent,
        # but we can verify the capability is declared if required
        
        # Note: We can't fully test this as we'd need to trigger a list change
        # and capture the notification, which requires async communication
        
    # Remove the _send_request method since it's now provided by the parent class 