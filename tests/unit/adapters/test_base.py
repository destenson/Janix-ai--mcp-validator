"""
Unit tests for the base server adapter.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from mcp_testing.adapters.base import MCPServerAdapter


class TestMCPServerAdapter:
    """Tests for the MCPServerAdapter class."""

    def test_init(self):
        """Test initialization of the base server adapter."""
        # Create a concrete subclass for testing
        class ConcreteAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_request(self, method, params=None):
                return {"result": "success"}
                
            async def send_notification(self, method, params=None):
                pass
        
        # Create adapter instance
        adapter = ConcreteAdapter("1.0", debug=True)
        
        # Test initialization
        assert adapter.protocol_version == "1.0"
        assert adapter.debug is True
        assert adapter.server_info is None
        assert adapter._request_id == 0

    @pytest.mark.asyncio
    async def test_abstract_methods(self):
        """Test that abstract methods must be implemented."""
        # Verify that MCPServerAdapter can't be instantiated directly
        with pytest.raises(TypeError):
            MCPServerAdapter("1.0")
            
        # Verify that concrete subclasses must implement all abstract methods
        class IncompleteAdapter(MCPServerAdapter):
            # Missing some abstract methods
            async def start(self):
                return True
        
        with pytest.raises(TypeError):
            IncompleteAdapter("1.0")

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "name": "Test Server",
                    "version": "1.0",
                    "capabilities": {}
                }
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test initialize
        result = await adapter.initialize()
        
        # Verify
        adapter.send_request.assert_called_once_with("initialize", {
            "protocolVersion": "1.0",
            "options": {}
        })
        assert adapter.server_info == {
            "name": "Test Server",
            "version": "1.0",
            "capabilities": {}
        }
        assert result["result"] == adapter.server_info

    @pytest.mark.asyncio
    async def test_initialize_error(self):
        """Test initialization with error response."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method to return an error
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                }
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test initialize with error
        with pytest.raises(RuntimeError) as excinfo:
            await adapter.initialize()
        
        # Verify
        adapter.send_request.assert_called_once()
        assert "Failed to initialize server" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_invalid_initialize_response(self):
        """Test initialization with invalid response."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method to return invalid response
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1
                # Missing result field
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test initialize with invalid response
        with pytest.raises(RuntimeError) as excinfo:
            await adapter.initialize()
        
        # Verify
        adapter.send_request.assert_called_once()
        assert "Invalid initialize response" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutdown method."""
        # Create a concrete subclass with mocked methods
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            # Mock these methods
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {}
            })
            send_notification = AsyncMock()
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test shutdown
        result = await adapter.shutdown()
        
        # Verify
        adapter.send_request.assert_called_once_with("shutdown", {})
        adapter.send_notification.assert_called_once_with("exit")
        assert result == {"jsonrpc": "2.0", "id": 1, "result": {}}

    @pytest.mark.asyncio
    async def test_shutdown_error(self):
        """Test shutdown with error."""
        # Create a concrete subclass with mocked methods
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            # Mock send_request to raise an exception
            send_request = AsyncMock(side_effect=Exception("Connection lost"))
            send_notification = AsyncMock()
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test shutdown with error
        result = await adapter.shutdown()
        
        # Verify
        adapter.send_request.assert_called_once()
        adapter.send_notification.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """Test list_tools method."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": [
                    {"name": "tool1", "description": "Tool 1"},
                    {"name": "tool2", "description": "Tool 2"}
                ]
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test list_tools
        tools = await adapter.list_tools()
        
        # Verify
        adapter.send_request.assert_called_once_with("listTools", {})
        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[1]["name"] == "tool2"

    @pytest.mark.asyncio
    async def test_list_tools_error(self):
        """Test list_tools with error response."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method to return an error
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                }
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test list_tools with error
        with pytest.raises(RuntimeError) as excinfo:
            await adapter.list_tools()
        
        # Verify
        adapter.send_request.assert_called_once()
        assert "Failed to list tools" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test call_tool method."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"output": "Tool result"}
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test call_tool
        result = await adapter.call_tool("test_tool", {"param1": "value1"})
        
        # Verify
        adapter.send_request.assert_called_once_with("callTool", {
            "name": "test_tool",
            "params": {"param1": "value1"}
        })
        assert result["result"]["output"] == "Tool result"

    @pytest.mark.asyncio
    async def test_call_tool_error(self):
        """Test call_tool with error response."""
        # Create a concrete subclass with mocked send_request
        class TestAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_notification(self, method, params=None):
                pass
            
            # Mock the send_request method to return an error
            send_request = AsyncMock(return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32602,
                    "message": "Invalid params"
                }
            })
        
        # Create the adapter
        adapter = TestAdapter("1.0")
        
        # Test call_tool with error
        result = await adapter.call_tool("test_tool", {"param1": "value1"})
        
        # Verify
        adapter.send_request.assert_called_once()
        assert "error" in result
        assert result["error"]["message"] == "Invalid params"

    def test_get_next_request_id(self):
        """Test _get_next_request_id method."""
        # Create a concrete subclass for testing
        class ConcreteAdapter(MCPServerAdapter):
            async def start(self):
                return True
                
            async def stop(self):
                return True
                
            async def send_request(self, method, params=None):
                return {"result": "success"}
                
            async def send_notification(self, method, params=None):
                pass
        
        # Create adapter instance
        adapter = ConcreteAdapter("1.0")
        
        # Test ID generation
        id1 = adapter._get_next_request_id()
        id2 = adapter._get_next_request_id()
        id3 = adapter._get_next_request_id()
        
        # Verify each ID is unique and sequential
        assert id1 == 1
        assert id2 == 2
        assert id3 == 3 