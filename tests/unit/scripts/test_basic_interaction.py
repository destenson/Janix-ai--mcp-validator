#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the basic_interaction.py script.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import io
import json
import logging
from argparse import Namespace

from mcp_testing.scripts import basic_interaction


class LogCapture:
    """Helper class to capture log messages."""
    
    def __init__(self):
        self.messages = []
        self.handler = None
        
    def start(self):
        """Start capturing log messages."""
        self.handler = logging.StreamHandler(io.StringIO())
        self.handler.setLevel(logging.DEBUG)
        
        for name in ["mcp_testing", "mcp_testing.scripts.basic_interaction"]:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(self.handler)
            
    def stop(self):
        """Stop capturing log messages."""
        if self.handler:
            for name in ["mcp_testing", "mcp_testing.scripts.basic_interaction"]:
                logging.getLogger(name).removeHandler(self.handler)
                
    def get_logs(self):
        """Get the captured log messages."""
        if self.handler:
            return self.handler.stream.getvalue()
        return ""


class TestBasicInteraction(unittest.TestCase):
    """Test cases for the basic_interaction script."""

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
        
        # Setup log capture
        self.log_capture = LogCapture()
        self.log_capture.start()

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Restore original sys.argv
        sys.argv = self.original_argv
        
        # Stop log capture
        self.log_capture.stop()

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_success(self, mock_transport_class, mock_parse_args):
        """Test the main function with successful execution."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=False,
            debug=False
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful transport responses
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = True
    
        # Mock successful initialization
        init_response = {
            "jsonrpc": "2.0",
            "id": "init",
            "result": {
                "serverInfo": {"name": "Test Server", "version": "1.0"},
                "capabilities": {}
            }
        }
        mock_transport_instance.send_request.side_effect = [
            init_response,  # initialization response
            {  # tools/list response
                "jsonrpc": "2.0",
                "id": "tools_list",
                "result": {
                    "tools": [
                        {"name": "echo", "description": "Echo text back"},
                        {"name": "add", "description": "Add two numbers"}
                    ]
                }
            },
            {  # list_directory response
                "jsonrpc": "2.0",
                "id": "list_dir_call",
                "result": {
                    "files": ["file1.txt", "file2.txt"]
                }
            },
            {  # shutdown response
                "jsonrpc": "2.0",
                "id": "shutdown",
                "result": {}
            }
        ]
    
        # Call the main function
        result = basic_interaction.main()
    
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
    
        # Check that methods were called
        mock_transport_instance.start.assert_called_once()
        self.assertEqual(mock_transport_instance.send_request.call_count, 4)
        mock_transport_instance.send_notification.assert_called_once()
        mock_transport_instance.stop.assert_called_once()
    
        # Check the log messages
        logs = self.log_capture.get_logs()
        self.assertIn("Starting server", logs)
        self.assertIn("Initializing server", logs)
        self.assertIn("Server has 2 tools", logs)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_with_allowed_dirs(self, mock_transport_class, mock_parse_args):
        """Test the main function with list_allowed_dirs option."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=True,
            debug=False
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful transport responses
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = True
    
        # Mock responses
        mock_transport_instance.send_request.side_effect = [
            {  # initialization response
                "jsonrpc": "2.0",
                "id": "init",
                "result": {
                    "serverInfo": {"name": "Test Server", "version": "1.0"},
                    "capabilities": {}
                }
            },
            {  # tools/list response
                "jsonrpc": "2.0",
                "id": "tools_list",
                "result": {
                    "tools": [
                        {"name": "list_allowed_directories", "description": "List allowed directories"}
                    ]
                }
            },
            {  # list_allowed_directories response
                "jsonrpc": "2.0",
                "id": "tool_call",
                "result": {
                    "directories": ["/home", "/tmp"]
                }
            },
            {  # list_directory response
                "jsonrpc": "2.0",
                "id": "list_dir_call",
                "result": {
                    "files": ["file1.txt", "file2.txt"]
                }
            },
            {  # shutdown response
                "jsonrpc": "2.0",
                "id": "shutdown",
                "result": {}
            }
        ]
    
        # Call the main function
        result = basic_interaction.main()
    
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
    
        # Verify transport method calls
        self.assertEqual(mock_transport_instance.send_request.call_count, 5)
        
        # Check the log messages
        logs = self.log_capture.get_logs()
        self.assertIn("Trying to list allowed directories", logs)
        self.assertIn("Allowed directories response", logs)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_debug_mode(self, mock_transport_class, mock_parse_args):
        """Test the main function with debug mode enabled."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=False,
            debug=True
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful transport responses
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = True
        
        # Mock responses
        mock_transport_instance.send_request.side_effect = [
            {  # initialization response
                "jsonrpc": "2.0",
                "id": "init",
                "result": {
                    "serverInfo": {"name": "Test Server", "version": "1.0"},
                    "capabilities": {}
                }
            },
            {  # tools/list response
                "jsonrpc": "2.0",
                "id": "tools_list",
                "result": {
                    "tools": []
                }
            },
            {  # list_directory response
                "jsonrpc": "2.0",
                "id": "list_dir_call",
                "result": {
                    "files": []
                }
            },
            {  # shutdown response
                "jsonrpc": "2.0",
                "id": "shutdown",
                "result": {}
            }
        ]
        
        # Call the main function
        result = basic_interaction.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify debug mode was passed to the transport
        mock_transport_class.assert_called_once()
        _, kwargs = mock_transport_class.call_args
        self.assertTrue(kwargs.get('debug', False))

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_start_failure(self, mock_transport_class, mock_parse_args):
        """Test the main function when server start fails."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=False,
            debug=False
        )
        mock_parse_args.return_value = mock_args
        
        # Mock failed transport start
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = False
        
        # Call the main function
        result = basic_interaction.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Assert that the transport was started but stop is still called in the finally block
        mock_transport_instance.start.assert_called_once()
        mock_transport_instance.stop.assert_called_once()  # Stop is always called in finally block
        
        # Check that error was logged
        logs = self.log_capture.get_logs()
        self.assertIn("Failed to start server", logs)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_exception_handling(self, mock_transport_class, mock_parse_args):
        """Test the main function's exception handling."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=False,
            debug=False
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful start but exception during send_request
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = True
        mock_transport_instance.send_request.side_effect = Exception("Test exception")
        
        # Call the main function
        result = basic_interaction.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Assert that the transport was started and stopped
        mock_transport_instance.start.assert_called_once()
        mock_transport_instance.stop.assert_called_once()
        
        # Check error was logged
        logs = self.log_capture.get_logs()
        self.assertIn("Error during interaction", logs)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.scripts.basic_interaction.StdioTransportAdapter')
    def test_main_tool_list_exception(self, mock_transport_class, mock_parse_args):
        """Test the main function when tools/list throws an exception."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            list_allowed_dirs=False,
            debug=False
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful transport start
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.start.return_value = True
        
        # Make initialization succeed but tools/list fail
        mock_transport_instance.send_request.side_effect = [
            {  # initialization response
                "jsonrpc": "2.0",
                "id": "init",
                "result": {"serverInfo": {"name": "Test Server"}}
            },
            Exception("Error listing tools"),  # tools/list throws exception
            {  # list_directory response
                "jsonrpc": "2.0",
                "id": "list_dir_call",
                "result": {
                    "files": ["file1.txt", "file2.txt"]
                }
            },
            {  # shutdown response
                "jsonrpc": "2.0",
                "id": "shutdown",
                "result": {}
            }
        ]
        
        # Call the main function
        result = basic_interaction.main()
        
        # Since the exception is caught and handled, main should still complete successfully
        self.assertEqual(result, 0)
        
        # Verify error was logged
        logs = self.log_capture.get_logs()
        self.assertIn("Error listing tools", logs)

if __name__ == "__main__":
    unittest.main() 