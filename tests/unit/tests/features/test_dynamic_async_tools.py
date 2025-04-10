#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the dynamic_async_tools module.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import asyncio

from mcp_testing.tests.features import dynamic_async_tools
from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter


class TestDynamicAsyncTools(unittest.TestCase):
    """Test class for dynamic_async_tools.py module."""

    @pytest.mark.asyncio
    async def test_test_async_tool_support_old_protocol(self):
        """Test the test_async_tool_support function with older protocol version."""
        # Create a mock protocol adapter with older protocol version
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2024-11-05"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_tool_support(mock_protocol)
        
        # Verify the test was skipped (returning True)
        self.assertTrue(result)
        self.assertIn("Async tool calls only supported in 2025-03-26", message)
        self.assertIn("skipping", message)

    @pytest.mark.asyncio
    async def test_test_async_tool_support_wrong_adapter_type(self):
        """Test the test_async_tool_support function with wrong adapter type."""
        # Create a mock protocol adapter with right version but wrong type
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2025-03-26"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_tool_support(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Protocol adapter does not support async tool calls", message)

    @pytest.mark.asyncio
    async def test_test_async_tool_support_success(self):
        """Test the test_async_tool_support function with correct adapter type."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_tool_support(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Protocol version and adapter support async tool calls", message)

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_skipped_old_protocol(self):
        """Test the test_async_echo_tool function with older protocol version."""
        # Create a mock protocol adapter with older protocol version
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2024-11-05"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test was skipped (returning True)
        self.assertTrue(result)
        self.assertIn("Async tool calls only supported in 2025-03-26", message)
        self.assertIn("skipping", message)

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_wrong_adapter_type(self):
        """Test the test_async_echo_tool function with wrong adapter type."""
        # Create a mock protocol adapter with right version but wrong type
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2025-03-26"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Protocol adapter does not support async tool calls", message)

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_no_echo_tool(self):
        """Test the test_async_echo_tool function when echo tool is not available."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response without echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "other_tool", "description": "Some other tool"}
        ]
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test was skipped (returning True)
        self.assertTrue(result)
        self.assertIn("Echo tool not available", message)
        self.assertIn("skipping test", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_success(self):
        """Test the test_async_echo_tool function with successful execution."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool_async and get_tool_result responses
        tool_call_id = "test-call-id"
        test_message = "Hello, Async Echo!"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {
            "status": "completed",
            "result": {"content": {"echo": test_message}}
        }
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Async echo tool works correctly", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_missing_id(self):
        """Test the test_async_echo_tool function when ID is missing from response."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool_async response without ID
        mock_protocol.call_tool_async.return_value = {}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Async tool call response is missing 'id' property", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_incomplete_status(self):
        """Test the test_async_echo_tool function when tool doesn't complete."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool_async and get_tool_result responses with non-completed status
        tool_call_id = "test-call-id"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {
            "status": "running"
        }
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Async tool call did not complete", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)

    @pytest.mark.asyncio
    async def test_test_async_echo_tool_wrong_result(self):
        """Test the test_async_echo_tool function when echo result is incorrect."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with echo tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "echo", "description": "Echoes the input text"}
        ]
        
        # Mock the call_tool_async and get_tool_result responses with wrong content
        tool_call_id = "test-call-id"
        test_message = "Hello, Async Echo!"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {
            "status": "completed",
            "result": {"content": {"echo": "Wrong message"}}
        }
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_echo_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Echo tool did not return the same text", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_skipped_old_protocol(self):
        """Test the test_async_long_running_tool function with older protocol version."""
        # Create a mock protocol adapter with older protocol version
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2024-11-05"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test was skipped (returning True)
        self.assertTrue(result)
        self.assertIn("Async tool calls only supported in 2025-03-26", message)
        self.assertIn("skipping", message)

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_wrong_adapter_type(self):
        """Test the test_async_long_running_tool function with wrong adapter type."""
        # Create a mock protocol adapter with right version but wrong type
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2025-03-26"
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Protocol adapter does not support async tool calls", message)

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_no_sleep_tool(self):
        """Test the test_async_long_running_tool function when sleep tool is not available."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response without sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "other_tool", "description": "Some other tool"}
        ]
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test was skipped (returning True)
        self.assertTrue(result)
        self.assertIn("Sleep tool not available", message)
        self.assertIn("skipping test", message)
        mock_protocol.get_tools_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_success(self):
        """Test the test_async_long_running_tool function with successful execution."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "sleep", "description": "Sleeps for a specified duration"}
        ]
        
        # Mock the call_tool_async, get_tool_result, and wait_for_tool_completion responses
        tool_call_id = "test-call-id"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {"status": "running"}
        mock_protocol.wait_for_tool_completion.return_value = {"status": "completed"}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test passed
        self.assertTrue(result)
        self.assertIn("Async long-running tool works correctly", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)
        mock_protocol.wait_for_tool_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_missing_id(self):
        """Test the test_async_long_running_tool function when ID is missing from response."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "sleep", "description": "Sleeps for a specified duration"}
        ]
        
        # Mock the call_tool_async response without ID
        mock_protocol.call_tool_async.return_value = {}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Async tool call response is missing 'id' property", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_missing_status(self):
        """Test the test_async_long_running_tool function when status is missing from response."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "sleep", "description": "Sleeps for a specified duration"}
        ]
        
        # Mock the call_tool_async and get_tool_result responses without status
        tool_call_id = "test-call-id"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Async tool result is missing 'status' property", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_unexpected_status(self):
        """Test the test_async_long_running_tool function with unexpected status."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "sleep", "description": "Sleeps for a specified duration"}
        ]
        
        # Mock the call_tool_async and get_tool_result responses with unexpected status
        tool_call_id = "test-call-id"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {"status": "unexpected_status"}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Unexpected initial status: unexpected_status", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)

    @pytest.mark.asyncio
    async def test_test_async_long_running_tool_not_completed(self):
        """Test the test_async_long_running_tool function when tool doesn't complete."""
        # Create a mock protocol adapter of correct type
        mock_protocol = AsyncMock(spec=MCP2025_03_26Adapter)
        mock_protocol.version = "2025-03-26"
        
        # Mock the get_tools_list response with sleep tool
        mock_protocol.get_tools_list.return_value = [
            {"name": "sleep", "description": "Sleeps for a specified duration"}
        ]
        
        # Mock the responses with non-completed status in wait_for_tool_completion
        tool_call_id = "test-call-id"
        mock_protocol.call_tool_async.return_value = {"id": tool_call_id}
        mock_protocol.get_tool_result.return_value = {"status": "running"}
        mock_protocol.wait_for_tool_completion.return_value = {"status": "running"}
        
        # Call the test function
        result, message = await dynamic_async_tools.test_async_long_running_tool(mock_protocol)
        
        # Verify the test failed
        self.assertFalse(result)
        self.assertIn("Async tool call did not complete", message)
        mock_protocol.get_tools_list.assert_called_once()
        mock_protocol.call_tool_async.assert_called_once()
        mock_protocol.get_tool_result.assert_called_once_with(tool_call_id)
        mock_protocol.wait_for_tool_completion.assert_called_once()


if __name__ == "__main__":
    unittest.main() 