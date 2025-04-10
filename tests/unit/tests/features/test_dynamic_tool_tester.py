#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the dynamic_tool_tester module.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from mcp_testing.tests.features import dynamic_tool_tester
from mcp_testing.protocols.base import MCPProtocolAdapter


class TestDynamicToolTester(unittest.TestCase):
    """Test class for dynamic_tool_tester.py module."""

    @pytest.mark.asyncio
    async def test_test_dynamic_tools_list(self):
        """Test the test_dynamic_tools_list function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with some tools
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"},
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Call the test function
        result, message = await dynamic_tool_tester.test_dynamic_tools_list(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Retrieved 2 tools", message)
        mock_protocol.get_tools_list.assert_called_once()
        
        # Test with no tools
        mock_protocol.get_tools_list.reset_mock()
        mock_protocol.get_tools_list.return_value = []
        
        result, message = await dynamic_tool_tester.test_dynamic_tools_list(mock_protocol)
        self.assertTrue(result)
        self.assertIn("Retrieved 0 tools", message)
        mock_protocol.get_tools_list.assert_called_once()
        
        # Test with an exception
        mock_protocol.get_tools_list.reset_mock()
        mock_protocol.get_tools_list.side_effect = Exception("Test error")
        
        result, message = await dynamic_tool_tester.test_dynamic_tools_list(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Error retrieving tools list", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_dynamic_get_required_tools(self):
        """Test the test_dynamic_get_required_tools function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock environment without required tools
        with patch.dict('os.environ', {}, clear=True):
            result, message = await dynamic_tool_tester.test_dynamic_get_required_tools(mock_protocol)
            self.assertTrue(result)
            self.assertIn("No required tools specified", message)
        
        # Mock environment with required tools
        with patch.dict('os.environ', {'MCP_REQUIRED_TOOLS': 'tool1,tool2'}):
            result, message = await dynamic_tool_tester.test_dynamic_get_required_tools(mock_protocol)
            self.assertTrue(result)
            self.assertIn("Required tools: tool1, tool2", message)

    @pytest.mark.asyncio
    async def test_test_dynamic_tool_list_required_tools(self):
        """Test the test_dynamic_tool_list_required_tools function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with all required tools
        mock_protocol.get_tools_list.return_value = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"},
            {"name": "extra_tool", "description": "Extra tool"}
        ]
        
        # Mock environment with required tools
        with patch.dict('os.environ', {'MCP_REQUIRED_TOOLS': 'tool1,tool2'}):
            result, message = await dynamic_tool_tester.test_dynamic_tool_list_required_tools(mock_protocol)
            self.assertTrue(result)
            self.assertIn("All required tools are available", message)
        
        # Test with missing tools
        mock_protocol.get_tools_list.return_value = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "extra_tool", "description": "Extra tool"}
        ]
        
        with patch.dict('os.environ', {'MCP_REQUIRED_TOOLS': 'tool1,tool2'}):
            result, message = await dynamic_tool_tester.test_dynamic_tool_list_required_tools(mock_protocol)
            self.assertFalse(result)
            self.assertIn("Missing required tools", message)
            self.assertIn("tool2", message)
        
        # Test with no required tools
        with patch.dict('os.environ', {}, clear=True):
            result, message = await dynamic_tool_tester.test_dynamic_tool_list_required_tools(mock_protocol)
            self.assertTrue(result)
            self.assertIn("No required tools specified", message)
        
        # Test with an exception
        mock_protocol.get_tools_list.side_effect = Exception("Test error")
        
        with patch.dict('os.environ', {'MCP_REQUIRED_TOOLS': 'tool1,tool2'}):
            result, message = await dynamic_tool_tester.test_dynamic_tool_list_required_tools(mock_protocol)
            self.assertFalse(result)
            self.assertIn("Error checking required tools", message)

    @pytest.mark.asyncio
    async def test_test_dynamic_echo_tool(self):
        """Test the test_dynamic_echo_tool function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool response for echo
        test_message = "Hello, Dynamic Tool Tester!"
        mock_protocol.call_tool.return_value = {
            "content": {"echo": test_message}
        }
        
        # Call the test function
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Echo tool works correctly", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()
        
        # Test when echo tool is not available
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "other_tool", "description": "Some other tool"}
        ]
        
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        self.assertTrue(result)
        self.assertIn("Echo tool not available", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_not_called()
        
        # Test with incorrect response format
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        mock_protocol.call_tool.return_value = {
            "content": "not-a-dict"
        }
        
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Echo tool did not return the expected format", message)
        
        # Test with missing content
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        mock_protocol.call_tool.return_value = {}
        
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Echo tool response is missing 'content' property", message)
        
        # Test with incorrect echo value
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        mock_protocol.call_tool.return_value = {
            "content": {"echo": "Wrong message"}
        }
        
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Echo tool did not return the same text", message)
        
        # Test with an exception
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        mock_protocol.call_tool.side_effect = Exception("Test error")
        
        result, message = await dynamic_tool_tester.test_dynamic_echo_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Failed to test echo tool", message)

    @pytest.mark.asyncio
    async def test_test_dynamic_add_tool(self):
        """Test the test_dynamic_add_tool function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with add tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Mock the call_tool response for add
        mock_protocol.call_tool.return_value = {
            "content": {"sum": 100}
        }
        
        # Call the test function
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Add tool works correctly", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()
        
        # Test when add tool is not available
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "other_tool", "description": "Some other tool"}
        ]
        
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        self.assertTrue(result)
        self.assertIn("Add tool not available", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_not_called()
        
        # Test with incorrect response format
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        mock_protocol.call_tool.return_value = {
            "content": "not-a-dict"
        }
        
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Add tool did not return the expected format", message)
        
        # Test with missing content
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        mock_protocol.call_tool.return_value = {}
        
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Add tool response is missing 'content' property", message)
        
        # Test with incorrect sum value
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        mock_protocol.call_tool.return_value = {
            "content": {"sum": 99}  # Should be 100
        }
        
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Add tool returned incorrect result", message)
        
        # Test with an exception
        mock_protocol.reset_mock()
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        mock_protocol.call_tool.side_effect = Exception("Test error")
        
        result, message = await dynamic_tool_tester.test_dynamic_add_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Failed to test add tool", message)

    @pytest.mark.asyncio
    async def test_test_dynamic_invalid_tool(self):
        """Test the test_dynamic_invalid_tool function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the call_tool to raise an exception (expected behavior)
        mock_protocol.call_tool.side_effect = Exception("Tool not found")
        
        # Call the test function
        result, message = await dynamic_tool_tester.test_dynamic_invalid_tool(mock_protocol)
        
        # Verify the test passed (because rejection is expected)
        self.assertTrue(result)
        self.assertIn("Server correctly rejected invalid tool call", message)
        mock_protocol.call_tool.assert_called_once()
        
        # Test when server doesn't reject the invalid tool
        mock_protocol.reset_mock()
        mock_protocol.call_tool.side_effect = None
        mock_protocol.call_tool.return_value = {"content": "some response"}
        
        result, message = await dynamic_tool_tester.test_dynamic_invalid_tool(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Server did not reject call to non-existent tool", message)
        mock_protocol.call_tool.assert_called_once()


if __name__ == "__main__":
    unittest.main() 