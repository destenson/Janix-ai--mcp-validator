#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Resources Tests

This module tests the resource management aspects of the MCP protocol, focusing on:
1. Resource creation and tracking
2. Resource lifetime management
3. Protocol version differences in resource handling
4. Error handling for resources

These tests focus on the protocol mechanisms rather than specific resource implementations.
"""

import os
import pytest
import json
import time
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")

class TestResourcesProtocol(MCPBaseTest):
    """Test suite for MCP protocol resources functionality."""
    
    def get_init_capabilities(self):
        """Get appropriate capabilities based on protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "supports": {
                    "resources": True
                }
            }
        else:  # 2025-03-26 or later
            return {
                "resources": {}
            }
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_initialization(self):
        """Test the initialization process with resources capabilities."""
        # Send initialize request with appropriate capabilities for the protocol version
        init_capabilities = self.get_init_capabilities()
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_initialization",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": init_capabilities,
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        assert "capabilities" in init_data["result"]
        
        # Store the capabilities for later tests
        self.server_capabilities = init_data["result"]["capabilities"]
        self.negotiated_version = init_data["result"]["protocolVersion"]
        
        print(f"\nNegotiated protocol version: {self.negotiated_version}")
        print(f"Server capabilities: {json.dumps(self.server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_creation(self):
        """Test creating a resource."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if resources aren't supported
        has_resources = False
        if self.protocol_version == "2024-11-05":
            has_resources = self.server_capabilities.get("supports", {}).get("resources", False)
        else:
            has_resources = "resources" in self.server_capabilities
            
        if not has_resources:
            pytest.skip("Resources not supported by this server")
        
        # Create a test resource
        resource_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_create_resource",
            "method": "resources/create",
            "params": {
                "type": "test",
                "data": {
                    "test_key": "test_value"
                }
            }
        })
        
        # Check response (expected either success or not implemented)
        if resource_response.status_code == 200:
            resource_data = resource_response.json()
            
            if "result" in resource_data:
                # Success, store resource ID for later tests
                assert "id" in resource_data["result"]
                self.resource_id = resource_data["result"]["id"]
                print(f"\nCreated resource with ID: {self.resource_id}")
                return
            elif "error" in resource_data:
                # Method might return an error if not implemented
                error_code = resource_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("resources/create not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {resource_data['error']}"
        
        # Method might not be implemented
        pytest.skip("resources/create not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_get(self):
        """Test retrieving a resource by ID."""
        # Skip if we don't have a resource ID from a previous test
        if not hasattr(self, 'resource_id'):
            try:
                self.test_resource_creation()
            except:
                pytest.skip("Could not create a resource to test")
                
        if not hasattr(self, 'resource_id'):
            pytest.skip("No resource ID available for testing")
        
        # Get the resource
        get_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_get_resource",
            "method": "resources/get",
            "params": {
                "id": self.resource_id
            }
        })
        
        # Check response
        if get_response.status_code == 200:
            get_data = get_response.json()
            
            if "result" in get_data:
                # Resource retrieved successfully
                assert "id" in get_data["result"]
                assert get_data["result"]["id"] == self.resource_id
                assert "type" in get_data["result"]
                assert "data" in get_data["result"]
                print(f"\nRetrieved resource with ID: {self.resource_id}")
                return
            elif "error" in get_data:
                # Method might return an error if not implemented
                error_code = get_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("resources/get not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {get_data['error']}"
        
        # Method might not be implemented
        pytest.skip("resources/get not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_update(self):
        """Test updating a resource."""
        # Skip if we don't have a resource ID from a previous test
        if not hasattr(self, 'resource_id'):
            try:
                self.test_resource_creation()
            except:
                pytest.skip("Could not create a resource to test")
                
        if not hasattr(self, 'resource_id'):
            pytest.skip("No resource ID available for testing")
        
        # Update the resource
        update_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_update_resource",
            "method": "resources/update",
            "params": {
                "id": self.resource_id,
                "data": {
                    "test_key": "updated_value",
                    "updated_at": time.time()
                }
            }
        })
        
        # Check response
        if update_response.status_code == 200:
            update_data = update_response.json()
            
            if "result" in update_data:
                # Resource updated successfully
                assert "id" in update_data["result"]
                assert update_data["result"]["id"] == self.resource_id
                print(f"\nUpdated resource with ID: {self.resource_id}")
                return
            elif "error" in update_data:
                # Method might return an error if not implemented
                error_code = update_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("resources/update not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {update_data['error']}"
        
        # Method might not be implemented
        pytest.skip("resources/update not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_list(self):
        """Test listing available resources."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if resources aren't supported
        has_resources = False
        if self.protocol_version == "2024-11-05":
            has_resources = self.server_capabilities.get("supports", {}).get("resources", False)
        else:
            has_resources = "resources" in self.server_capabilities
            
        if not has_resources:
            pytest.skip("Resources not supported by this server")
        
        # Try to create a resource first if we haven't already
        if not hasattr(self, 'resource_id'):
            try:
                self.test_resource_creation()
            except:
                pass
        
        # List resources
        list_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_list_resources",
            "method": "resources/list",
            "params": {}
        })
        
        # Check response
        if list_response.status_code == 200:
            list_data = list_response.json()
            
            if "result" in list_data:
                # Resources listed successfully
                assert "resources" in list_data["result"]
                assert isinstance(list_data["result"]["resources"], list)
                print(f"\nFound {len(list_data['result']['resources'])} resources")
                return
            elif "error" in list_data:
                # Method might return an error if not implemented
                error_code = list_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("resources/list not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {list_data['error']}"
        
        # Method might not be implemented
        pytest.skip("resources/list not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_delete(self):
        """Test deleting a resource."""
        # Skip if we don't have a resource ID from a previous test
        if not hasattr(self, 'resource_id'):
            try:
                self.test_resource_creation()
            except:
                pytest.skip("Could not create a resource to test")
                
        if not hasattr(self, 'resource_id'):
            pytest.skip("No resource ID available for testing")
        
        # Delete the resource
        delete_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_delete_resource",
            "method": "resources/delete",
            "params": {
                "id": self.resource_id
            }
        })
        
        # Check response
        if delete_response.status_code == 200:
            delete_data = delete_response.json()
            
            if "result" in delete_data:
                # Resource deleted successfully
                print(f"\nDeleted resource with ID: {self.resource_id}")
                # Clear the resource ID since it's now deleted
                delattr(self, 'resource_id')
                return
            elif "error" in delete_data:
                # Method might return an error if not implemented
                error_code = delete_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("resources/delete not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {delete_data['error']}"
        
        # Method might not be implemented
        pytest.skip("resources/delete not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_resource_error_handling(self):
        """Test error handling for resource operations."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if resources aren't supported
        has_resources = False
        if self.protocol_version == "2024-11-05":
            has_resources = self.server_capabilities.get("supports", {}).get("resources", False)
        else:
            has_resources = "resources" in self.server_capabilities
            
        if not has_resources:
            pytest.skip("Resources not supported by this server")
        
        # 1. Try to get a non-existent resource
        nonexistent_id = "non_existent_resource_id"
        get_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_get_nonexistent",
            "method": "resources/get",
            "params": {
                "id": nonexistent_id
            }
        })
        
        # Check response
        if get_response.status_code == 200:
            get_data = get_response.json()
            
            if "error" in get_data:
                # Should return an error for non-existent resource
                assert "code" in get_data["error"]
                assert "message" in get_data["error"]
                print(f"\nProperly handled non-existent resource error: {get_data['error']['message']}")
            elif "result" in get_data:
                # If it returns a result, the server might have created a new resource on demand
                print("\nServer returned a result for non-existent resource (created on demand?)")
        elif get_response.status_code in [404, 400]:
            # HTTP-level error is also acceptable
            print("\nServer returned HTTP-level error for non-existent resource")
        
        # 2. Test with invalid method
        invalid_method_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_method",
            "method": "resources/invalid_method",
            "params": {}
        })
        
        # Should return error for invalid method
        assert invalid_method_response.status_code in [200, 400, 404, 405]
        invalid_method_data = invalid_method_response.json()
        
        if "error" in invalid_method_data:
            assert "code" in invalid_method_data["error"]
            assert "message" in invalid_method_data["error"]
            print(f"\nProperly handled invalid method error: {invalid_method_data['error']['message']}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_shutdown(self):
        """Test the shutdown method."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # First try to clean up any resources we created
        if hasattr(self, 'resource_id'):
            try:
                self._send_request({
                    "jsonrpc": "2.0",
                    "id": "cleanup_resource",
                    "method": "resources/delete",
                    "params": {
                        "id": self.resource_id
                    }
                })
                print(f"\nCleaned up resource with ID: {self.resource_id}")
            except:
                print(f"\nFailed to clean up resource with ID: {self.resource_id}")
        
        # Send shutdown request
        shutdown_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_shutdown",
            "method": "shutdown",
            "params": {}
        })
        
        assert shutdown_response.status_code == 200
        shutdown_data = shutdown_response.json()
        
        # Shutdown should return an empty result object
        assert "result" in shutdown_data
        
        # Send exit notification
        exit_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "exit"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert exit_notification.status_code in [200, 202, 204] 