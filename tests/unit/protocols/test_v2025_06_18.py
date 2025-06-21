#!/usr/bin/env python3
"""
Unit tests for MCP 2025-06-18 Protocol Adapter.

Tests the 2025-06-18 protocol implementation including OAuth 2.1,
structured tool output, elicitation support, and enhanced security.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from mcp_testing.protocols.v2025_06_18 import MCP2025_06_18Adapter
from mcp_testing.transports.base import MCPTransportAdapter


class TestMCP2025_06_18Adapter:
    """Test suite for MCP 2025-06-18 Protocol Adapter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_transport = AsyncMock(spec=MCPTransportAdapter)
        self.adapter = MCP2025_06_18Adapter(self.mock_transport)

    def test_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.version == "2025-06-18"
        assert self.adapter.transport == self.mock_transport
        assert not self.adapter.initialized
        # Check that it has the protocol version header
        assert hasattr(self.adapter, 'protocol_version_header')
        assert self.adapter.protocol_version_header == "2025-06-18"

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization with 2025-06-18 features."""
        # Mock successful response with 2025-06-18 capabilities
        mock_response = {
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {"supported": True},
                    "resources": {"supported": True},
                    "prompts": {"supported": True},
                    "elicitation": {"supported": True},
                    "oauth": {
                        "supported": True,
                        "flows": ["authorization_code"],
                        "scopes": ["read", "write"]
                    }
                },
                "serverInfo": {
                    "name": "Test Server 2025-06-18",
                    "version": "1.0.0"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.initialize({
            "client_info": {"name": "Test Client", "version": "1.0.0"},
            "client_capabilities": {"protocol_versions": ["2025-06-18"]}
        })

        assert self.adapter.initialized
        assert result["protocolVersion"] == "2025-06-18"
        assert self.adapter.server_capabilities["elicitation"]["supported"]
        assert self.adapter.server_capabilities["oauth"]["supported"]

    @pytest.mark.asyncio
    async def test_initialize_oauth_required(self):
        """Test initialization when OAuth is required."""
        mock_response = {
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "oauth": {
                        "supported": True,
                        "required": True,
                        "flows": ["authorization_code"],
                        "authorization_url": "https://example.com/oauth/authorize"
                    }
                },
                "serverInfo": {"name": "OAuth Server", "version": "1.0.0"}
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.initialize({
            "client_info": {"name": "Test Client", "version": "1.0.0"},
            "client_capabilities": {"protocol_versions": ["2025-06-18"]}
        })

        # Check that OAuth capabilities are properly stored
        assert "oauth" in self.adapter.server_capabilities
        assert self.adapter.server_capabilities["oauth"]["supported"] is True
        assert "authorization_url" in self.adapter.server_capabilities["oauth"]

    @pytest.mark.asyncio
    async def test_initialize_error(self):
        """Test initialization failure."""
        self.mock_transport.send_request.return_value = {
            "error": {"code": -32603, "message": "Initialization failed"}
        }

        with pytest.raises(ConnectionError, match="Initialize failed"):
            await self.adapter.initialize({})

    @pytest.mark.asyncio
    async def test_get_tools_list_structured_format(self):
        """Test tools list with 2025-06-18 structured format."""
        self.adapter.initialized = True
        mock_response = {
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "title": "Echo Tool",
                        "description": "Echoes input message",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            },
                            "required": ["message"]
                        },
                        "outputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "array"},
                                "isError": {"type": "boolean"},
                                "structuredContent": {"type": "object"}
                            }
                        }
                    }
                ]
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        tools = await self.adapter.get_tools_list()

        assert len(tools) == 1
        tool = tools[0]
        assert tool["name"] == "echo"
        assert tool["title"] == "Echo Tool"
        assert "inputSchema" in tool
        assert "outputSchema" in tool
        assert tool["outputSchema"]["properties"]["structuredContent"]

    @pytest.mark.asyncio
    async def test_call_tool_structured_output(self):
        """Test tool call with structured output format."""
        self.adapter.initialized = True
        mock_response = {
            "result": {
                "content": [
                    {"type": "text", "text": "Hello, World!"}
                ],
                "isError": False,
                "structuredContent": {
                    "type": "echo_response",
                    "original_message": "Hello, World!",
                    "timestamp": "2025-06-18T10:00:00Z"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.call_tool("echo", {"message": "Hello, World!"})

        assert "content" in result
        assert "isError" in result
        assert "structuredContent" in result
        assert result["isError"] is False
        assert result["structuredContent"]["type"] == "echo_response"

    @pytest.mark.asyncio
    async def test_call_tool_error_structured(self):
        """Test tool call with structured error response."""
        self.adapter.initialized = True
        mock_response = {
            "result": {
                "content": [
                    {"type": "text", "text": "Tool execution failed"}
                ],
                "isError": True,
                "structuredContent": {
                    "type": "error",
                    "error_code": "INVALID_INPUT",
                    "details": "Missing required parameter"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.call_tool("broken_tool", {})

        assert result["isError"] is True
        assert result["structuredContent"]["type"] == "error"
        assert result["structuredContent"]["error_code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_batch_request_rejection(self):
        """Test that batch requests are properly rejected in 2025-06-18."""
        self.adapter.initialized = True

        with pytest.raises(ConnectionError, match="JSON-RPC batching is not supported in protocol version 2025-06-18"):
            await self.adapter.send_batch_request([
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
            ])

    @pytest.mark.asyncio
    async def test_elicitation_support(self):
        """Test elicitation support functionality."""
        self.adapter.initialized = True
        self.adapter.server_capabilities = {
            "elicitation": {"supported": True}
        }

        # Test that elicitation requests dict exists
        assert hasattr(self.adapter, 'elicitation_requests')
        assert isinstance(self.adapter.elicitation_requests, dict)

        # Test creating an elicitation request
        mock_response = {
            "result": {
                "action": "accept",
                "elicitation": {
                    "type": "confirmation",
                    "message": "Do you want to proceed with this action?",
                    "options": ["yes", "no"],
                    "default": "no"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.create_elicitation_request(
            {"type": "string"}, 
            "Do you want to proceed?"
        )

        assert "action" in result
        assert result["action"] == "accept"

    @pytest.mark.asyncio
    async def test_oauth_token_handling(self):
        """Test OAuth token handling in requests."""
        self.adapter.initialized = True
        self.adapter.oauth_token = "bearer_token_123"

        # Mock successful tools list response
        mock_response = {
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "title": "Echo Tool",
                        "description": "Echoes input message",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"]
                        }
                    }
                ]
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        # Mock a request that should include OAuth token
        await self.adapter.get_tools_list()

        # The adapter should have set OAuth context
        assert hasattr(self.adapter, 'oauth_token')
        assert self.adapter.oauth_token == "bearer_token_123"

    @pytest.mark.asyncio
    async def test_enhanced_error_handling(self):
        """Test enhanced error handling for 2025-06-18."""
        self.adapter.initialized = True
        
        # Test structured error response
        mock_response = {
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {
                    "type": "validation_error",
                    "field": "arguments.message",
                    "expected": "string",
                    "received": "null"
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            await self.adapter.call_tool("echo", {})

        error_msg = str(exc_info.value)
        assert "Invalid params" in error_msg

    def test_protocol_version_property(self):
        """Test protocol version property."""
        # Test that adapter has correct version
        assert self.adapter.version == "2025-06-18"
        assert hasattr(self.adapter, 'protocol_version_header')
        assert self.adapter.protocol_version_header == "2025-06-18"

    @pytest.mark.asyncio
    async def test_structured_tool_call(self):
        """Test structured tool call method."""
        self.adapter.initialized = True
        
        mock_response = {
            "result": {
                "content": [{"type": "text", "text": "Hello"}],
                "isError": False,
                "structuredContent": {"type": "response"}
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.call_tool_with_structured_output("echo", {"message": "test"})

        assert "content" in result
        assert "isError" in result
        assert "structuredContent" in result

    @pytest.mark.asyncio 
    async def test_enhanced_ping(self):
        """Test enhanced ping with validation."""
        self.adapter.initialized = True
        
        mock_response = {
            "result": {}
        }
        self.mock_transport.send_request.return_value = mock_response

        result = await self.adapter.ping_with_enhanced_validation()
        
        # The method returns the response result directly
        assert result == {}

    @pytest.mark.asyncio
    async def test_resource_with_metadata(self):
        """Test getting resource with metadata."""
        self.adapter.initialized = True
        
        mock_response = {
            "result": {
                "contents": [{"type": "text", "text": "file content", "uri": "file://test.txt"}],
                "metadata": {
                    "created": "2025-06-18T10:00:00Z",
                    "modified": "2025-06-18T10:30:00Z",
                    "size": 1024
                }
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        resource = await self.adapter.get_resource_with_metadata("file://test.txt")

        assert "contents" in resource
        assert "metadata" in resource
        assert "created" in resource["metadata"]

    @pytest.mark.asyncio
    async def test_tools_with_output_schema(self):
        """Test getting tools list with output schema."""
        self.adapter.initialized = True
        
        mock_response = {
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "title": "Echo Tool",
                        "description": "Echoes input",
                        "inputSchema": {"type": "object"},
                        "outputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "array"},
                                "isError": {"type": "boolean"},
                                "structuredContent": {"type": "object"}
                            }
                        }
                    }
                ]
            }
        }
        self.mock_transport.send_request.return_value = mock_response

        tools = await self.adapter.list_tools_with_output_schema()

        assert len(tools) == 1
        tool = tools[0]
        assert "outputSchema" in tool
        assert "structuredContent" in tool["outputSchema"]["properties"] 