#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the STDIO Tester module
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import subprocess
from io import StringIO
import logging
import sys

from mcp_testing.stdio.tester import MCPStdioTester


class TestMCPStdioTester(unittest.TestCase):
    """Tests for the MCPStdioTester class."""

    def setUp(self):
        """Set up the test environment."""
        # Capture logs
        self.log_capture = StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        logging.getLogger("MCPStdioTester").addHandler(self.log_handler)
        
        # Create tester instance
        self.tester = MCPStdioTester("python", ["server.py"], debug=True)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove log handler
        logging.getLogger("MCPStdioTester").removeHandler(self.log_handler)
    
    def test_init(self):
        """Test initialization of the tester."""
        tester = MCPStdioTester("node", ["server.js", "--debug"], debug=True)
        
        self.assertEqual(tester.server_command, "node")
        self.assertEqual(tester.args, ["server.js", "--debug"])
        self.assertTrue(tester.debug)
        self.assertEqual(tester.protocol_version, "2025-03-26")
        self.assertIsNone(tester.server_process)
        self.assertEqual(tester.client_id, 1)
        self.assertIsNone(tester.session_id)
        
        # Check log output
        self.assertIn("Initialized tester with command: node server.js --debug", self.log_capture.getvalue())

    @patch('mcp_testing.stdio.tester.logger.debug')
    def test_init_with_defaults(self, mock_debug):
        """Test initialization with default arguments."""
        # Initialize with default args (without specifying args parameter)
        tester = MCPStdioTester("python")
        
        # Verify the tester was initialized with defaults
        self.assertEqual(tester.server_command, "python")
        self.assertEqual(tester.args, [])  # Should be an empty list, not None
        self.assertFalse(tester.debug)
        
        # Verify logging behavior
        # The debug message in __init__ shouldn't be called since debug=False
        mock_debug.assert_not_called()
        
        # Now test with debug=True to verify debug logging
        mock_debug.reset_mock()
        tester_with_debug = MCPStdioTester("python", debug=True)
        mock_debug.assert_called_once_with("Initialized tester with command: python ")
    
    @patch('mcp_testing.stdio.tester.shlex.split')
    @patch('mcp_testing.stdio.tester.check_command_exists')
    @patch('mcp_testing.stdio.tester.subprocess.Popen')
    @patch('mcp_testing.stdio.tester.time.sleep')
    def test_start_server_success(self, mock_sleep, mock_popen, mock_check, mock_shlex):
        """Test starting a server successfully."""
        # Setup mocks
        mock_check.return_value = True
        mock_shlex.return_value = ["python"]  # Return a simple command without script arg
        
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process
        
        # Call method
        result = self.tester.start_server()
        
        # Verify
        self.assertTrue(result)
        mock_check.assert_called_once_with("python")
        
        # verify_python_server is only called if python command has a script arg
        # our mock returns just ["python"] so it shouldn't be called
        
        mock_popen.assert_called_once()
        self.assertEqual(self.tester.server_process, mock_process)
        
        # Check command args
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], ["python", "server.py"])  # Should be command + args
        self.assertEqual(kwargs['stdin'], subprocess.PIPE)
        self.assertEqual(kwargs['stdout'], subprocess.PIPE)
        self.assertEqual(kwargs['stderr'], subprocess.PIPE)
        self.assertTrue(kwargs['text'])
        
        # Verify sleep was called
        mock_sleep.assert_called_once()
        
        # Check log output
        self.assertIn("Starting server with command", self.log_capture.getvalue())
        self.assertIn("Server started successfully", self.log_capture.getvalue())
    
    @patch('mcp_testing.stdio.tester.check_command_exists')
    def test_start_server_command_not_found(self, mock_check):
        """Test starting a server with a command that doesn't exist."""
        # Setup mocks
        mock_check.return_value = False
        
        # Call method
        result = self.tester.start_server()
        
        # Verify
        self.assertFalse(result)
        mock_check.assert_called_once_with('python')
        
        # Check log output
        self.assertIn("Command not found: python", self.log_capture.getvalue())
    
    @patch('mcp_testing.stdio.tester.check_command_exists')
    @patch('mcp_testing.stdio.tester.subprocess.Popen')
    @patch('mcp_testing.stdio.tester.time.sleep')
    def test_start_server_premature_exit(self, mock_sleep, mock_popen, mock_check):
        """Test starting a server that exits prematurely."""
        # Setup mocks
        mock_check.return_value = True
        
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited with code 1
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = "Error: Invalid arguments"
        mock_popen.return_value = mock_process
        
        # Call method
        result = self.tester.start_server()
        
        # Verify
        self.assertFalse(result)
        
        # Check log output
        self.assertIn("Server exited with code 1", self.log_capture.getvalue())
        self.assertIn("Error: Invalid arguments", self.log_capture.getvalue())
    
    @patch('mcp_testing.stdio.tester.check_command_exists')
    @patch('mcp_testing.stdio.tester.subprocess.Popen')
    def test_start_server_exception(self, mock_popen, mock_check):
        """Test starting a server that throws an exception."""
        # Setup mocks
        mock_check.return_value = True
        mock_popen.side_effect = Exception("Process start failed")
        
        # Call method
        result = self.tester.start_server()
        
        # Verify
        self.assertFalse(result)
        
        # Check log output
        self.assertIn("Failed to start server: Process start failed", self.log_capture.getvalue())
    
    def test_stop_server_no_process(self):
        """Test stopping a server when no process is running."""
        # Verify initial state
        self.assertIsNone(self.tester.server_process)
        
        # Call method
        self.tester.stop_server()
        
        # No exception should be raised
    
    @patch('mcp_testing.stdio.tester.MCPStdioTester._send_request')
    def test_stop_server_with_process(self, mock_send_request):
        """Test stopping a server process."""
        # Setup mock process
        mock_process = MagicMock()
        self.tester.server_process = mock_process
        
        # Call method
        self.tester.stop_server()
        
        # Verify
        mock_send_request.assert_called_once_with("shutdown", {})
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        mock_process.stdin.close.assert_called_once()
        mock_process.stdout.close.assert_called_once()
        mock_process.stderr.close.assert_called_once()
        
        # Verify server_process is reset
        self.assertIsNone(self.tester.server_process)
        
        # Check log output
        self.assertIn("Server stopped", self.log_capture.getvalue())
    
    @patch('mcp_testing.stdio.tester.MCPStdioTester._send_request')
    def test_stop_server_timeout(self, mock_send_request):
        """Test stopping a server process that times out."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 2)
        self.tester.server_process = mock_process
        
        # Call method
        self.tester.stop_server()
        
        # Verify
        mock_process.kill.assert_called_once()
        
        # Check log output
        self.assertIn("Server did not terminate within timeout", self.log_capture.getvalue())
    
    def test_send_request_no_server(self):
        """Test sending a request when no server is running."""
        # Verify initial state
        self.assertIsNone(self.tester.server_process)
        
        # Call method
        success, response = self.tester._send_request("test", {})
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(response, {"error": "Server not running"})
        
        # Check log output
        self.assertIn("Cannot send request - server not running", self.log_capture.getvalue())
    
    def test_send_request_success(self):
        """Test sending a request successfully."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": {"success": true}}'
        self.tester.server_process = mock_process
        
        # Call method
        success, response = self.tester._send_request("test", {"param": "value"})
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(response, {"jsonrpc": "2.0", "id": 1, "result": {"success": True}})
        
        # Verify request was written correctly
        write_call = mock_process.stdin.write.call_args[0][0]
        request_obj = json.loads(write_call.rstrip("\n"))
        self.assertEqual(request_obj["method"], "test")
        self.assertEqual(request_obj["params"], {"param": "value"})
        self.assertEqual(request_obj["id"], 1)
        
        # Verify flush was called
        mock_process.stdin.flush.assert_called_once()
    
    def test_send_request_with_session_id(self):
        """Test sending a request with a session ID."""
        # Setup mock process and session ID
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "result": {}}'
        self.tester.server_process = mock_process
        self.tester.session_id = "test-session-id"
        
        # Call method
        self.tester._send_request("tools/list", {})
        
        # Verify sessionId was included
        write_call = mock_process.stdin.write.call_args[0][0]
        request_obj = json.loads(write_call.rstrip("\n"))
        self.assertEqual(request_obj["sessionId"], "test-session-id")
    
    def test_send_request_error_response(self):
        """Test sending a request that gets an error response."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}}'
        self.tester.server_process = mock_process
        
        # Call method
        success, response = self.tester._send_request("test", {})
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertEqual(response["error"]["message"], "Invalid Request")
        
        # Check log output
        self.assertIn("Server returned error", self.log_capture.getvalue())
    
    def test_send_request_no_response(self):
        """Test sending a request that gets no response."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = ''  # Empty response
        self.tester.server_process = mock_process
        
        # Call method
        success, response = self.tester._send_request("test", {})
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(response, {"error": "No response received"})
        
        # Check log output
        self.assertIn("Server closed connection without sending a response", self.log_capture.getvalue())
    
    @patch('mcp_testing.stdio.tester.MCPStdioTester._send_request')
    def test_initialize_success(self, mock_send_request):
        """Test initializing the server successfully."""
        # Setup mock response
        mock_send_request.return_value = (True, {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "Test Server", "version": "1.0.0"},
                "capabilities": {"tools": {"asyncSupported": True}},
                "sessionId": "test-session-id"
            }
        })
        
        # Call method
        result = self.tester.initialize()
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.tester.session_id, "test-session-id")
        
        # Check if the params match what's actually in the code
        # Rather than checking exact match, check key fields
        call_args = mock_send_request.call_args[0]
        self.assertEqual(call_args[0], "initialize")
        params = call_args[1]
        self.assertEqual(params["protocolVersion"], "2025-03-26")
        self.assertEqual(params["clientInfo"]["name"], "MCP STDIO Tester")


if __name__ == '__main__':
    unittest.main() 