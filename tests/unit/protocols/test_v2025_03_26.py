"""
Tests for the 2025-03-26 MCP protocol adapter.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import json
import asyncio
import uuid

from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter
from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter
from mcp_testing.transports.base import MCPTransportAdapter


class TestMCP2025_03_26Adapter(unittest.TestCase):
    """Tests for the 2025-03-26 MCP protocol adapter."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_transport = MagicMock(spec=MCPTransportAdapter)
        self.mock_transport.send_request = AsyncMock()
        self.mock_transport.send_notification = AsyncMock()
        
        self.adapter = MCP2025_03_26Adapter(self.mock_transport, debug=True)
        self.adapter.initialized = True  # Set to True for most tests

    def test_inheritance(self):
        """Test that the adapter inherits from MCP2024_11_05Adapter."""
        self.assertTrue(issubclass(MCP2025_03_26Adapter, MCP2024_11_05Adapter))

    def test_init(self):
        """Test that the adapter initializes correctly."""
        adapter = MCP2025_03_26Adapter(self.mock_transport, debug=True)
        
        self.assertEqual(adapter.transport, self.mock_transport)
        self.assertTrue(adapter.debug)
        self.assertFalse(adapter.initialized)
        self.assertEqual(adapter.server_capabilities, {})
        self.assertEqual(adapter.server_info, {})
        self.assertIsNone(adapter.protocol_version)
        self.assertEqual(adapter.pending_tool_calls, {})

    def test_version(self):
        """Test that the version property returns the correct version."""
        self.assertEqual(self.adapter.version, "2025-03-26")

    @patch('uuid.uuid4')
    async def test_call_tool_async(self, mock_uuid):
        """Test the call_tool_async method."""
        mock_uuid.return_value = "test-uuid"
        tool_name = "test-tool"
        tool_args = {"arg1": "value1"}
        
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": "test-uuid",
            "result": {
                "id": "test-uuid",
                "status": "pending"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.call_tool_async(tool_name, tool_args)
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": "test-uuid",
            "method": "tools/call-async",
            "params": {
                "name": tool_name,
                "arguments": tool_args
            }
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request, expected_request)
        
        # Check that the result is correct
        self.assertEqual(result, {"id": "test-uuid", "status": "pending"})
        
        # Check that the pending tool call was stored
        self.assertEqual(self.adapter.pending_tool_calls["test-uuid"], {"id": "test-uuid", "status": "pending"})

    async def test_call_tool_async_not_initialized(self):
        """Test that call_tool_async raises an error if not initialized."""
        self.adapter.initialized = False
        
        with pytest.raises(ConnectionError, match="Cannot call tool before initialization"):
            await self.adapter.call_tool_async("test-tool", {})

    async def test_call_tool_async_error_response(self):
        """Test that call_tool_async handles error responses correctly."""
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": "test-uuid",
            "error": {
                "code": -32000,
                "message": "Test error"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Async tool call failed: Test error"):
            await self.adapter.call_tool_async("test-tool", {})

    async def test_get_tool_result(self):
        """Test the get_tool_result method."""
        tool_call_id = "test-tool-id"
        
        # Add a pending tool call
        self.adapter.pending_tool_calls[tool_call_id] = {"id": tool_call_id, "status": "pending"}
        
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": f"result_{tool_call_id}",
            "result": {
                "id": tool_call_id,
                "status": "completed",
                "result": {"output": "test-output"}
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.get_tool_result(tool_call_id)
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": f"result_{tool_call_id}",
            "method": "tools/result",
            "params": {
                "id": tool_call_id
            }
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request, expected_request)
        
        # Check that the result is correct
        expected_result = {
            "id": tool_call_id,
            "status": "completed",
            "result": {"output": "test-output"}
        }
        self.assertEqual(result, expected_result)
        
        # Check that the pending tool call was removed
        self.assertNotIn(tool_call_id, self.adapter.pending_tool_calls)

    async def test_get_tool_result_not_initialized(self):
        """Test that get_tool_result raises an error if not initialized."""
        self.adapter.initialized = False
        
        with pytest.raises(ConnectionError, match="Cannot get tool result before initialization"):
            await self.adapter.get_tool_result("test-tool-id")

    async def test_get_tool_result_error_response(self):
        """Test that get_tool_result handles error responses correctly."""
        tool_call_id = "test-tool-id"
        
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": f"result_{tool_call_id}",
            "error": {
                "code": -32000,
                "message": "Test error"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Failed to get tool result: Test error"):
            await self.adapter.get_tool_result(tool_call_id)

    async def test_cancel_tool_call(self):
        """Test the cancel_tool_call method."""
        tool_call_id = "test-tool-id"
        
        # Add a pending tool call
        self.adapter.pending_tool_calls[tool_call_id] = {"id": tool_call_id, "status": "pending"}
        
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": f"cancel_{tool_call_id}",
            "result": {
                "id": tool_call_id,
                "cancelled": True
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.cancel_tool_call(tool_call_id)
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": f"cancel_{tool_call_id}",
            "method": "tools/cancel",
            "params": {
                "id": tool_call_id
            }
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request, expected_request)
        
        # Check that the result is correct
        expected_result = {
            "id": tool_call_id,
            "cancelled": True
        }
        self.assertEqual(result, expected_result)
        
        # Check that the pending tool call was removed
        self.assertNotIn(tool_call_id, self.adapter.pending_tool_calls)

    async def test_cancel_tool_call_not_initialized(self):
        """Test that cancel_tool_call raises an error if not initialized."""
        self.adapter.initialized = False
        
        with pytest.raises(ConnectionError, match="Cannot cancel tool call before initialization"):
            await self.adapter.cancel_tool_call("test-tool-id")

    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_wait_for_tool_completion(self, mock_sleep):
        """Test the wait_for_tool_completion method."""
        tool_call_id = "test-tool-id"
        
        # Set up the get_tool_result method to return different responses on consecutive calls
        responses = [
            {"id": tool_call_id, "status": "pending"},
            {"id": tool_call_id, "status": "pending"},
            {"id": tool_call_id, "status": "completed", "result": {"output": "test-output"}}
        ]
        
        self.adapter.get_tool_result = AsyncMock(side_effect=responses)
        
        # Call the method
        result = await self.adapter.wait_for_tool_completion(tool_call_id, timeout=10, poll_interval=0.1)
        
        # Check that get_tool_result was called the expected number of times
        self.assertEqual(self.adapter.get_tool_result.call_count, 3)
        
        # Check that sleep was called the expected number of times
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Check that the result is correct
        expected_result = {
            "id": tool_call_id,
            "status": "completed",
            "result": {"output": "test-output"}
        }
        self.assertEqual(result, expected_result) 