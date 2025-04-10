"""
Tests for the 2024-11-05 MCP protocol adapter.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import json

from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter
from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.transports.base import MCPTransportAdapter


class TestMCP2024_11_05Adapter(unittest.TestCase):
    """Tests for the 2024-11-05 MCP protocol adapter."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_transport = MagicMock(spec=MCPTransportAdapter)
        self.mock_transport.send_request = AsyncMock()
        self.mock_transport.send_notification = AsyncMock()
        
        self.adapter = MCP2024_11_05Adapter(self.mock_transport, debug=True)
        self.adapter.initialized = True  # Set to True for most tests

    def test_inheritance(self):
        """Test that the adapter inherits from MCPProtocolAdapter."""
        self.assertTrue(issubclass(MCP2024_11_05Adapter, MCPProtocolAdapter))

    def test_init(self):
        """Test that the adapter initializes correctly."""
        adapter = MCP2024_11_05Adapter(self.mock_transport, debug=True)
        
        self.assertEqual(adapter.transport, self.mock_transport)
        self.assertTrue(adapter.debug)
        self.assertFalse(adapter.initialized)
        self.assertEqual(adapter.server_capabilities, {})
        self.assertEqual(adapter.server_info, {})
        self.assertIsNone(adapter.protocol_version)

    def test_version(self):
        """Test that the version property returns the correct version."""
        self.assertEqual(self.adapter.version, "2024-11-05")

    async def test_initialize(self):
        """Test the initialize method."""
        client_capabilities = {"test": "capability"}
        
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "protocolVersion": "2024-11-05",
                    "tools": True
                },
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0.0"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.initialize(client_capabilities)
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "capabilities": client_capabilities,
                "protocolVersion": "2024-11-05"
            }
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request["jsonrpc"], expected_request["jsonrpc"])
        self.assertEqual(actual_request["method"], expected_request["method"])
        self.assertEqual(actual_request["params"], expected_request["params"])
        
        # Check that the result is correct
        expected_result = {
            "capabilities": {
                "protocolVersion": "2024-11-05",
                "tools": True
            },
            "serverInfo": {
                "name": "test-server",
                "version": "1.0.0"
            }
        }
        self.assertEqual(result, expected_result)
        
        # Check that the adapter state was updated correctly
        self.assertTrue(self.adapter.initialized)
        self.assertEqual(self.adapter.server_capabilities, expected_result["capabilities"])
        self.assertEqual(self.adapter.server_info, expected_result["serverInfo"])
        self.assertEqual(self.adapter.protocol_version, "2024-11-05")

    async def test_initialize_with_null_capabilities(self):
        """Test initialize with null client capabilities."""
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "protocolVersion": "2024-11-05",
                    "tools": True
                },
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0.0"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method with None capabilities
        result = await self.adapter.initialize(None)
        
        # Check that the request included empty capabilities
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request["params"]["capabilities"], {})

    async def test_initialize_error(self):
        """Test initialize handling error responses."""
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": "Initialization failed"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Initialization failed: Initialization failed"):
            await self.adapter.initialize({})

    async def test_send_initialized(self):
        """Test the send_initialized method."""
        # Call the method
        await self.adapter.send_initialized()
        
        # Check that the notification was sent correctly
        expected_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        self.mock_transport.send_notification.assert_called_once_with(expected_notification)

    async def test_get_tools_list(self):
        """Test the get_tools_list method."""
        # Set up the mock response
        mock_tools = [
            {
                "name": "test-tool-1",
                "description": "Test tool 1",
                "parameters": {}
            },
            {
                "name": "test-tool-2",
                "description": "Test tool 2",
                "parameters": {}
            }
        ]
        mock_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": mock_tools
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.get_tools_list()
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request["jsonrpc"], expected_request["jsonrpc"])
        self.assertEqual(actual_request["method"], expected_request["method"])
        self.assertEqual(actual_request["params"], expected_request["params"])
        
        # Check that the result is correct
        self.assertEqual(result, mock_tools)

    async def test_get_tools_list_not_initialized(self):
        """Test that get_tools_list raises an error if not initialized."""
        self.adapter.initialized = False
        
        with pytest.raises(ConnectionError, match="Cannot get tools list before initialization"):
            await self.adapter.get_tools_list()

    async def test_get_tools_list_error(self):
        """Test that get_tools_list handles error responses correctly."""
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {
                "code": -32000,
                "message": "Failed to get tools list"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Failed to get tools list: Failed to get tools list"):
            await self.adapter.get_tools_list()

    async def test_call_tool(self):
        """Test the call_tool method."""
        tool_name = "test-tool"
        tool_args = {"arg1": "value1"}
        
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "output": "test-output"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        result = await self.adapter.call_tool(tool_name, tool_args)
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_args
            }
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request["jsonrpc"], expected_request["jsonrpc"])
        self.assertEqual(actual_request["method"], expected_request["method"])
        self.assertEqual(actual_request["params"], expected_request["params"])
        
        # Check that the result is correct
        expected_result = {
            "output": "test-output"
        }
        self.assertEqual(result, expected_result)

    async def test_call_tool_not_initialized(self):
        """Test that call_tool raises an error if not initialized."""
        self.adapter.initialized = False
        
        with pytest.raises(ConnectionError, match="Cannot call tool before initialization"):
            await self.adapter.call_tool("test-tool", {})

    async def test_call_tool_error(self):
        """Test that call_tool handles error responses correctly."""
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {
                "code": -32000,
                "message": "Failed to call tool"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Tool call failed: Failed to call tool"):
            await self.adapter.call_tool("test-tool", {})

    async def test_shutdown(self):
        """Test the shutdown method."""
        # Set up the mock response
        mock_response = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": None
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method
        await self.adapter.shutdown()
        
        # Check that the request was sent correctly
        expected_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "shutdown",
            "params": {}
        }
        self.mock_transport.send_request.assert_called_once()
        actual_request = self.mock_transport.send_request.call_args[0][0]
        self.assertEqual(actual_request["jsonrpc"], expected_request["jsonrpc"])
        self.assertEqual(actual_request["method"], expected_request["method"])
        self.assertEqual(actual_request["params"], expected_request["params"])

    async def test_shutdown_error(self):
        """Test that shutdown handles error responses correctly."""
        # Set up the mock response with an error
        mock_response = {
            "jsonrpc": "2.0",
            "id": 4,
            "error": {
                "code": -32000,
                "message": "Shutdown failed"
            }
        }
        self.mock_transport.send_request.return_value = mock_response
        
        # Call the method and check that it raises the correct error
        with pytest.raises(ConnectionError, match="Shutdown failed: Shutdown failed"):
            await self.adapter.shutdown()

    async def test_exit(self):
        """Test the exit method."""
        # Call the method
        await self.adapter.exit()
        
        # Check that the notification was sent correctly
        expected_notification = {
            "jsonrpc": "2.0",
            "method": "exit",
            "params": {}
        }
        self.mock_transport.send_notification.assert_called_once_with(expected_notification) 