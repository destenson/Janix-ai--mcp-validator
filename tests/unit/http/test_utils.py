#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the HTTP utility functions.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import socket
import time
import io
import sys

from mcp_testing.http.utils import check_server, wait_for_server


class TestHttpUtils(unittest.TestCase):
    """Test cases for HTTP utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout for testing
        self.held_output = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.held_output

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout
        sys.stdout = self.original_stdout

    @patch('socket.socket')
    def test_check_server_success(self, mock_socket):
        """Test check_server function with successful connection."""
        # Mock a successful socket connection
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Call the function with standard HTTP port
        result = check_server("http://example.com")
        
        # Verify the result is True (successful connection)
        self.assertTrue(result)
        
        # Verify socket was created and connect was called with right params
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket_instance.connect.assert_called_once_with(('example.com', 80))
        mock_socket_instance.close.assert_called_once()
        
        # Check messages
        output = self.held_output.getvalue()
        self.assertIn("Checking if server at http://example.com is accessible", output)
        self.assertIn("Server at example.com:80 is accessible", output)

    @patch('socket.socket')
    def test_check_server_with_custom_port(self, mock_socket):
        """Test check_server function with a custom port."""
        # Mock a successful socket connection
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Call the function with custom port
        result = check_server("http://example.com:8080")
        
        # Verify the result is True (successful connection)
        self.assertTrue(result)
        
        # Verify socket was created and connect was called with right params
        mock_socket_instance.connect.assert_called_once_with(('example.com', 8080))
        
        # Check messages
        output = self.held_output.getvalue()
        self.assertIn("Server at example.com:8080 is accessible", output)

    @patch('socket.socket')
    def test_check_server_with_custom_timeout(self, mock_socket):
        """Test check_server function with a custom timeout."""
        # Mock a successful socket connection
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Call the function with custom timeout
        result = check_server("http://example.com", timeout=10)
        
        # Verify the socket was configured with the custom timeout
        mock_socket_instance.settimeout.assert_called_once_with(10)

    @patch('socket.socket')
    def test_check_server_connection_failure(self, mock_socket):
        """Test check_server function when connection fails."""
        # Mock a failed socket connection
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.error("Connection refused")
        mock_socket.return_value = mock_socket_instance
        
        # Call the function
        result = check_server("http://nonexistent.example.com")
        
        # Verify the result is False (failed connection)
        self.assertFalse(result)
        
        # Verify socket was created, connect was attempted, and socket was closed
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket_instance.connect.assert_called_once()
        mock_socket_instance.close.assert_called_once()
        
        # Check error message
        output = self.held_output.getvalue()
        self.assertIn("Failed to connect to server", output)
        self.assertIn("Connection refused", output)

    @patch('mcp_testing.http.utils.check_server')
    @patch('time.sleep')
    def test_wait_for_server_immediate_success(self, mock_sleep, mock_check_server):
        """Test wait_for_server function with immediately successful connection."""
        # Mock a successful connection on first try
        mock_check_server.return_value = True
        
        # Call the function
        result = wait_for_server("http://example.com")
        
        # Verify the result is True (successful connection)
        self.assertTrue(result)
        
        # Verify check_server was called once and sleep was not called
        mock_check_server.assert_called_once_with("http://example.com", 5)
        mock_sleep.assert_not_called()

    @patch('mcp_testing.http.utils.check_server')
    @patch('time.sleep')
    def test_wait_for_server_success_after_retry(self, mock_sleep, mock_check_server):
        """Test wait_for_server function with success after a retry."""
        # Mock failed first connection then successful retry
        mock_check_server.side_effect = [False, True]
        
        # Call the function
        result = wait_for_server("http://example.com", max_retries=2, retry_interval=1)
        
        # Verify the result is True (successful connection)
        self.assertTrue(result)
        
        # Verify check_server was called twice and sleep was called once
        self.assertEqual(mock_check_server.call_count, 2)
        mock_sleep.assert_called_once_with(1)
        
        # Check messages
        output = self.held_output.getvalue()
        self.assertIn("Retrying in 1 seconds", output)

    @patch('mcp_testing.http.utils.check_server')
    @patch('time.sleep')
    def test_wait_for_server_with_custom_params(self, mock_sleep, mock_check_server):
        """Test wait_for_server function with custom parameters."""
        # Mock successful connection after two failures
        mock_check_server.side_effect = [False, False, True]
        
        # Call the function with custom parameters
        result = wait_for_server(
            "http://example.com", 
            max_retries=3, 
            retry_interval=2, 
            timeout=10
        )
        
        # Verify the result is True (successful connection)
        self.assertTrue(result)
        
        # Verify check_server was called with custom timeout
        mock_check_server.assert_has_calls([
            call("http://example.com", 10),
            call("http://example.com", 10),
            call("http://example.com", 10)
        ])
        
        # Verify sleep was called with custom interval
        mock_sleep.assert_has_calls([
            call(2),
            call(2)
        ])

    @patch('mcp_testing.http.utils.check_server')
    @patch('time.sleep')
    def test_wait_for_server_all_attempts_fail(self, mock_sleep, mock_check_server):
        """Test wait_for_server function when all connection attempts fail."""
        # Mock all connection attempts failing
        mock_check_server.return_value = False
        
        # Call the function
        result = wait_for_server("http://example.com", max_retries=3, retry_interval=1)
        
        # Verify the result is False (failed connection)
        self.assertFalse(result)
        
        # Verify check_server was called max_retries times
        self.assertEqual(mock_check_server.call_count, 3)
        
        # Verify sleep was called max_retries-1 times
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Check failure message
        output = self.held_output.getvalue()
        self.assertIn("Failed to connect to server after 3 attempts", output)

    @patch('mcp_testing.http.utils.check_server')
    @patch('time.sleep')
    def test_wait_for_server_single_attempt(self, mock_sleep, mock_check_server):
        """Test wait_for_server function with max_retries=1 (single attempt)."""
        # Mock a failed connection
        mock_check_server.return_value = False
        
        # Call the function with only one attempt
        result = wait_for_server("http://example.com", max_retries=1)
        
        # Verify the result is False (failed connection)
        self.assertFalse(result)
        
        # Verify check_server was called once and sleep was not called
        mock_check_server.assert_called_once()
        mock_sleep.assert_not_called()
        
        # Check failure message
        output = self.held_output.getvalue()
        self.assertIn("Failed to connect to server after 1 attempts", output)


if __name__ == "__main__":
    unittest.main() 