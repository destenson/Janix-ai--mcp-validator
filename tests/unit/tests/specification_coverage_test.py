#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the specification_coverage module.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import json

from mcp_testing.tests import specification_coverage
from mcp_testing.protocols.base import MCPProtocolAdapter


class TestSpecificationCoverage(unittest.TestCase):
    """Test class for specification_coverage.py module."""

    @pytest.mark.asyncio
    async def test_test_jsonrpc_id_handling(self):
        """Test the test_jsonrpc_id_handling function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Test with a successful response
        mock_protocol.send_jsonrpc_request.return_value = {"id": "test-id", "result": {}}
        
        result, message = await specification_coverage.test_jsonrpc_id_handling(mock_protocol)
        self.assertTrue(result)
        self.assertIn("correctly handles JSON-RPC ID", message)
        mock_protocol.send_jsonrpc_request.assert_called_once()
        
        # Test with a response missing ID
        mock_protocol.send_jsonrpc_request.reset_mock()
        mock_protocol.send_jsonrpc_request.return_value = {"result": {}}
        
        result, message = await specification_coverage.test_jsonrpc_id_handling(mock_protocol)
        self.assertFalse(result)
        self.assertIn("missing 'id' field", message)
        mock_protocol.send_jsonrpc_request.assert_called_once()
        
        # Test with a mismatched ID
        mock_protocol.send_jsonrpc_request.reset_mock()
        mock_protocol.send_jsonrpc_request.return_value = {"id": "wrong-id", "result": {}}
        
        result, message = await specification_coverage.test_jsonrpc_id_handling(mock_protocol)
        self.assertFalse(result)
        self.assertIn("did not return the same ID", message)
        mock_protocol.send_jsonrpc_request.assert_called_once()
        
        # Test with an exception
        mock_protocol.send_jsonrpc_request.reset_mock()
        mock_protocol.send_jsonrpc_request.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_jsonrpc_id_handling(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)
        mock_protocol.send_jsonrpc_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_jsonrpc_version_handling(self):
        """Test the test_jsonrpc_version_handling function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Setup transport to capture raw requests
        mock_transport = MagicMock()
        mock_protocol.transport = mock_transport
        
        # Test with a properly formatted request
        mock_request = json.dumps({"jsonrpc": "2.0", "method": "test", "id": "1"})
        mock_transport.send_raw_request.return_value = {"id": "1", "result": {}}
        
        with patch('mcp_testing.tests.specification_coverage.json.loads', return_value={"jsonrpc": "2.0"}):
            result, message = await specification_coverage.test_jsonrpc_version_handling(mock_protocol)
            self.assertTrue(result)
            self.assertIn("correctly includes jsonrpc", message)
        
        # Test with a missing jsonrpc field
        with patch('mcp_testing.tests.specification_coverage.json.loads', return_value={}):
            result, message = await specification_coverage.test_jsonrpc_version_handling(mock_protocol)
            self.assertFalse(result)
            self.assertIn("is missing the 'jsonrpc' field", message)
        
        # Test with an incorrect jsonrpc version
        with patch('mcp_testing.tests.specification_coverage.json.loads', return_value={"jsonrpc": "1.0"}):
            result, message = await specification_coverage.test_jsonrpc_version_handling(mock_protocol)
            self.assertFalse(result)
            self.assertIn("has incorrect jsonrpc version", message)
        
        # Test with an exception
        mock_transport.send_raw_request.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_jsonrpc_version_handling(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)

    @pytest.mark.asyncio
    async def test_test_protocol_version_header(self):
        """Test the test_protocol_version_header function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        mock_protocol.version = "2025-03-26"
        
        # Test with a transport that supports get_headers
        mock_transport = MagicMock()
        mock_transport.get_headers.return_value = {"MCP-Version": "2025-03-26"}
        mock_protocol.transport = mock_transport
        
        result, message = await specification_coverage.test_protocol_version_header(mock_protocol)
        self.assertTrue(result)
        self.assertIn("correctly sets the MCP-Version header", message)
        
        # Test with a mismatched version
        mock_transport.get_headers.return_value = {"MCP-Version": "2024-11-05"}
        
        result, message = await specification_coverage.test_protocol_version_header(mock_protocol)
        self.assertFalse(result)
        self.assertIn("header does not match the expected protocol version", message)
        
        # Test with a missing header
        mock_transport.get_headers.return_value = {}
        
        result, message = await specification_coverage.test_protocol_version_header(mock_protocol)
        self.assertFalse(result)
        self.assertIn("does not set the MCP-Version header", message)
        
        # Test with an exception
        mock_transport.get_headers.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_protocol_version_header(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)
        
        # Test with a transport that doesn't support headers
        mock_protocol.transport = AsyncMock()  # without get_headers method
        
        result, message = await specification_coverage.test_protocol_version_header(mock_protocol)
        self.assertTrue(result)
        self.assertIn("Transport does not support headers", message)

    @pytest.mark.asyncio
    async def test_test_initialize_content_type(self):
        """Test the test_initialize_content_type function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Test with a transport that supports get_headers
        mock_transport = MagicMock()
        mock_transport.get_headers.return_value = {"Content-Type": "application/json"}
        mock_protocol.transport = mock_transport
        
        result, message = await specification_coverage.test_initialize_content_type(mock_protocol)
        self.assertTrue(result)
        self.assertIn("correctly sets the Content-Type header", message)
        
        # Test with an incorrect content type
        mock_transport.get_headers.return_value = {"Content-Type": "text/plain"}
        
        result, message = await specification_coverage.test_initialize_content_type(mock_protocol)
        self.assertFalse(result)
        self.assertIn("has incorrect Content-Type", message)
        
        # Test with a missing content type
        mock_transport.get_headers.return_value = {}
        
        result, message = await specification_coverage.test_initialize_content_type(mock_protocol)
        self.assertFalse(result)
        self.assertIn("does not set the Content-Type header", message)
        
        # Test with an exception
        mock_transport.get_headers.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_initialize_content_type(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)
        
        # Test with a transport that doesn't support headers
        mock_protocol.transport = AsyncMock()  # without get_headers method
        
        result, message = await specification_coverage.test_initialize_content_type(mock_protocol)
        self.assertTrue(result)
        self.assertIn("Transport does not support headers", message)

    @pytest.mark.asyncio
    async def test_test_initialization_contains_required_fields(self):
        """Test the test_initialization_contains_required_fields function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Test with a complete response
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": {
                    "streaming": True,
                    "tools": True
                }
            }
        }
        
        result, message = await specification_coverage.test_initialization_contains_required_fields(mock_protocol)
        self.assertTrue(result)
        self.assertIn("response contains all required fields", message)
        
        # Test with a missing capabilities field
        mock_protocol.initialize.return_value = {
            "config": {}
        }
        
        result, message = await specification_coverage.test_initialization_contains_required_fields(mock_protocol)
        self.assertFalse(result)
        self.assertIn("missing 'capabilities' field", message)
        
        # Test with a missing config field
        mock_protocol.initialize.return_value = {}
        
        result, message = await specification_coverage.test_initialization_contains_required_fields(mock_protocol)
        self.assertFalse(result)
        self.assertIn("missing 'config' field", message)
        
        # Test with a None response
        mock_protocol.initialize.return_value = None
        
        result, message = await specification_coverage.test_initialization_contains_required_fields(mock_protocol)
        self.assertFalse(result)
        self.assertIn("returned None", message)
        
        # Test with an exception
        mock_protocol.initialize.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_initialization_contains_required_fields(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)

    @pytest.mark.asyncio
    async def test_test_capabilities_field_is_object(self):
        """Test the test_capabilities_field_is_object function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Test with a proper capabilities object
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": {
                    "streaming": True,
                    "tools": True
                }
            }
        }
        
        result, message = await specification_coverage.test_capabilities_field_is_object(mock_protocol)
        self.assertTrue(result)
        self.assertIn("capabilities field is an object", message)
        
        # Test with a non-object capabilities field
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": "not-an-object"
            }
        }
        
        result, message = await specification_coverage.test_capabilities_field_is_object(mock_protocol)
        self.assertFalse(result)
        self.assertIn("capabilities field is not an object", message)
        
        # Test with a missing capabilities field
        mock_protocol.initialize.return_value = {
            "config": {}
        }
        
        result, message = await specification_coverage.test_capabilities_field_is_object(mock_protocol)
        self.assertFalse(result)
        self.assertIn("missing capabilities field", message)
        
        # Test with an exception
        mock_protocol.initialize.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_capabilities_field_is_object(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)

    @pytest.mark.asyncio
    async def test_test_capabilities_streaming_boolean(self):
        """Test the test_capabilities_streaming_boolean function."""
        # Create a mock protocol adapter
        mock_protocol = AsyncMock(spec=MCPProtocolAdapter)
        
        # Test with a proper streaming boolean
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": {
                    "streaming": True
                }
            }
        }
        
        result, message = await specification_coverage.test_capabilities_streaming_boolean(mock_protocol)
        self.assertTrue(result)
        self.assertIn("streaming capability is a boolean", message)
        
        # Test with a non-boolean streaming capability
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": {
                    "streaming": "not-a-boolean"
                }
            }
        }
        
        result, message = await specification_coverage.test_capabilities_streaming_boolean(mock_protocol)
        self.assertFalse(result)
        self.assertIn("streaming capability is not a boolean", message)
        
        # Test with a missing streaming capability
        mock_protocol.initialize.return_value = {
            "config": {
                "capabilities": {}
            }
        }
        
        result, message = await specification_coverage.test_capabilities_streaming_boolean(mock_protocol)
        self.assertFalse(result)
        self.assertIn("missing streaming capability", message)
        
        # Test with an exception
        mock_protocol.initialize.side_effect = Exception("Test error")
        
        result, message = await specification_coverage.test_capabilities_streaming_boolean(mock_protocol)
        self.assertFalse(result)
        self.assertIn("Exception during test", message)


if __name__ == "__main__":
    unittest.main() 