#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the http_test.py script.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import sys
import os
import io
import tempfile
import shutil
import json
import logging
from argparse import Namespace

from mcp_testing.scripts import http_test
from mcp_testing.http.utils import wait_for_server


class TestHttpTest(unittest.TestCase):
    """Test cases for the http_test script."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout and stderr for testing
        self.held_output = io.StringIO()
        self.held_error = io.StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self.held_output
        sys.stderr = self.held_error
        
        # Save original sys.argv
        self.original_argv = sys.argv

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Restore original sys.argv
        sys.argv = self.original_argv

    @patch('mcp_testing.scripts.http_test.MCPHttpTester')
    @patch('mcp_testing.scripts.http_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_success(self, mock_parse_args, mock_wait_for_server, mock_tester):
        """Test the main function with successful execution."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8000',
            protocol_version='2025-03-26',
            output_dir=None,
            debug=False,
            max_retries=3,
            retry_interval=1
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server response
        mock_wait_for_server.return_value = True
        
        # Mock validation run
        mock_tester_instance = mock_tester.return_value
        mock_tester_instance.run_all_tests.return_value = True
        
        # Call the main function
        result = http_test.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once_with(
            'http://localhost:8000', 
            max_retries=3, 
            retry_interval=1
        )
        mock_tester.assert_called_once_with('http://localhost:8000', False)
        mock_tester_instance.run_all_tests.assert_called_once()

    @patch('mcp_testing.scripts.http_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_unreachable_server(self, mock_parse_args, mock_wait_for_server):
        """Test the main function when server is unreachable."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8000',
            protocol_version='2025-03-26',
            output_dir=None,
            debug=False,
            max_retries=1,
            retry_interval=0.1
        )
        mock_parse_args.return_value = mock_args
        
        # Mock unsuccessful server response
        mock_wait_for_server.return_value = False
        
        # Call the main function
        result = http_test.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once_with(
            'http://localhost:8000', 
            max_retries=1, 
            retry_interval=0.1
        )

    @patch('mcp_testing.scripts.http_test.MCPHttpTester')
    @patch('mcp_testing.scripts.http_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_test_failure(self, mock_parse_args, mock_wait_for_server, mock_tester):
        """Test the main function when tests fail."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8000',
            protocol_version='2025-03-26',
            output_dir=None,
            debug=False,
            max_retries=3,
            retry_interval=1
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server response but failed tests
        mock_wait_for_server.return_value = True
        mock_tester_instance = mock_tester.return_value
        mock_tester_instance.run_all_tests.return_value = False
        
        # Call the main function
        result = http_test.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once_with(
            'http://localhost:8000', 
            max_retries=3, 
            retry_interval=1
        )
        mock_tester.assert_called_once_with('http://localhost:8000', False)
        mock_tester_instance.run_all_tests.assert_called_once()

    @patch('mcp_testing.scripts.http_test.MCPHttpTester')
    @patch('mcp_testing.scripts.http_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('builtins.open', new_callable=mock_open)
    def test_main_with_report(self, mock_file, mock_parse_args, mock_wait_for_server, mock_tester):
        """Test the main function with report output."""
        # Create a temporary directory for the report
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock arguments
            mock_args = Namespace(
                server_url='http://localhost:8000',
                protocol_version='2025-03-26',
                output_dir=tmpdir,
                debug=False,
                max_retries=3,
                retry_interval=1
            )
            mock_parse_args.return_value = mock_args
            
            # Mock successful server and test responses
            mock_wait_for_server.return_value = True
            mock_tester_instance = mock_tester.return_value
            mock_tester_instance.run_all_tests.return_value = True
            
            # Call the main function
            result = http_test.main()
            
            # Assert that the function returned success (0)
            self.assertEqual(result, 0)
            
            # Verify method calls
            mock_wait_for_server.assert_called_once_with(
                'http://localhost:8000', 
                max_retries=3, 
                retry_interval=1
            )
            mock_tester.assert_called_once_with('http://localhost:8000', False)
            mock_tester_instance.run_all_tests.assert_called_once()
            
            # Verify that the report file was written
            mock_file.assert_called()

    @patch('mcp_testing.scripts.http_test.MCPHttpTester')
    @patch('mcp_testing.scripts.http_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_debug(self, mock_parse_args, mock_wait_for_server, mock_tester):
        """Test the main function with debug enabled."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8000',
            protocol_version='2025-03-26',
            output_dir=None,
            debug=True,
            max_retries=3,
            retry_interval=1
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server response
        mock_wait_for_server.return_value = True
        
        # Mock validation run
        mock_tester_instance = mock_tester.return_value
        mock_tester_instance.run_all_tests.return_value = True
        
        # Call the main function
        result = http_test.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify that the tester was created with debug=True
        mock_wait_for_server.assert_called_once_with(
            'http://localhost:8000', 
            max_retries=3, 
            retry_interval=1
        )
        mock_tester.assert_called_once_with('http://localhost:8000', True)

    @patch('argparse.ArgumentParser.parse_args')
    def test_main_exception_handling(self, mock_parse_args):
        """Test exception handling in the main function."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8000',
            protocol_version='2025-03-26',
            output_dir=None,
            debug=True,
            max_retries=3,
            retry_interval=1
        )
        mock_parse_args.return_value = mock_args
        
        # Create a side effect that raises an exception
        def raise_exception(*args, **kwargs):
            raise Exception("Test failure")
        
        # Mock wait_for_server to raise an exception        
        with patch('mcp_testing.scripts.http_test.wait_for_server', side_effect=raise_exception):
            # Call the main function
            result = http_test.main()
            
            # Assert that the function returned failure (1)
            self.assertEqual(result, 1)
            
            # Check error output
            error_output = self.held_error.getvalue()
            self.assertIn("Error during HTTP test", error_output)
            self.assertIn("Test failure", error_output)


if __name__ == "__main__":
    unittest.main() 