#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the HTTP session validator.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY, call
import io
import sys
import json
import uuid
import requests
from urllib.parse import urlparse

from mcp_testing.http.session_validator import MCPSessionValidator, main


class TestMCPSessionValidator(unittest.TestCase):
    """Test cases for the MCPSessionValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout for testing
        self.held_output = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.held_output
        
        # Create a validator instance for testing
        self.validator = MCPSessionValidator("http://example.com/mcp", debug=True)
        
        # Reset output capture for tests
        self.held_output.truncate(0)
        self.held_output.seek(0)

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout
        sys.stdout = self.original_stdout

    def test_init(self):
        """Test the initialization of the validator."""
        # Create a fresh validator to test initialization
        validator = MCPSessionValidator("http://example.com:8080/api/mcp", debug=True)
        
        # Verify the parsed URL components
        self.assertEqual(validator.url, "http://example.com:8080/api/mcp")
        self.assertEqual(validator.host, "example.com:8080")
        self.assertEqual(validator.path, "/api/mcp")
        self.assertEqual(validator.protocol_version, "2025-03-26")
        self.assertTrue(validator.debug)
        
        # Check initialization message
        output = self.held_output.getvalue()
        self.assertIn("Session Validator initialized for http://example.com:8080/api/mcp", output)
        self.assertIn("Host: example.com:8080, Path: /api/mcp", output)

    def test_log(self):
        """Test the log method with debug enabled and disabled."""
        # Test with debug enabled
        self.validator.debug = True
        self.validator.log("Debug message")
        output = self.held_output.getvalue()
        self.assertIn("[DEBUG] Debug message", output)
        
        # Reset output
        self.held_output.truncate(0)
        self.held_output.seek(0)
        
        # Test with debug disabled
        self.validator.debug = False
        self.validator.log("Debug message")
        output = self.held_output.getvalue()
        self.assertEqual("", output)  # Nothing should be logged

    @patch('requests.post')
    def test_send_request_with_session_no_session_id(self, mock_post):
        """Test sending a request without a session ID."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "12345", "result": {}}
        mock_post.return_value = mock_response
        
        # Send request without session ID
        status, headers, body = self.validator.send_request_with_session("test_method")
        
        # Verify results
        self.assertEqual(status, 200)
        self.assertEqual(headers, {'Content-Type': 'application/json'})
        self.assertEqual(body, {"jsonrpc": "2.0", "id": "12345", "result": {}})
        
        # Verify the request was sent correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://example.com/mcp")
        self.assertEqual(kwargs['json']['method'], "test_method")
        self.assertEqual(kwargs['json']['jsonrpc'], "2.0")
        self.assertNotIn("Mcp-Session-Id", kwargs['headers'])

    @patch('requests.post')
    def test_send_request_with_session_with_session_id(self, mock_post):
        """Test sending a request with a session ID."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "12345", "result": {}}
        mock_post.return_value = mock_response
        
        # Send request with session ID
        status, headers, body = self.validator.send_request_with_session(
            "test_method", 
            session_id="test-session-id"
        )
        
        # Verify results
        self.assertEqual(status, 200)
        self.assertEqual(headers, {'Content-Type': 'application/json'})
        self.assertEqual(body, {"jsonrpc": "2.0", "id": "12345", "result": {}})
        
        # Verify the request was sent correctly with session ID
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://example.com/mcp")
        self.assertEqual(kwargs['json']['method'], "test_method")
        self.assertEqual(kwargs['json']['jsonrpc'], "2.0")
        self.assertEqual(kwargs['headers']["Mcp-Session-Id"], "test-session-id")

    @patch('requests.post')
    def test_send_request_with_json_data(self, mock_post):
        """Test sending a request with JSON data."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "12345", "result": {}}
        mock_post.return_value = mock_response
        
        # Send request with JSON data
        json_data = {"param1": "value1", "param2": 42}
        status, headers, body = self.validator.send_request_with_session(
            "test_method", 
            session_id="test-session-id",
            json_data=json_data
        )
        
        # Verify the request was sent with the JSON data
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['params'], json_data)

    @patch('requests.post')
    def test_send_request_with_non_json_response(self, mock_post):
        """Test handling a non-JSON response."""
        # Mock response with non-JSON content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "This is not JSON"
        mock_post.return_value = mock_response
        
        # Send request
        status, headers, body = self.validator.send_request_with_session("test_method")
        
        # Verify results
        self.assertEqual(status, 200)
        self.assertEqual(body, "This is not JSON")

    @patch('requests.post')
    def test_send_request_with_request_exception(self, mock_post):
        """Test handling a request exception."""
        # Mock a request exception
        mock_post.side_effect = requests.RequestException("Connection error")
        
        # Verify the exception is propagated
        with self.assertRaises(requests.RequestException) as cm:
            self.validator.send_request_with_session("test_method")
        
        self.assertEqual(str(cm.exception), "Connection error")

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_initialize_and_get_session_header(self, mock_send_request):
        """Test initializing and getting a session ID from headers."""
        # Mock a successful response with session ID in headers
        mock_send_request.return_value = (
            200,  # status code
            {'mcp-session-id': 'test-session-1234'},  # headers
            {"jsonrpc": "2.0", "id": "init", "result": {}}  # body
        )
        
        # Call the method
        session_id = self.validator.initialize_and_get_session()
        
        # Verify results
        self.assertEqual(session_id, 'test-session-1234')
        
        # Verify the correct request was sent
        mock_send_request.assert_called_once()
        args, kwargs = mock_send_request.call_args
        self.assertEqual(args[0], "initialize")
        self.assertIsNone(args[1])  # No session ID
        # Check that the protocolVersion was passed correctly
        self.assertIn("protocolVersion", mock_send_request.call_args[0][2])
        self.assertEqual(mock_send_request.call_args[0][2]["protocolVersion"], "2025-03-26")
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Session ID found in headers: test-session-1234", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_initialize_and_get_session_body(self, mock_send_request):
        """Test initializing and getting a session ID from body."""
        # Mock a successful response with session ID in body
        mock_send_request.return_value = (
            200,  # status code
            {},  # headers (no session ID)
            {  # body with session ID
                "jsonrpc": "2.0", 
                "id": "init", 
                "result": {"sessionId": "test-session-body"}
            }
        )
        
        # Call the method
        session_id = self.validator.initialize_and_get_session()
        
        # Verify results
        self.assertEqual(session_id, 'test-session-body')
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Session ID found in response body: test-session-body", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_initialize_and_get_session_no_session_id(self, mock_send_request):
        """Test initializing with no session ID returned."""
        # Mock a response with no session ID anywhere
        mock_send_request.return_value = (
            200,  # status code
            {},  # headers (no session ID)
            {"jsonrpc": "2.0", "id": "init", "result": {}}  # body (no session ID)
        )
        
        # Call the method
        session_id = self.validator.initialize_and_get_session()
        
        # Verify results
        self.assertIsNone(session_id)
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("❌ Failure: No session ID found in response", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_initialize_and_get_session_error(self, mock_send_request):
        """Test initializing with an error response."""
        # Mock an error response
        mock_send_request.return_value = (
            400,  # status code
            {},  # headers
            {"jsonrpc": "2.0", "id": "init", "error": {"code": -32600, "message": "Invalid request"}}
        )
        
        # Call the method
        session_id = self.validator.initialize_and_get_session()
        
        # Verify results
        self.assertIsNone(session_id)
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("ERROR: Initialize request failed with status 400", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_initialize_and_get_session_exception(self, mock_send_request):
        """Test initializing with an exception."""
        # Mock an exception
        mock_send_request.side_effect = Exception("Test exception")
        
        # Call the method
        session_id = self.validator.initialize_and_get_session()
        
        # Verify results
        self.assertIsNone(session_id)
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("ERROR: Initialize request raised exception: Test exception", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_test_no_session_id_success(self, mock_send_request):
        """Test the no_session_id test with successful rejection."""
        # Mock a response with an error about missing session
        mock_send_request.return_value = (
            401,  # status code
            {},  # headers
            {  # body with session error
                "jsonrpc": "2.0", 
                "id": "test", 
                "error": {"code": -32000, "message": "Missing session ID"}
            }
        )
        
        # Call the method
        result = self.validator.test_no_session_id("test-session")
        
        # Verify results
        self.assertTrue(result)
        
        # Verify the correct request was sent (without session ID)
        mock_send_request.assert_called_once_with("server/info")
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Server correctly rejected request without session ID", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_test_no_session_id_failure(self, mock_send_request):
        """Test the no_session_id test with incorrect acceptance."""
        # Mock a successful response (incorrect behavior)
        mock_send_request.return_value = (
            200,  # status code
            {},  # headers
            {"jsonrpc": "2.0", "id": "test", "result": {}}  # body
        )
        
        # Call the method
        result = self.validator.test_no_session_id("test-session")
        
        # Verify results
        self.assertFalse(result)
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("❌ Failure: Server did not reject request without session ID", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_test_invalid_session_id(self, mock_send_request):
        """Test the invalid_session_id test."""
        # Mock a response with an error about invalid session
        mock_send_request.return_value = (
            401,  # status code
            {},  # headers
            {  # body with session error
                "jsonrpc": "2.0", 
                "id": "test", 
                "error": {"code": -32000, "message": "Invalid session ID"}
            }
        )
        
        # Call the method
        result = self.validator.test_invalid_session_id("test-session")
        
        # Verify results
        self.assertTrue(result)
        
        # Verify the request was sent with an invalid session ID
        mock_send_request.assert_called_once()
        args, kwargs = mock_send_request.call_args
        self.assertEqual(args[0], "server/info")
        self.assertNotEqual(args[1], "test-session")  # Should be an invalid session ID
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Server correctly rejected request with invalid session ID", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_test_valid_session_id(self, mock_send_request):
        """Test the valid_session_id test."""
        # Mock a successful response
        mock_send_request.return_value = (
            200,  # status code
            {},  # headers
            {"jsonrpc": "2.0", "id": "test", "result": {}}  # body
        )
        
        # Call the method
        result = self.validator.test_valid_session_id("test-session")
        
        # Verify results
        self.assertTrue(result)
        
        # Verify the request was sent with the valid session ID
        mock_send_request.assert_called_once()
        args, kwargs = mock_send_request.call_args
        self.assertEqual(args[0], "server/info")
        self.assertEqual(args[1], "test-session")
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Server accepted request with valid session ID", output)

    @patch.object(MCPSessionValidator, 'send_request_with_session')
    def test_test_tools_list_with_session(self, mock_send_request):
        """Test the tools_list_with_session test."""
        # Mock a successful response with tools
        mock_send_request.return_value = (
            200,  # status code
            {},  # headers
            {  # body with tools
                "jsonrpc": "2.0", 
                "id": "test", 
                "result": {
                    "tools": [
                        {"name": "tool1", "description": "Test Tool 1"},
                        {"name": "tool2", "description": "Test Tool 2"}
                    ]
                }
            }
        )
        
        # Call the method
        result = self.validator.test_tools_list_with_session("test-session")
        
        # Verify results
        self.assertTrue(result)
        
        # Verify the request was sent correctly
        mock_send_request.assert_called_once()
        args, kwargs = mock_send_request.call_args
        self.assertEqual(args[0], "tools/list")
        self.assertEqual(args[1], "test-session")
        
        # Check output message
        output = self.held_output.getvalue()
        self.assertIn("✅ Success: Server returned tools list with valid session ID", output)
        self.assertIn("Found 2 tools", output)

    @patch.object(MCPSessionValidator, 'initialize_and_get_session')
    @patch.object(MCPSessionValidator, 'test_no_session_id')
    @patch.object(MCPSessionValidator, 'test_invalid_session_id')
    @patch.object(MCPSessionValidator, 'test_valid_session_id')
    @patch.object(MCPSessionValidator, 'test_tools_list_with_session')
    @patch.object(MCPSessionValidator, 'test_tool_call_with_session')
    def test_run_all_tests_success(
        self, 
        mock_tool_call, 
        mock_tools_list, 
        mock_valid, 
        mock_invalid, 
        mock_no_session, 
        mock_initialize
    ):
        """Test running all tests with success."""
        # Mock successful responses for all tests
        mock_initialize.return_value = "test-session-123"
        mock_no_session.return_value = True
        mock_invalid.return_value = True
        mock_valid.return_value = True
        mock_tools_list.return_value = True
        mock_tool_call.return_value = True
        
        # Call the method
        result = self.validator.run_all_tests()
        
        # Verify results
        self.assertTrue(result)
        
        # Verify all tests were called
        mock_initialize.assert_called_once()
        mock_no_session.assert_called_once_with("test-session-123")
        mock_invalid.assert_called_once_with("test-session-123")
        mock_valid.assert_called_once_with("test-session-123")
        mock_tools_list.assert_called_once_with("test-session-123")
        mock_tool_call.assert_called_once_with("test-session-123")
        
        # Check summary message
        output = self.held_output.getvalue()
        self.assertIn("=== Session Validation Test Results ===", output)
        self.assertIn("Tests passed: 5/5", output)
        self.assertIn("All session validation tests PASSED", output)

    @patch.object(MCPSessionValidator, 'initialize_and_get_session')
    def test_run_all_tests_failed_initialization(self, mock_initialize):
        """Test running all tests with failed initialization."""
        # Mock failed initialization
        mock_initialize.return_value = None
        
        # Call the method
        result = self.validator.run_all_tests()
        
        # Verify results
        self.assertFalse(result)
        
        # Check error message
        output = self.held_output.getvalue()
        self.assertIn("Session validation FAILED: Could not obtain a session ID", output)

    @patch.object(MCPSessionValidator, 'initialize_and_get_session')
    @patch.object(MCPSessionValidator, 'test_no_session_id')
    @patch.object(MCPSessionValidator, 'test_invalid_session_id')
    @patch.object(MCPSessionValidator, 'test_valid_session_id')
    @patch.object(MCPSessionValidator, 'test_tools_list_with_session')
    @patch.object(MCPSessionValidator, 'test_tool_call_with_session')
    def test_run_all_tests_some_failures(
        self, 
        mock_tool_call, 
        mock_tools_list, 
        mock_valid, 
        mock_invalid, 
        mock_no_session, 
        mock_initialize
    ):
        """Test running all tests with some failures."""
        # Mock mixed results
        mock_initialize.return_value = "test-session-123"
        mock_no_session.return_value = True
        mock_invalid.return_value = False  # This test fails
        mock_valid.return_value = True
        mock_tools_list.return_value = True
        mock_tool_call.return_value = False  # This test fails
        
        # Call the method
        result = self.validator.run_all_tests()
        
        # Verify results
        self.assertFalse(result)
        
        # Check summary message
        output = self.held_output.getvalue()
        self.assertIn("=== Session Validation Test Results ===", output)
        self.assertIn("Tests passed: 3/5", output)
        self.assertIn("Tests failed: 2/5", output)
        self.assertIn("Session validation FAILED", output)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.http.session_validator.MCPSessionValidator')
    @patch.object(MCPSessionValidator, 'run_all_tests')
    def test_main_success(self, mock_run_all_tests, mock_validator_class, mock_parse_args):
        """Test the main function with successful execution."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.url = "http://example.com/mcp"
        mock_args.debug = False
        mock_args.protocol_version = "2025-03-26"
        mock_parse_args.return_value = mock_args
        
        # Mock validator instance
        mock_validator = mock_validator_class.return_value
        mock_validator.run_all_tests.return_value = True
        
        # Call the main function
        with patch.object(sys, 'argv', ['session_validator.py']):
            result = main()
        
        # Verify results
        self.assertEqual(result, 0)
        mock_validator_class.assert_called_once_with("http://example.com/mcp", False)
        mock_validator.run_all_tests.assert_called_once()

    @patch('argparse.ArgumentParser.parse_args')
    @patch('mcp_testing.http.session_validator.MCPSessionValidator')
    @patch.object(MCPSessionValidator, 'run_all_tests')
    def test_main_failure(self, mock_run_all_tests, mock_validator_class, mock_parse_args):
        """Test the main function with test failures."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.url = "http://example.com/mcp"
        mock_args.debug = True
        mock_args.protocol_version = "2025-03-26"
        mock_parse_args.return_value = mock_args
        
        # Mock validator instance
        mock_validator = mock_validator_class.return_value
        mock_validator.run_all_tests.return_value = False
        
        # Call the main function
        with patch.object(sys, 'argv', ['session_validator.py']):
            result = main()
        
        # Verify results
        self.assertEqual(result, 1)
        mock_validator_class.assert_called_once_with("http://example.com/mcp", True)
        mock_validator.run_all_tests.assert_called_once()


if __name__ == "__main__":
    unittest.main() 