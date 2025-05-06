"""Unit tests for the HTTP server notification system."""

import pytest
import json
import time
import threading
import asyncio
import requests
from unittest.mock import MagicMock, patch
from minimal_http_server.minimal_http_server import (
    MCPHTTPRequestHandler,
    server_state,
    broadcast_sse_message,
    send_sse_message_to_session,
    cleanup_stale_connections,
    count_session_connections,
    RATE_LIMIT_WINDOW,
    MAX_CONNECTIONS_PER_SESSION,
    CONNECTION_TIMEOUT
)

class TestNotificationSystem:
    """Tests for the notification system."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock SSE connection."""
        connection = MagicMock()
        wfile = MagicMock()
        rfile = MagicMock()
        return {
            "id": "test-conn-1",
            "session_id": "test-session-1",
            "wfile": wfile,
            "rfile": rfile,
            "connection": connection,
            "last_active": time.time()
        }
    
    @pytest.fixture
    def setup_server_state(self):
        """Set up clean server state before each test."""
        server_state["initialized"] = True
        server_state["sessions"] = {
            "test-session": {"last_poll_time": 0}
        }
        server_state["sse_connections"] = []
        server_state["notifications"] = {}
        yield
        # Clean up after test
        server_state["initialized"] = False
        server_state["sessions"] = {}
        server_state["sse_connections"] = []
        server_state["notifications"] = {}
    
    def test_connection_limit(self, setup_server_state, mock_connection):
        """Test maximum connections per session limit."""
        # Add max number of connections
        for i in range(MAX_CONNECTIONS_PER_SESSION):
            conn = mock_connection.copy()
            conn["id"] = f"test-conn-{i}"
            server_state["sse_connections"].append(conn)
        
        # Verify connection count
        assert count_session_connections("test-session") == MAX_CONNECTIONS_PER_SESSION
        
        # Try to add one more connection
        new_conn = mock_connection.copy()
        new_conn["id"] = "test-conn-extra"
        server_state["sse_connections"].append(new_conn)
        
        # Should still have max connections
        assert count_session_connections("test-session") == MAX_CONNECTIONS_PER_SESSION
    
    def test_stale_connection_cleanup(self, setup_server_state, mock_connection):
        """Test cleanup of stale connections."""
        # Add a stale connection
        stale_conn = mock_connection.copy()
        stale_conn["last_active"] = time.time() - (CONNECTION_TIMEOUT + 10)
        server_state["sse_connections"].append(stale_conn)
        
        # Add a fresh connection
        fresh_conn = mock_connection.copy()
        fresh_conn["id"] = "test-conn-fresh"
        server_state["sse_connections"].append(fresh_conn)
        
        # Run cleanup
        cleanup_stale_connections()
        
        # Verify only fresh connection remains
        assert len(server_state["sse_connections"]) == 1
        assert server_state["sse_connections"][0]["id"] == "test-conn-fresh"
    
    def test_rate_limiting(self, setup_server_state):
        """Test notification polling rate limiting."""
        session = server_state["sessions"]["test-session"]
        
        # First poll should work
        session["last_poll_time"] = time.time() - (RATE_LIMIT_WINDOW + 1)
        handler = MCPHTTPRequestHandler(None, None, None)
        result = handler._handle_notifications_poll({})
        assert "notifications" in result
        
        # Immediate second poll should fail
        session["last_poll_time"] = time.time()
        with pytest.raises(Exception) as excinfo:
            handler._handle_notifications_poll({})
        assert "Rate limit exceeded" in str(excinfo.value)
    
    def test_broadcast_message(self, setup_server_state, mock_connection):
        """Test broadcasting messages to all connections."""
        # Add two connections
        conn1 = mock_connection.copy()
        conn2 = mock_connection.copy()
        conn2["id"] = "test-conn-2"
        server_state["sse_connections"].extend([conn1, conn2])
        
        # Broadcast a message
        test_message = {"type": "test", "data": "Hello"}
        broadcast_sse_message(test_message)
        
        # Verify both connections received the message
        expected_data = f"event: message\ndata: {json.dumps(test_message)}\n\n"
        conn1["wfile"].write.assert_called_once_with(expected_data.encode('utf-8'))
        conn2["wfile"].write.assert_called_once_with(expected_data.encode('utf-8'))
    
    def test_session_message(self, setup_server_state, mock_connection):
        """Test sending messages to specific session."""
        # Add two connections for different sessions
        conn1 = mock_connection.copy()
        conn2 = mock_connection.copy()
        conn2["id"] = "test-conn-2"
        conn2["session_id"] = "other-session"
        server_state["sse_connections"].extend([conn1, conn2])
        
        # Send message to test-session
        test_message = {"type": "test", "data": "Hello"}
        send_sse_message_to_session("test-session", test_message)
        
        # Verify only test-session connection received the message
        expected_data = f"event: message\ndata: {json.dumps(test_message)}\n\n"
        conn1["wfile"].write.assert_called_once_with(expected_data.encode('utf-8'))
        conn2["wfile"].write.assert_not_called()
    
    def test_connection_error_handling(self, setup_server_state, mock_connection):
        """Test handling of connection errors during message send."""
        # Add a connection that will raise an error
        conn = mock_connection.copy()
        conn["wfile"].write.side_effect = BrokenPipeError("Connection lost")
        server_state["sse_connections"].append(conn)
        
        # Try to send a message
        test_message = {"type": "test", "data": "Hello"}
        broadcast_sse_message(test_message)
        
        # Verify connection was removed
        assert len(server_state["sse_connections"]) == 0
        conn["connection"].close.assert_called_once()

    def test_cleanup_stale_connections(self, mock_connection):
        """Test cleanup of stale connections."""
        # Add a stale connection
        mock_connection["last_active"] = time.time() - (CONNECTION_TIMEOUT + 10)
        server_state["sse_connections"] = [mock_connection]
        
        # Run cleanup
        cleanup_stale_connections()
        
        # Verify connection was removed
        assert len(server_state["sse_connections"]) == 0
        mock_connection["connection"].close.assert_called_once()

    def test_count_session_connections(self, mock_connection):
        """Test counting connections for a session."""
        # Add multiple connections for same session
        conn1 = mock_connection.copy()
        conn2 = mock_connection.copy()
        conn2["id"] = "test-conn-2"
        server_state["sse_connections"] = [conn1, conn2]
        
        # Count connections
        count = count_session_connections("test-session-1")
        assert count == 2

    def test_broadcast_sse_message(self, mock_connection):
        """Test broadcasting message to all connections."""
        # Add connection to server state
        server_state["sse_connections"] = [mock_connection]
        
        # Broadcast message
        message = {"type": "test", "data": "test message"}
        broadcast_sse_message(message, "test-event")
        
        # Verify message was sent
        expected_data = f"event: test-event\ndata: {json.dumps(message)}\n\n"
        mock_connection["wfile"].write.assert_called_once_with(expected_data.encode('utf-8'))
        mock_connection["wfile"].flush.assert_called_once()

    def test_send_sse_message_to_session(self, mock_connection):
        """Test sending message to specific session."""
        # Add connections for different sessions
        conn1 = mock_connection.copy()
        conn2 = mock_connection.copy()
        conn2["id"] = "test-conn-2"
        conn2["session_id"] = "test-session-2"
        server_state["sse_connections"] = [conn1, conn2]
        
        # Send message to specific session
        message = {"type": "test", "data": "test message"}
        send_sse_message_to_session("test-session-1", message, "test-event")
        
        # Verify message was sent only to correct session
        expected_data = f"event: test-event\ndata: {json.dumps(message)}\n\n"
        conn1["wfile"].write.assert_called_once_with(expected_data.encode('utf-8'))
        conn1["wfile"].flush.assert_called_once()
        conn2["wfile"].write.assert_not_called()
        conn2["wfile"].flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_high_concurrency_notifications(self):
        """Test sending notifications under high concurrency."""
        # Create multiple mock connections
        connections = []
        for i in range(10):
            connection = MagicMock()
            wfile = MagicMock()
            rfile = MagicMock()
            connections.append({
                "id": f"test-conn-{i}",
                "session_id": f"test-session-{i % 3}",  # Distribute across 3 sessions
                "wfile": wfile,
                "rfile": rfile,
                "connection": connection,
                "last_active": time.time()
            })
        server_state["sse_connections"] = connections

        # Create tasks to send notifications concurrently
        async def send_notifications():
            for i in range(50):  # Send 50 notifications
                message = {"type": "test", "data": f"message-{i}"}
                if i % 2 == 0:
                    # Broadcast to all
                    broadcast_sse_message(message, "test-event")
                else:
                    # Send to specific session
                    send_sse_message_to_session(f"test-session-{i % 3}", message, "test-event")
                await asyncio.sleep(0.01)  # Small delay to simulate real traffic

        # Run multiple notification senders concurrently
        tasks = [send_notifications() for _ in range(3)]
        await asyncio.gather(*tasks)

        # Verify connections are still active
        cleanup_stale_connections()
        assert len(server_state["sse_connections"]) == 10

        # Verify each connection received messages
        for conn in connections:
            assert conn["wfile"].write.call_count > 0
            assert conn["wfile"].flush.call_count > 0

    def test_handle_connection_errors(self, mock_connection):
        """Test handling of connection errors during message sending."""
        # Setup connection to raise error
        mock_connection["wfile"].write.side_effect = ConnectionResetError("Connection reset")
        server_state["sse_connections"] = [mock_connection]
        
        # Try to send message
        message = {"type": "test", "data": "test message"}
        broadcast_sse_message(message)
        
        # Verify connection was removed
        assert len(server_state["sse_connections"]) == 0
        mock_connection["connection"].close.assert_called_once()

    def test_rate_limiting(self, mock_connection):
        """Test rate limiting of notifications."""
        server_state["sse_connections"] = [mock_connection]
        
        # Send messages rapidly
        start_time = time.time()
        for i in range(5):
            message = {"type": "test", "data": f"message-{i}"}
            broadcast_sse_message(message)
        end_time = time.time()
        
        # Verify timing respects rate limit
        assert end_time - start_time >= RATE_LIMIT_WINDOW

    def test_max_connections_per_session(self, mock_connection):
        """Test maximum connections per session limit."""
        # Add maximum number of connections for a session
        connections = []
        for i in range(MAX_CONNECTIONS_PER_SESSION):
            conn = mock_connection.copy()
            conn["id"] = f"test-conn-{i}"
            connections.append(conn)
        server_state["sse_connections"] = connections
        
        # Verify connection count
        count = count_session_connections("test-session-1")
        assert count == MAX_CONNECTIONS_PER_SESSION 