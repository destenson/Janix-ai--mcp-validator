#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Basic Protocol Tests for STDIO Transport

Simplified test suite for testing MCP protocol initialization and basic capabilities
when using STDIO transport.
"""

import os
import json
import pytest
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")

class TestBasicSTDIO(MCPBaseTest):
    """Basic test suite for STDIO transport."""
    
    def get_init_capabilities(self):
        """Get appropriate capabilities based on protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "supports": {
                    "filesystem": True
                }
            }
        else:  # 2025-03-26 or later
            return {
                "tools": {
                    "listChanged": True
                },
                "resources": {}
            }
    
    def test_initialization(self):
        """Test the initialization process with the STDIO transport."""
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
    
    def test_tools_list(self):
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
        
        # Check for some common expected tools in filesystem servers
        tool_names = [tool["name"] for tool in tools_data["result"]["tools"]]
        print(f"\nAvailable tools: {', '.join(tool_names)}")
        
        # Filesystem servers should have these tools
        expected_tools = ["list_directory", "read_file"]
        found_tools = [tool for tool in expected_tools if tool in tool_names]
        if found_tools:
            print(f"Found expected filesystem tools: {', '.join(found_tools)}")
        else:
            print("Note: Common filesystem tools not found. This may be expected if testing a non-filesystem server.")
    
    def test_filesystem_operations(self):
        """Test basic filesystem operations using the tools."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Get the list of tools to check what's available
        tools_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_get_tools",
            "method": "tools/list",
            "params": {}
        })
        
        assert tools_response.status_code == 200
        tools_data = tools_response.json()
        tool_names = [tool["name"] for tool in tools_data["result"]["tools"]]
        
        # Skip if filesystem tools aren't available
        if "list_directory" not in tool_names or "read_file" not in tool_names:
            pytest.skip("Filesystem tools not available in this server")
        
        # 1. List allowed directories (if this tool exists)
        if "list_allowed_directories" in tool_names:
            list_allowed_dirs_response = self._send_request({
                "jsonrpc": "2.0",
                "id": "test_list_allowed_dirs",
                "method": "tools/call",
                "params": {
                    "name": "list_allowed_directories",
                    "arguments": {}
                }
            })
            
            assert list_allowed_dirs_response.status_code == 200
            list_allowed_dirs_data = list_allowed_dirs_response.json()
            assert "result" in list_allowed_dirs_data
            assert "content" in list_allowed_dirs_data["result"]
        
        # 2. List files in the root directory
        list_dir_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_list_dir",
            "method": "tools/call",
            "params": {
                "name": "list_directory",
                "arguments": {
                    "path": "/projects"
                }
            }
        })
        
        assert list_dir_response.status_code == 200
        list_dir_data = list_dir_response.json()
        assert "result" in list_dir_data
        assert "content" in list_dir_data["result"]
        
        # 3. Write a test file
        test_content = "This is a test file created by the test suite."
        write_file_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_write_file",
            "method": "tools/call",
            "params": {
                "name": "write_file",
                "arguments": {
                    "path": "/projects/files/test_file.txt",
                    "content": test_content
                }
            }
        })
        
        assert write_file_response.status_code == 200
        write_file_data = write_file_response.json()
        assert "result" in write_file_data
        
        # 4. Read the test file back
        read_file_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_read_file",
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "path": "/projects/files/test_file.txt"
                }
            }
        })
        
        assert read_file_response.status_code == 200
        read_file_data = read_file_response.json()
        assert "result" in read_file_data
        assert "content" in read_file_data["result"]
        
        # 5. Verify the content matches what we wrote
        content_items = read_file_data["result"]["content"]
        found_content = False
        for item in content_items:
            if item["type"] == "text" and test_content in item["text"]:
                found_content = True
                break
        
        assert found_content, "File content does not match what was written" 