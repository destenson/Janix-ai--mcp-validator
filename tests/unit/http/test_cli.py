#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the HTTP CLI module
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO

from mcp_testing.http.cli import main, run_http_tester


class TestHttpCli(unittest.TestCase):
    """Tests for the HTTP CLI module."""

    @patch('mcp_testing.http.cli.wait_for_server')
    @patch('mcp_testing.http.cli.run_http_tester')
    def test_main_success(self, mock_run_tester, mock_wait_for_server):
        """Test that main returns 0 when tests pass."""
        # Setup
        mock_wait_for_server.return_value = True
        mock_run_tester.return_value = True
        
        # Redirect stdout for testing
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Run with test arguments
            with patch('sys.argv', ['cli.py', '--server-url', 'http://test-server:8000/mcp']):
                result = main()
                
            # Verify
            self.assertEqual(result, 0)
            mock_wait_for_server.assert_called_once()
            mock_run_tester.assert_called_once_with('http://test-server:8000/mcp', False, '2025-03-26')
            self.assertIn("All HTTP tests passed", sys.stdout.getvalue())
        finally:
            # Restore stdout
            sys.stdout = original_stdout

    @patch('mcp_testing.http.cli.wait_for_server')
    @patch('mcp_testing.http.cli.run_http_tester')
    def test_main_failure(self, mock_run_tester, mock_wait_for_server):
        """Test that main returns 1 when tests fail."""
        # Setup
        mock_wait_for_server.return_value = True
        mock_run_tester.return_value = False
        
        # Redirect stderr for testing
        original_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            # Run with test arguments
            with patch('sys.argv', ['cli.py']):
                result = main()
                
            # Verify
            self.assertEqual(result, 1)
            mock_wait_for_server.assert_called_once()
            mock_run_tester.assert_called_once()
            self.assertIn("Some HTTP tests failed", sys.stderr.getvalue())
        finally:
            # Restore stderr
            sys.stderr = original_stderr

    @patch('mcp_testing.http.cli.wait_for_server')
    def test_main_server_unreachable(self, mock_wait_for_server):
        """Test that main returns 1 when server is unreachable."""
        # Setup
        mock_wait_for_server.return_value = False
        
        # Run with test arguments
        with patch('sys.argv', ['cli.py']):
            result = main()
            
        # Verify
        self.assertEqual(result, 1)
        mock_wait_for_server.assert_called_once()

    @patch('mcp_testing.http.cli.MCPHttpTester')
    def test_run_http_tester(self, mock_tester_class):
        """Test that run_http_tester creates a tester and runs all tests."""
        # Setup the mock
        mock_tester = MagicMock()
        mock_tester_class.return_value = mock_tester
        mock_tester.run_all_tests.return_value = True
        
        # Call the function
        result = run_http_tester("http://test-server:8000/mcp", True, "2024-11-05")
        
        # Verify
        self.assertTrue(result)
        mock_tester_class.assert_called_once_with("http://test-server:8000/mcp", True)
        self.assertEqual(mock_tester.protocol_version, "2024-11-05")
        mock_tester.run_all_tests.assert_called_once()


if __name__ == '__main__':
    unittest.main() 