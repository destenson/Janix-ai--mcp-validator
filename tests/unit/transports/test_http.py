"""
Unit tests for the HTTP transport adapter.
"""

import pytest
import json
import subprocess
import requests
from unittest.mock import MagicMock, patch, call, ANY
from mcp_testing.transports.http import HttpTransportAdapter


class TestHttpTransportAdapter:
    """Tests for the HttpTransportAdapter class."""

    def test_init_with_server_command(self):
        """Test initialization with server command."""
        adapter = HttpTransportAdapter(server_command="python server.py")
        
        assert adapter.server_command == "python server.py"
        assert adapter.server_url is None
        assert adapter.headers == {"Content-Type": "application/json"}
        assert adapter.timeout == 30.0
        assert adapter.use_sse is False
        assert adapter.is_started is False
        assert adapter.process is None
        assert adapter.sse_client is None

    def test_init_with_server_url(self):
        """Test initialization with server URL."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        
        assert adapter.server_command is None
        assert adapter.server_url == "http://localhost:8080"
        assert adapter.headers == {"Content-Type": "application/json"}
        assert adapter.timeout == 30.0
        assert adapter.use_sse is False
        assert adapter.is_started is False
        assert adapter.process is None
        assert adapter.sse_client is None

    def test_init_with_custom_headers(self):
        """Test initialization with custom headers."""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        adapter = HttpTransportAdapter(server_url="http://localhost:8080", headers=headers)
        
        assert adapter.headers == headers

    def test_init_with_no_server_info(self):
        """Test initialization with neither server command nor URL."""
        with pytest.raises(ValueError) as excinfo:
            HttpTransportAdapter()
        
        assert "Either server_command or server_url must be provided" in str(excinfo.value)

    @patch('subprocess.Popen')
    @patch('time.sleep')
    @patch('requests.Session.options')
    def test_start_with_server_command(self, mock_options, mock_sleep, mock_popen):
        """Test starting with server command."""
        # Setup mocks
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_options.return_value = mock_response
        
        # Create adapter and start it
        adapter = HttpTransportAdapter(server_command="python server.py")
        result = adapter.start()
        
        # Verify
        assert result is True
        assert adapter.is_started is True
        assert adapter.server_url == "http://localhost:8000"  # Default URL
        
        mock_popen.assert_called_once_with(
            ["python", "server.py"],
            stdin=ANY,
            stdout=ANY,
            stderr=ANY,
            text=False
        )
        mock_sleep.assert_called_once()
        mock_options.assert_called_once()

    @patch('requests.Session.options')
    def test_start_with_server_url(self, mock_options):
        """Test starting with server URL."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_options.return_value = mock_response
        
        # Create adapter and start it
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        result = adapter.start()
        
        # Verify
        assert result is True
        assert adapter.is_started is True
        
        mock_options.assert_called_once_with("http://localhost:8080", timeout=30.0)

    @patch('requests.Session.options')
    def test_start_connection_error(self, mock_options):
        """Test starting with connection error."""
        # Setup mock to raise exception
        mock_options.side_effect = Exception("Connection failed")
        
        # Create adapter and try to start it
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        result = adapter.start()
        
        # Verify
        assert result is False
        assert adapter.is_started is False

    @patch('subprocess.Popen')
    @patch('time.sleep')
    @patch('requests.Session.options')
    def test_start_with_sse(self, mock_options, mock_sleep, mock_popen):
        """Test starting with SSE enabled."""
        # Setup mocks
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_options.return_value = mock_response
        
        # Create adapter with SSE and start it
        adapter = HttpTransportAdapter(
            server_url="http://localhost:8080",
            use_sse=True
        )
        
        # Patch the SSE listener method
        with patch.object(adapter, '_start_sse_listener') as mock_sse_listener:
            result = adapter.start()
            
            # Verify
            assert result is True
            assert adapter.is_started is True
            
            # Check that SSE listener was started
            mock_sse_listener.assert_called_once_with(
                "http://localhost:8080/notifications",
                {"Content-Type": "application/json", "Accept": "text/event-stream"}
            )

    def test_stop_not_started(self):
        """Test stopping an adapter that was not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        
        result = adapter.stop()
        
        assert result is True
        assert adapter.is_started is False

    @patch('requests.Session.close')
    def test_stop_with_server_url(self, mock_close):
        """Test stopping an adapter with server URL."""
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Stop the adapter
        result = adapter.stop()
        
        # Verify
        assert result is True
        assert adapter.is_started is False
        mock_close.assert_called_once()

    @patch('requests.Session.close')
    def test_stop_with_server_command(self, mock_close):
        """Test stopping an adapter with server command."""
        # Create adapter with mock process and mark as started
        adapter = HttpTransportAdapter(server_command="python server.py")
        adapter.is_started = True
        adapter.process = MagicMock()
        process = adapter.process  # Save reference to process before it gets nulled

        # Stop the adapter
        result = adapter.stop()

        # Verify
        assert result is True
        assert adapter.is_started is False
        assert adapter.process is None
        mock_close.assert_called_once()
        process.terminate.assert_called_once()  # Use saved reference

    @patch('requests.Session.close')
    def test_stop_with_server_process_timeout(self, mock_close):
        """Test stopping an adapter when process termination times out."""
        # Create adapter with mock process that times out
        adapter = HttpTransportAdapter(server_command="python server.py")
        adapter.is_started = True
        adapter.process = MagicMock()
        adapter.process.wait.side_effect = subprocess.TimeoutExpired(cmd="python server.py", timeout=5)
        process = adapter.process  # Save reference to process before it gets nulled

        # Stop the adapter
        result = adapter.stop()

        # Verify
        assert result is True
        assert adapter.is_started is False
        assert adapter.process is None
        mock_close.assert_called_once()
        process.terminate.assert_called_once()  # Use saved reference

    def test_send_request_not_started(self):
        """Test sending request when adapter is not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_request({"jsonrpc": "2.0", "method": "test", "id": 1})
        
        assert "Transport not started" in str(excinfo.value)

    @patch('requests.Session.post')
    def test_send_request_success(self, mock_post):
        """Test sending request successfully."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": "success", "id": 1}
        mock_post.return_value = mock_response
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send request
        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        response = adapter.send_request(request)
        
        # Verify
        assert response == {"jsonrpc": "2.0", "result": "success", "id": 1}
        mock_post.assert_called_once_with(
            "http://localhost:8080",
            data=json.dumps(request),
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()

    @patch('requests.Session.post')
    def test_send_request_http_error(self, mock_post):
        """Test sending request with HTTP error."""
        # Setup mock to raise exception
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")
        mock_post.return_value = mock_response
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send request and expect error
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_request({"jsonrpc": "2.0", "method": "test", "id": 1})
        
        assert "HTTP request failed" in str(excinfo.value)

    @patch('requests.Session.post')
    def test_send_request_json_error(self, mock_post):
        """Test sending request with JSON decoding error."""
        # Setup mock to return invalid JSON
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send request and expect error
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_request({"jsonrpc": "2.0", "method": "test", "id": 1})
        
        assert "Invalid JSON response" in str(excinfo.value)

    def test_send_notification_not_started(self):
        """Test sending notification when adapter is not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_notification({"jsonrpc": "2.0", "method": "test"})
        
        assert "Transport not started" in str(excinfo.value)

    @patch('requests.Session.post')
    def test_send_notification_success(self, mock_post):
        """Test sending notification successfully."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send notification
        notification = {"jsonrpc": "2.0", "method": "test"}
        adapter.send_notification(notification)
        
        # Verify
        mock_post.assert_called_once_with(
            "http://localhost:8080",
            data=json.dumps(notification),
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('requests.Session.post')
    def test_send_notification_error(self, mock_post):
        """Test sending notification with error."""
        # Setup mock to raise exception
        mock_post.side_effect = Exception("Request failed")
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send notification and expect error
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_notification({"jsonrpc": "2.0", "method": "test"})
        
        assert "Failed to send notification" in str(excinfo.value)

    def test_send_batch_not_started(self):
        """Test sending batch when adapter is not started."""
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        
        with pytest.raises(ConnectionError) as excinfo:
            adapter.send_batch([
                {"jsonrpc": "2.0", "method": "test1", "id": 1},
                {"jsonrpc": "2.0", "method": "test2", "id": 2}
            ])
        
        assert "Transport not started" in str(excinfo.value)

    @patch('requests.Session.post')
    def test_send_batch_success(self, mock_post):
        """Test sending batch successfully."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"jsonrpc": "2.0", "result": "success1", "id": 1},
            {"jsonrpc": "2.0", "result": "success2", "id": 2}
        ]
        mock_post.return_value = mock_response
        
        # Create adapter and mark as started
        adapter = HttpTransportAdapter(server_url="http://localhost:8080")
        adapter.is_started = True
        
        # Send batch
        batch = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2}
        ]
        responses = adapter.send_batch(batch)
        
        # Verify
        assert responses == [
            {"jsonrpc": "2.0", "result": "success1", "id": 1},
            {"jsonrpc": "2.0", "result": "success2", "id": 2}
        ]
        mock_post.assert_called_once_with(
            "http://localhost:8080",
            data=json.dumps(batch),
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once() 