"""
Unit tests for the transport base module.
"""

import pytest
from unittest.mock import Mock, patch
from mcp_testing.transports.base import MCPTransportAdapter
from typing import Dict, Any, List


class TestMCPTransportAdapter:
    """Tests for the MCPTransportAdapter class."""

    def test_abstract_methods(self):
        """Test that MCPTransportAdapter cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError):
            transport = MCPTransportAdapter()

    def test_concrete_implementation(self):
        """Test that a concrete subclass implementation works correctly."""
        # Create a concrete subclass that implements all abstract methods
        class ConcreteTransport(MCPTransportAdapter):
            def start(self) -> bool:
                return True
                
            def stop(self) -> bool:
                return True
                
            def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
                return {"jsonrpc": "2.0", "result": "success", "id": 1}
                
            def send_notification(self, notification: Dict[str, Any]) -> None:
                pass
                
            def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return [{"jsonrpc": "2.0", "result": "success", "id": i} for i in range(len(requests))]
                
        # Now the concrete class should be instantiable
        transport = ConcreteTransport()
        assert transport.debug is False
        assert transport.is_started is False
        
        assert transport.start() is True
        assert transport.stop() is True
        
        # Test sending a request
        response = transport.send_request({"jsonrpc": "2.0", "method": "test", "id": 1})
        assert response == {"jsonrpc": "2.0", "result": "success", "id": 1}
        
        # Test sending a notification
        transport.send_notification({"jsonrpc": "2.0", "method": "notify"})
        
        # Test sending a batch
        requests = [
            {"jsonrpc": "2.0", "method": "test1", "id": 0},
            {"jsonrpc": "2.0", "method": "test2", "id": 1}
        ]
        responses = transport.send_batch(requests)
        assert len(responses) == 2
        assert responses[0] == {"jsonrpc": "2.0", "result": "success", "id": 0}
        assert responses[1] == {"jsonrpc": "2.0", "result": "success", "id": 1}

    def test_init_with_debug(self):
        """Test initialization with debug flag."""
        # Create a concrete implementation to test the constructor
        class DebugTransport(MCPTransportAdapter):
            def start(self) -> bool:
                return True
                
            def stop(self) -> bool:
                return True
                
            def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
                return {}
                
            def send_notification(self, notification: Dict[str, Any]) -> None:
                pass
                
            def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return []
        
        # Test with debug=True
        transport = DebugTransport(debug=True)
        assert transport.debug is True
        assert transport.is_started is False
        
        # Test with debug=False (default)
        transport = DebugTransport()
        assert transport.debug is False
        assert transport.is_started is False

    def test_basic_workflow(self):
        """Test the basic workflow of a transport adapter."""
        # Create a mock implementation that tracks method calls
        mock_start = Mock(return_value=True)
        mock_stop = Mock(return_value=True)
        mock_send_request = Mock(return_value={"jsonrpc": "2.0", "result": "success", "id": 1})
        mock_send_notification = Mock()
        mock_send_batch = Mock(return_value=[{"jsonrpc": "2.0", "result": "success", "id": 1}])
        
        class TrackingTransport(MCPTransportAdapter):
            def start(self) -> bool:
                return mock_start()
                
            def stop(self) -> bool:
                return mock_stop()
                
            def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
                return mock_send_request(request)
                
            def send_notification(self, notification: Dict[str, Any]) -> None:
                mock_send_notification(notification)
                
            def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return mock_send_batch(requests)
        
        # Test the expected workflow
        transport = TrackingTransport()
        
        # Start the transport
        result = transport.start()
        assert result is True
        mock_start.assert_called_once()
        
        # Send a request
        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        response = transport.send_request(request)
        assert response == {"jsonrpc": "2.0", "result": "success", "id": 1}
        mock_send_request.assert_called_once_with(request)
        
        # Send a notification
        notification = {"jsonrpc": "2.0", "method": "notify"}
        transport.send_notification(notification)
        mock_send_notification.assert_called_once_with(notification)
        
        # Send a batch
        requests = [{"jsonrpc": "2.0", "method": "test", "id": 1}]
        responses = transport.send_batch(requests)
        assert responses == [{"jsonrpc": "2.0", "result": "success", "id": 1}]
        mock_send_batch.assert_called_once_with(requests)
        
        # Stop the transport
        result = transport.stop()
        assert result is True
        mock_stop.assert_called_once() 