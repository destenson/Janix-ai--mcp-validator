#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Tools Tests

This module tests the tools-related aspects of the MCP protocol, focusing on:
1. Tools listing
2. Tools calling mechanisms
3. Protocol version differences in tool handling
4. Error handling for tools

These tests focus on the protocol mechanisms rather than specific tool implementations.
"""

import os
import pytest
import json
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")

class TestToolsProtocol(MCPBaseTest):
    """Test suite for MCP protocol tools functionality."""
    
    def get_init_capabilities(self):
        """Get appropriate capabilities based on protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "supports": {
                    "tools": True
                }
            }
        else:  # 2025-03-26 or later
            return {
                "tools": {
                    "listChanged": True
                }
            }
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_initialization(self):
        """Test the initialization process with tools capabilities."""
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
        assert "serverInfo" in init_data["result"]
        
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
    def test_tools_list_method(self):
        """Test the tools/list method to get available tools."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Request the list of tools
        tools_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tools_list",
            "method": "tools/list",
            "params": {}
        })
        
        assert tools_response.status_code == 200
        tools_data = tools_response.json()
        
        # Verify the response structure
        assert "result" in tools_data
        assert "tools" in tools_data["result"]
        assert isinstance(tools_data["result"]["tools"], list)
        
        # Store tools for later tests
        self.available_tools = tools_data["result"]["tools"]
        
        # Check that each tool has the required fields
        for tool in self.available_tools:
            assert "name" in tool
            assert "description" in tool
            
            # Parameters schema should be present for most tools
            if "parameters" in tool:
                # Parameters should follow JSON Schema format
                assert "type" in tool["parameters"]
                
                # If it has properties, they should be well-formed
                if "properties" in tool["parameters"]:
                    assert isinstance(tool["parameters"]["properties"], dict)
        
        print(f"\nFound {len(self.available_tools)} tools")
    
    @pytest.mark.v2025_03_26_only
    def test_tools_list_with_changes(self):
        """Test tools/list with listChanged parameter (2025-03-26+ only)."""
        # Skip for older protocol versions
        if self.protocol_version == "2024-11-05":
            pytest.skip("listChanged parameter not supported in 2024-11-05")
        
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # First get all tools
        tools_response = self._send_request({
            "jsonrpc": "2.0", 
            "id": "test_tools_list_all",
            "method": "tools/list",
            "params": {}
        })
        
        assert tools_response.status_code == 200
        all_tools = tools_response.json()["result"]["tools"]
        
        # Then request with listChanged=true
        changes_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tools_list_changes",
            "method": "tools/list",
            "params": {
                "listChanged": True
            }
        })
        
        # This should either return all tools again (first request) or an empty list (no changes)
        assert changes_response.status_code == 200
        changes_data = changes_response.json()
        
        assert "result" in changes_data
        assert "tools" in changes_data["result"]
        assert isinstance(changes_data["result"]["tools"], list)
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_tools_call_basic(self):
        """Test the basic tools/call method."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
            
        # Get available tools if needed
        if not hasattr(self, 'available_tools'):
            self.test_tools_list_method()
            
        if not self.available_tools:
            pytest.skip("No tools available to test")
            
        # Find a simple tool to test
        # We'll try to find a tool that doesn't have required parameters first
        test_tool = None
        for tool in self.available_tools:
            if "parameters" not in tool or "required" not in tool["parameters"] or not tool["parameters"]["required"]:
                test_tool = tool
                break
                
        # If all tools have required parameters, just use the first one
        # and we'll test error handling separately
        if not test_tool and self.available_tools:
            test_tool = self.available_tools[0]
            
        if not test_tool:
            pytest.skip("No suitable tool found for testing")
            
        print(f"\nTesting tool: {test_tool['name']}")
        
        # Try calling the tool with empty arguments
        call_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_tool_call",
            "method": "tools/call",
            "params": {
                "name": test_tool["name"],
                "arguments": {}
            }
        })
        
        # If the tool requires parameters, we expect an error
        # If not, we expect success
        if "parameters" in test_tool and "required" in test_tool["parameters"] and test_tool["parameters"]["required"]:
            # Should return error for missing required parameters
            assert call_response.status_code in [200, 400]
            call_data = call_response.json()
            
            if "error" in call_data:
                assert "code" in call_data["error"]
                assert "message" in call_data["error"]
                print(f"Expected error: {call_data['error']['message']}")
            else:
                # Some servers might be lenient about required parameters
                print("Server accepted empty arguments for tool that has required parameters")
        else:
            # Should succeed for tools without required parameters
            assert call_response.status_code == 200
            call_data = call_response.json()
            assert "result" in call_data
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_tools_call_error_handling(self):
        """Test error handling for tools/call with invalid arguments."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # 1. Test with non-existent tool
        invalid_tool_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_tool",
            "method": "tools/call",
            "params": {
                "name": "non_existent_tool_name",
                "arguments": {}
            }
        })
        
        # Should return error for non-existent tool
        assert invalid_tool_response.status_code in [200, 400, 404]
        invalid_tool_data = invalid_tool_response.json()
        
        assert "error" in invalid_tool_data
        assert "code" in invalid_tool_data["error"]
        assert "message" in invalid_tool_data["error"]
        
        # 2. Test with invalid method
        invalid_method_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_method",
            "method": "tools/invalid_method",
            "params": {}
        })
        
        # Should return error for invalid method
        assert invalid_method_response.status_code in [200, 400, 404, 405]
        invalid_method_data = invalid_method_response.json()
        
        assert "error" in invalid_method_data
        assert "code" in invalid_method_data["error"]
        assert "message" in invalid_method_data["error"]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_tools_call_with_jsonrpc_batch(self):
        """Test tools/call with JSON-RPC batch requests (if supported)."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
            
        # Get available tools if needed
        if not hasattr(self, 'available_tools'):
            self.test_tools_list_method()
            
        if not self.available_tools or len(self.available_tools) < 2:
            pytest.skip("Not enough tools available to test batch requests")
        
        # Select two tools for testing
        tool1 = self.available_tools[0]
        tool2 = self.available_tools[1]
        
        # Create a batch request
        batch_request = [
            {
                "jsonrpc": "2.0",
                "id": "batch_1",
                "method": "tools/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": "batch_2",
                "method": "tools/call",
                "params": {
                    "name": tool1["name"],
                    "arguments": {}
                }
            }
        ]
        
        # Send batch request
        batch_response = self._send_request(batch_request)
        
        # Batch requests might not be supported by all servers
        # If supported, we expect a 200 response with an array of results
        if batch_response.status_code == 200:
            batch_data = batch_response.json()
            
            # Should be an array of responses
            if isinstance(batch_data, list):
                assert len(batch_data) == 2
                print("\nBatch requests are supported")
                
                # Check individual responses
                for response in batch_data:
                    assert "jsonrpc" in response
                    assert "id" in response
                    assert response["id"] in ["batch_1", "batch_2"]
            else:
                print("\nServer responded to batch request but didn't return an array")
        else:
            print("\nBatch requests might not be supported (non-200 response)")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_server_info(self):
        """Test the server/info method if available."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Request server info
        server_info_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_server_info",
            "method": "server/info",
            "params": {}
        })
        
        # server/info is optional, so it might not be implemented
        if server_info_response.status_code == 200:
            server_info_data = server_info_response.json()
            
            if "result" in server_info_data:
                # Server implemented server/info
                print("\nserver/info is implemented")
                assert isinstance(server_info_data["result"], dict)
                
                # Check for common fields
                if "version" in server_info_data["result"]:
                    print(f"Server version: {server_info_data['result']['version']}")
                
                if "name" in server_info_data["result"]:
                    print(f"Server name: {server_info_data['result']['name']}")
            else:
                # Error response
                print("\nserver/info returned an error")
        else:
            print("\nserver/info might not be implemented")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_shutdown(self):
        """Test the shutdown method."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
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