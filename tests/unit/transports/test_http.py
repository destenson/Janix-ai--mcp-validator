#!/usr/bin/env python3
"""
Unit tests for HTTP Transport Adapter.

Tests the HTTP transport implementation including OAuth 2.1 support,
session management, and 2025-06-18 protocol features.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
import requests
import logging

from mcp_testing.transports.http import HttpTransportAdapter, TransportError


class TestHttpTransportAdapter:
    """Test suite for HTTP Transport Adapter."""

    def setup_method(self):
        """Set up test fixtures."""
        # Note: Most tests will override this with their own adapter configuration
        pass

    def test_init_with_server_url(self):
        """Test initialization with server URL."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        assert adapter.server_url == "http://localhost:8088"
        assert adapter.server_command is None
        assert adapter.protocol_version is None
        assert adapter.bearer_token is None

    def test_init_with_server_command(self):
        """Test initialization with server command."""
        adapter = HttpTransportAdapter(server_command="python server.py")
        assert adapter.server_command == "python server.py"
        assert adapter.server_url is None

    def test_init_with_oauth_token(self):
        """Test initialization with OAuth token."""
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8088",
            protocol_version="2025-06-18",
            bearer_token="test_token_123"
        )
        assert adapter.bearer_token == "test_token_123"
        assert "Authorization" in adapter.headers
        assert adapter.headers["Authorization"] == "Bearer test_token_123"

    def test_init_with_protocol_version_2025_06_18(self):
        """Test initialization with 2025-06-18 protocol version."""
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8088",
            protocol_version="2025-06-18"
        )
        assert adapter.protocol_version == "2025-06-18"
        assert "MCP-Protocol-Version" in adapter.headers
        assert adapter.headers["MCP-Protocol-Version"] == "2025-06-18"

    def test_init_no_server_info(self):
        """Test initialization without server command or URL."""
        with pytest.raises(ValueError, match="Either server_command or server_url must be provided"):
            HttpTransportAdapter()

    @patch('mcp_testing.transports.http.subprocess.Popen')
    @patch('mcp_testing.transports.http.time.sleep')
    def test_start_with_server_command(self, mock_sleep, mock_popen):
        """Test starting with server command."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        adapter = HttpTransportAdapter(server_command="python server.py")
        
        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "connection-test",
                "result": {"protocolVersion": "2024-11-05"}
            }
            mock_post.return_value = mock_response
            
            with patch.object(adapter, 'send_notification'):
                result = adapter.start()

        assert result is True
        assert adapter.is_started
        assert adapter.process == mock_process
        mock_popen.assert_called_once()

    def test_start_with_server_url(self):
        """Test starting with server URL."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "connection-test",
                "result": {"protocolVersion": "2024-11-05"}
            }
            mock_post.return_value = mock_response
            
            with patch.object(adapter, 'send_notification'):
                result = adapter.start()

        assert result is True
        assert adapter.is_started
        assert adapter.process is None

    def test_start_connection_error(self):
        """Test starting with connection error."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        with patch.object(adapter.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            result = adapter.start()

        assert result is False
        assert not adapter.is_started

    def test_stop_not_started(self):
        """Test stopping when not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.stop()  # Should not raise exception
        assert not adapter.is_started

    def test_stop_with_server_url(self):
        """Test stopping with server URL."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True
        
        with patch.object(adapter.session, 'close') as mock_close:
            adapter.stop()
            
        assert not adapter.is_started
        mock_close.assert_called_once()

    @patch('mcp_testing.transports.http.subprocess.Popen')
    def test_stop_with_server_command(self, mock_popen):
        """Test stopping with server command."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        adapter = HttpTransportAdapter(server_command="python server.py")
        adapter.is_started = True
        adapter.process = mock_process

        with patch.object(adapter.session, 'close'):
            adapter.stop()

        assert not adapter.is_started
        mock_process.terminate.assert_called_once()

    def test_send_request_not_started(self):
        """Test sending request when not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        with pytest.raises(TransportError, match="Transport not started"):
            adapter.send_request("ping")

    def test_send_request_success(self):
        """Test successful request sending."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True
        adapter.session_id = "test-session-123"

        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {}
            }
            mock_post.return_value = mock_response

            response = adapter.send_request("ping", request_id="test-id")

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-id"
        mock_post.assert_called_once()

    def test_send_request_with_params(self):
        """Test sending request with parameters."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True

        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {"message": "test_value"}
            }
            mock_post.return_value = mock_response

            response = adapter.send_request(
                "tools/call", 
                params={"name": "echo", "arguments": {"message": "test_value"}},
                request_id="test-id"
            )

        assert response["result"]["message"] == "test_value"

    def test_send_request_connection_error(self):
        """Test request sending with connection error."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True

        with patch.object(adapter.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

            response = adapter.send_request("ping", request_id="test-id")

        assert "error" in response
        assert response["error"]["code"] == -32003
        assert "Connection error" in response["error"]["message"]

    def test_send_request_timeout(self):
        """Test request sending with timeout."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True

        with patch.object(adapter.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

            response = adapter.send_request("ping", request_id="test-id")

        assert "error" in response
        assert response["error"]["code"] == -32004
        assert "Request timeout" in response["error"]["message"]

    def test_send_notification_success(self):
        """Test successful notification sending."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True
        adapter.session_id = "test-session-123"

        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_post.return_value = mock_response

            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            adapter.send_notification(notification)

        mock_post.assert_called_once()

    def test_send_notification_not_started(self):
        """Test sending notification when not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        with pytest.raises(ConnectionError, match="Transport not started"):
            adapter.send_notification({"jsonrpc": "2.0", "method": "test"})

    def test_send_batch_success(self):
        """Test successful batch request sending."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True
        adapter.session_id = "test-session-123"

        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"jsonrpc": "2.0", "id": 1, "result": {}},
                {"jsonrpc": "2.0", "id": 2, "result": {}}
            ]
            mock_post.return_value = mock_response

            requests = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
            ]
            responses = adapter.send_batch(requests)

        assert len(responses) == 2
        mock_post.assert_called_once()

    def test_send_batch_not_started(self):
        """Test sending batch when not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        with pytest.raises(ConnectionError, match="Transport not started"):
            adapter.send_batch([{"jsonrpc": "2.0", "method": "ping", "id": 1}])

    def test_oauth_header_handling(self):
        """Test OAuth header handling for 2025-06-18."""
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8088",
            protocol_version="2025-06-18",
            bearer_token="bearer_token_123"
        )

        assert "Authorization" in adapter.headers
        assert adapter.headers["Authorization"] == "Bearer bearer_token_123"
        assert adapter.headers["MCP-Protocol-Version"] == "2025-06-18"

    def test_session_management(self):
        """Test session management features."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        # Session ID should be generated automatically
        assert adapter.session_id is not None
        assert len(adapter.session_id) > 0
        assert "Mcp-Session-Id" in adapter.headers

    def test_protocol_version_header(self):
        """Test protocol version header for different versions."""
        # Test 2025-06-18
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8088",
            protocol_version="2025-06-18"
        )
        assert adapter.headers["MCP-Protocol-Version"] == "2025-06-18"
        
        # Test without protocol version (should not have header)
        adapter2 = HttpTransportAdapter(server_url="http://localhost:8088")
        assert "MCP-Protocol-Version" not in adapter2.headers

    def test_error_response_handling(self):
        """Test proper error response handling."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        adapter.is_started = True

        with patch.object(adapter.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test-id",
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {"field": "arguments", "expected": "object"}
                }
            }
            mock_post.return_value = mock_response

            with patch.object(adapter, '_handle_response', return_value=mock_response.json.return_value):
                response = adapter.send_request("tools/call", request_id="test-id")

        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_session_id_extraction(self):
        """Test session ID extraction from responses."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        # Mock response with session ID in header
        mock_response = MagicMock()
        mock_response.headers = {"Mcp-Session-Id": "extracted-session-123"}
        
        response_json = {"jsonrpc": "2.0", "id": 1, "result": {}}
        
        session_id = adapter._extract_session_id(mock_response, response_json)
        assert session_id == "extracted-session-123"

    def test_handle_response_with_401(self):
        """Test response handling with 401 authentication error."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {"WWW-Authenticate": "Bearer realm=\"MCP Server\""}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {
                "code": -32001,
                "message": "Authentication required"
            }
        }
        
        result = adapter._handle_response(mock_response)
        
        assert "error" in result
        assert result["error"]["code"] == -32001

    def test_get_session_id(self):
        """Test getting session ID."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8088")
        
        # Should have a session ID generated automatically
        session_id = adapter.get_session_id()
        assert session_id is not None
        assert session_id == adapter.session_id

    def test_create_session_configuration(self):
        """Test session configuration with retries."""
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8088",
            max_retries=5,
            retry_delay=2.0
        )
        
        assert adapter.max_retries == 5
        assert adapter.retry_delay == 2.0
        assert adapter.session is not None

    def test_debug_logging(self):
        """Test debug logging configuration."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            adapter = HttpTransportAdapter(
                server_url="http://localhost:8088",
                debug=True
            )
            
            mock_logger.setLevel.assert_called_with(logging.DEBUG)
            mock_logger.addHandler.assert_called_once()

    def test_url_compatibility_mode(self):
        """Test compatibility mode where server_command is treated as URL."""
        adapter = HttpTransportAdapter(server_command="http://localhost:8088")
        
        assert adapter.server_url == "http://localhost:8088"
        assert adapter.server_command is None 