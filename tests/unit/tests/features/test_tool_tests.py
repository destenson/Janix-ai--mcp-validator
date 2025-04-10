#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the feature test modules.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from mcp_testing.tests.features import test_tools
from mcp_testing.protocols.base import MCPProtocolAdapter


class TestToolsTests(unittest.TestCase):
    """Test class for test_tools.py module."""

    @pytest.mark.asyncio
    async def test_tools_list_success(self):
        """Test the test_tools_list function with a valid response."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"},
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertEqual(message, "Successfully retrieved 2 tools")
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_tools_list_not_array(self):
        """Test the test_tools_list function with a non-array response."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response
        mock_protocol.get_tools_list.return_value = {"tools": []}
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Expected tools list to be an array", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_tools_list_invalid_tool(self):
        """Test the test_tools_list function with an invalid tool."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with an invalid tool (not a dict)
        mock_protocol.get_tools_list.return_value = [
            "not-a-dict"
        ]
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Tool at index 0 is not an object", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_tools_list_missing_name(self):
        """Test the test_tools_list function with a tool missing the name property."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with a tool missing a name
        mock_protocol.get_tools_list.return_value = [
            {"description": "Tool without a name"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("missing required 'name' property", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_tools_list_missing_description(self):
        """Test the test_tools_list function with a tool missing the description property."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with a tool missing a description
        mock_protocol.get_tools_list.return_value = [
            {"name": "tool-without-description"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("missing required 'description' property", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_tools_list_exception(self):
        """Test the test_tools_list function when an exception occurs."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list to raise an exception
        mock_protocol.get_tools_list.side_effect = Exception("Test error")
        
        # Call the test function
        result, message = await test_tools.test_tools_list(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Failed to retrieve tools list", message)
        self.assertIn("Test error", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_echo_tool_not_available(self):
        """Test the test_echo_tool function when the echo tool is not available."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response without the echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_echo_tool(mock_protocol)
        
        # Verify the test was skipped (but considered passing)
        self.assertTrue(result)
        self.assertEqual(message, "Echo tool not available (skipping test)")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_echo_tool_success(self):
        """Test the test_echo_tool function with a valid response."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool response
        test_message = "Hello, MCP Testing Framework!"
        mock_protocol.call_tool.return_value = {
            "content": {"echo": test_message}
        }
        
        # Call the test function
        result, message = await test_tools.test_echo_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertEqual(message, "Echo tool works correctly")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once_with("echo", {"text": test_message})

    @pytest.mark.asyncio
    async def test_echo_tool_missing_content(self):
        """Test the test_echo_tool function when content is missing from the response."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool response without content
        mock_protocol.call_tool.return_value = {}
        
        # Call the test function
        result, message = await test_tools.test_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertEqual(message, "Echo tool response is missing 'content' property")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_echo_tool_invalid_format(self):
        """Test the test_echo_tool function when the response format is invalid."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool response with invalid format
        mock_protocol.call_tool.return_value = {
            "content": "not-a-dict"
        }
        
        # Call the test function
        result, message = await test_tools.test_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Echo tool did not return the expected format", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_echo_tool_wrong_content(self):
        """Test the test_echo_tool function when the echo content is incorrect."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool response with wrong content
        test_message = "Hello, MCP Testing Framework!"
        mock_protocol.call_tool.return_value = {
            "content": {"echo": "Wrong message"}
        }
        
        # Call the test function
        result, message = await test_tools.test_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Echo tool did not return the same text", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_tool_not_available(self):
        """Test the test_add_tool function when the add tool is not available."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response without the add tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_add_tool(mock_protocol)
        
        # Verify the test was skipped (but considered passing)
        self.assertTrue(result)
        self.assertEqual(message, "Add tool not available (skipping test)")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_tool_success(self):
        """Test the test_add_tool function with a valid response."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with add tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Mock the call_tool response
        a, b = 42, 58
        mock_protocol.call_tool.return_value = {
            "content": {"sum": 100}
        }
        
        # Call the test function
        result, message = await test_tools.test_add_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertEqual(message, "Add tool works correctly")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once_with("add", {"a": a, "b": b})

    @pytest.mark.asyncio
    async def test_add_tool_wrong_result(self):
        """Test the test_add_tool function when the result is incorrect."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with add tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Mock the call_tool response with wrong sum
        mock_protocol.call_tool.return_value = {
            "content": {"sum": 99}  # Wrong sum (should be 100)
        }
        
        # Call the test function
        result, message = await test_tools.test_add_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Add tool returned incorrect result", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_tool_rejection(self):
        """Test the test_invalid_tool function when the server rejects the tool."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the call_tool to raise an exception (expected behavior)
        mock_protocol.call_tool.side_effect = Exception("Tool not found")
        
        # Call the test function
        result, message = await test_tools.test_invalid_tool(mock_protocol)
        
        # Verify the test passed (because rejection is expected)
        self.assertTrue(result)
        self.assertIn("Server correctly rejected invalid tool call", message)
        mock_protocol.call_tool.assert_called_once_with("non_existent_tool", {})

    @pytest.mark.asyncio
    async def test_invalid_tool_not_rejected(self):
        """Test the test_invalid_tool function when the server doesn't reject the tool."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the call_tool to NOT raise an exception (unexpected behavior)
        mock_protocol.call_tool.return_value = {"content": "some response"}
        
        # Call the test function
        result, message = await test_tools.test_invalid_tool(mock_protocol)
        
        # Verify the test failed (because the server should have rejected the tool)
        self.assertFalse(result)
        self.assertEqual(message, "Server did not reject call to non-existent tool")
        mock_protocol.call_tool.assert_called_once_with("non_existent_tool", {})

    @pytest.mark.asyncio
    async def test_invalid_params_no_suitable_tools(self):
        """Test the test_tool_with_invalid_params function when no suitable tools are available."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response without echo or add tools
        mock_protocol.get_tools_list.return_value = [
            {"name": "other_tool", "description": "Some other tool"}
        ]
        
        # Call the test function
        result, message = await test_tools.test_tool_with_invalid_params(mock_protocol)
        
        # Verify the test was skipped (but considered passing)
        self.assertTrue(result)
        self.assertEqual(message, "No suitable tools available for this test (skipping)")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_params_echo_rejection(self):
        """Test the test_tool_with_invalid_params function with echo tool that rejects invalid params."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool to raise an exception (expected behavior)
        mock_protocol.call_tool.side_effect = Exception("Missing required parameter")
        
        # Call the test function
        result, message = await test_tools.test_tool_with_invalid_params(mock_protocol)
        
        # Verify the test passed (because rejection is expected)
        self.assertTrue(result)
        self.assertIn("Server correctly rejected tool call with invalid parameters", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once_with("echo", {})

    @pytest.mark.asyncio
    async def test_invalid_params_add_rejection(self):
        """Test the test_tool_with_invalid_params function with add tool that rejects invalid params."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response without echo but with add tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "add", "description": "Adds two numbers"}
        ]
        
        # Mock the call_tool to raise an exception (expected behavior)
        mock_protocol.call_tool.side_effect = Exception("Invalid parameters")
        
        # Call the test function
        result, message = await test_tools.test_tool_with_invalid_params(mock_protocol)
        
        # Verify the test passed (because rejection is expected)
        self.assertTrue(result)
        self.assertIn("Server correctly rejected tool call with invalid parameters", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once_with("add", {"x": 1, "y": 2})

    @pytest.mark.asyncio
    async def test_invalid_params_not_rejected(self):
        """Test the test_tool_with_invalid_params function when the server doesn't reject invalid params."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool to NOT raise an exception (unexpected behavior)
        mock_protocol.call_tool.return_value = {"content": "some response"}
        
        # Call the test function
        result, message = await test_tools.test_tool_with_invalid_params(mock_protocol)
        
        # Verify the test failed (because the server should have rejected the params)
        self.assertFalse(result)
        self.assertEqual(message, "Server did not reject tool call with invalid parameters")
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool.assert_called_once()


if __name__ == "__main__":
    unittest.main() 