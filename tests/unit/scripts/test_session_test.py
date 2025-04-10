#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the session_test.py script.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import io
import subprocess
from argparse import Namespace

from mcp_testing.scripts import session_test
from mcp_testing.http.utils import wait_for_server


class TestSessionTest(unittest.TestCase):
    """Test cases for the session_test script."""

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

    @patch('mcp_testing.scripts.session_test.MCPSessionValidator')
    @patch('mcp_testing.scripts.session_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_success(self, mock_parse_args, mock_wait_for_server, mock_validator):
        """Test the main function with successful execution."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=False,
            server_port=8888,
            max_retries=3,
            retry_interval=2
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server response
        mock_wait_for_server.return_value = True
        
        # Mock successful validation
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.run_all_tests.return_value = True
        
        # Call the main function
        result = session_test.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once_with(
            'http://localhost:8888/mcp', 
            max_retries=3, 
            retry_interval=2
        )
        mock_validator.assert_called_once_with('http://localhost:8888/mcp', False)
        mock_validator_instance.run_all_tests.assert_called_once()
        
        # Check output contains success message
        output = self.held_output.getvalue()
        self.assertIn("✅ SERVER PASSED Session Validation Test", output)

    @patch('mcp_testing.scripts.session_test.MCPSessionValidator')
    @patch('mcp_testing.scripts.session_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_validation_failure(self, mock_parse_args, mock_wait_for_server, mock_validator):
        """Test the main function when validation fails."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=False,
            server_port=8888,
            max_retries=3,
            retry_interval=2
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server response but failed validation
        mock_wait_for_server.return_value = True
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.run_all_tests.return_value = False
        
        # Call the main function
        result = session_test.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once()
        mock_validator.assert_called_once()
        mock_validator_instance.run_all_tests.assert_called_once()
        
        # Check output contains failure message
        output = self.held_output.getvalue()
        self.assertIn("❌ SERVER FAILED Session Validation Test", output)

    @patch('mcp_testing.scripts.session_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_server_unreachable(self, mock_parse_args, mock_wait_for_server):
        """Test the main function when server is unreachable."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=False,
            server_port=8888,
            max_retries=1,
            retry_interval=1
        )
        mock_parse_args.return_value = mock_args
        
        # Mock unsuccessful server response
        mock_wait_for_server.return_value = False
        
        # Call the main function
        result = session_test.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Verify method calls
        mock_wait_for_server.assert_called_once()
        
        # Check error message
        output = self.held_output.getvalue()
        self.assertIn("ERROR: Could not connect to server", output)

    @patch('mcp_testing.scripts.session_test.subprocess.Popen')
    @patch('mcp_testing.scripts.session_test.subprocess.run')
    @patch('mcp_testing.scripts.session_test.time.sleep')
    @patch('mcp_testing.scripts.session_test.MCPSessionValidator')
    @patch('mcp_testing.scripts.session_test.wait_for_server')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_restart_server_success(self, mock_parse_args, mock_wait_for_server, 
                                         mock_validator, mock_sleep, mock_run, mock_popen):
        """Test the main function with server restart."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=True,
            server_port=8888,
            max_retries=3,
            retry_interval=2
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful server process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process still running
        mock_popen.return_value = mock_process
        
        # Mock successful server connection and validation
        mock_wait_for_server.return_value = True
        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.run_all_tests.return_value = True
        
        # Call the main function
        result = session_test.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify method calls
        mock_run.assert_called_once()  # Called to kill existing processes
        mock_popen.assert_called_once()  # Called to start new server
        mock_process.poll.assert_called_once()  # Called to check if server started
        mock_wait_for_server.assert_called_once()
        mock_validator.assert_called_once()
        
        # Check output contains server restart and success messages
        output = self.held_output.getvalue()
        self.assertIn("Restarting the MCP HTTP server", output)
        self.assertIn("Server started successfully", output)
        self.assertIn("✅ SERVER PASSED Session Validation Test", output)

    @patch('mcp_testing.scripts.session_test.subprocess.Popen')
    @patch('mcp_testing.scripts.session_test.subprocess.run')
    @patch('mcp_testing.scripts.session_test.time.sleep')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_restart_server_failure(self, mock_parse_args, mock_sleep, mock_run, mock_popen):
        """Test the main function when server restart fails."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=True,
            server_port=8888,
            max_retries=3,
            retry_interval=2
        )
        mock_parse_args.return_value = mock_args
        
        # Mock failed server process
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited with error
        mock_process.communicate.return_value = ("stdout output", "stderr output")
        mock_popen.return_value = mock_process
        
        # Call the main function
        result = session_test.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Verify method calls
        mock_run.assert_called_once()  # Called to kill existing processes
        mock_popen.assert_called_once()  # Called to start new server
        mock_process.poll.assert_called_once()  # Called to check if server started
        mock_process.communicate.assert_called_once()  # Called to get output from failed process
        
        # Check output contains server failure message
        output = self.held_output.getvalue()
        self.assertIn("ERROR: Failed to start the server", output)

    @patch('argparse.ArgumentParser.parse_args')
    def test_main_restart_server_exception(self, mock_parse_args):
        """Test the main function when server restart raises an exception."""
        # Mock arguments
        mock_args = Namespace(
            server_url='http://localhost:8888/mcp',
            protocol_version='2025-03-26',
            debug=False,
            restart_server=True,
            server_port=8888,
            max_retries=3,
            retry_interval=2
        )
        mock_parse_args.return_value = mock_args
        
        # Mock subprocess.run to raise an exception
        with patch('mcp_testing.scripts.session_test.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Test failure")
            
            # Call the main function
            result = session_test.main()
            
            # Assert that the function returned failure (1)
            self.assertEqual(result, 1)
            
            # Check output contains exception message
            output = self.held_output.getvalue()
            self.assertIn("ERROR: Failed to restart the server", output)
            self.assertIn("Test failure", output)

if __name__ == '__main__':
    unittest.main() 