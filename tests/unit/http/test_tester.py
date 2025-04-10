#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the HTTP Tester module
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import requests
from io import StringIO
import sys

from mcp_testing.http.tester import MCPHttpTester


class TestMCPHttpTester(unittest.TestCase):
    """Tests for the MCPHttpTester class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.tester = MCPHttpTester("http://localhost:9000/mcp", debug=True)
        
        # Capture stdout for testing log output
        self.stdout_backup = sys.stdout
        sys.stdout = StringIO()
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore stdout
        sys.stdout = self.stdout_backup
    
    def test_init(self):
        """Test initialization of the tester."""
        tester = MCPHttpTester("http://example.com:8080/mcp/v1", debug=True)
        
        self.assertEqual(tester.url, "http://example.com:8080/mcp/v1")
        self.assertEqual(tester.host, "example.com:8080")
        self.assertEqual(tester.path, "/mcp/v1")
        self.assertTrue(tester.debug)
        self.assertEqual(tester.protocol_version, "2025-03-26")
        self.assertIsNotNone(tester.request_session)
        
        # Check that headers are set correctly
        headers = tester.request_session.headers
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(headers.get("Accept"), "application/json, text/event-stream")
        
        # Check log output
        output = sys.stdout.getvalue()
        self.assertIn("MCP HTTP Tester initialized for http://example.com:8080/mcp/v1", output)
        self.assertIn("Host: example.com:8080, Path: /mcp/v1", output)
    
    def test_log(self):
        """Test the log method."""
        self.tester.log("Test message")
        
        output = sys.stdout.getvalue()
        self.assertIn("[DEBUG] Test message", output)
        
        # Test without debug
        sys.stdout = StringIO()  # Reset capture
        tester = MCPHttpTester("http://localhost:9000/mcp", debug=False)
        tester.log("This should not be logged")
        
        output = sys.stdout.getvalue()
        self.assertNotIn("This should not be logged", output)
    
    @patch('requests.Session.post')
    def test_send_request(self, mock_post):
        """Test the send_request method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1234",
            "result": {"message": "success"}
        }
        mock_post.return_value = mock_response
        
        # Call method
        status, headers, body = self.tester.send_request("test_method", {"param": "value"})
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(headers, {'Content-Type': 'application/json'})
        self.assertEqual(body, {"jsonrpc": "2.0", "id": "1234", "result": {"message": "success"}})
        
        # Verify request - note we don't check 'url' since it's the first positional arg
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://localhost:9000/mcp")  # first positional arg is the URL
        self.assertEqual(kwargs['json']['method'], "test_method")
        self.assertEqual(kwargs['json']['params'], {"param": "value"})
        self.assertEqual(kwargs['json']['jsonrpc'], "2.0")
        self.assertIn('id', kwargs['json'])
    
    @patch('requests.Session.post')
    def test_send_request_with_session_id(self, mock_post):
        """Test send_request with a session ID."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": {}}
        mock_post.return_value = mock_response
        
        # Set session ID
        self.tester.session_id = "test-session-id"
        
        # Call method
        self.tester.send_request("test_method")
        
        # Verify session header was added
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['headers'].get('Mcp-Session-Id'), "test-session-id")
    
    @patch.object(MCPHttpTester, 'send_request')
    def test_send_request_save_session_id(self, mock_send_request):
        """Test that send_request captures session ID from initialize response."""
        # Setup mock response for initialize with capitalized header name
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Mcp-Session-Id': 'new-session-id'}  # Capital M in Mcp
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": {}}
        mock_send_request.return_value = (200, mock_response.headers, mock_response.json())
        
        # Call initialize method
        self.tester.send_request("initialize")
        
        # Verify session ID was captured despite case differences
        self.assertEqual(self.tester.session_id, "new-session-id")
        
        # Test with lowercase header
        mock_response.headers = {'mcp-session-id': 'lowercase-session-id'}
        mock_send_request.return_value = (200, mock_response.headers, mock_response.json())
        
        # Call initialize method
        self.tester.session_id = None
        self.tester.send_request("initialize")
        
        # Verify session ID was captured
        self.assertEqual(self.tester.session_id, "lowercase-session-id")

    @patch('requests.options')
    def test_options_request_success(self, mock_options):
        """Test the options_request method with successful response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'POST, OPTIONS',
            'access-control-allow-headers': 'Content-Type, Mcp-Session-Id'
        }
        mock_options.return_value = mock_response
        
        # Redirect stdout for testing output
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Call method
            result = self.tester.options_request()
            
            # Verify result
            self.assertTrue(result)
            
            # Verify output messages
            output = sys.stdout.getvalue()
            self.assertIn("OPTIONS request successful", output)
            self.assertIn("All required CORS headers present", output)
        finally:
            # Restore stdout
            sys.stdout = original_stdout
    
    @patch('requests.options')
    def test_options_request_missing_headers(self, mock_options):
        """Test the options_request method with missing CORS headers."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No CORS headers
        mock_options.return_value = mock_response
        
        # Redirect stdout for testing output
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Call method
            result = self.tester.options_request()
            
            # Verify result (should still return True even with issues)
            self.assertTrue(result)
            
            # Verify output messages
            output = sys.stdout.getvalue()
            self.assertIn("OPTIONS request successful", output)
            self.assertIn("WARNING: Missing CORS headers", output)
        finally:
            # Restore stdout
            sys.stdout = original_stdout
    
    @patch('requests.options')
    def test_options_request_exception(self, mock_options):
        """Test the options_request method with an exception."""
        # Setup mock to raise exception
        mock_options.side_effect = requests.RequestException("Connection error")
        
        # Redirect stdout for testing output
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Call method
            result = self.tester.options_request()
            
            # Verify result (should still return True despite exception)
            self.assertTrue(result)
            
            # Verify output messages
            output = sys.stdout.getvalue()
            self.assertIn("WARNING: OPTIONS request failed with exception", output)
            self.assertIn("Connection error", output)
            self.assertIn("This may not be critical", output)
        finally:
            # Restore stdout
            sys.stdout = original_stdout
    
    @patch.object(MCPHttpTester, 'send_request')
    @patch.object(MCPHttpTester, 'reset_server')
    def test_initialize_already_initialized(self, mock_reset_server, mock_send_request):
        """Test initialization when server is already initialized."""
        # Setup return values for the mocks
        # First call: Error saying server is already initialized
        error_response = {
            "jsonrpc": "2.0", 
            "id": "test-id", 
            "error": {
                "code": -32803, 
                "message": "Server already initialized"
            }
        }
        # Second call: Successful initialization after reset
        success_response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "Test Server"},
                "capabilities": {}
            }
        }
        
        # Configure mocks
        mock_send_request.side_effect = [
            (200, {}, error_response),  # First call: already initialized error
            (200, {"mcp-session-id": "new-session-id"}, success_response)  # Second call: successful init after reset
        ]
        mock_reset_server.return_value = True  # Reset is successful
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(self.tester.session_id, "new-session-id")
        self.assertTrue(self.tester.initialized)
        
        # Verify reset_server was called
        mock_reset_server.assert_called_once()
        
        # Verify send_request was called twice
        self.assertEqual(mock_send_request.call_count, 2)

    @patch.object(MCPHttpTester, 'send_request')
    @patch.object(MCPHttpTester, 'reset_server')
    def test_initialize_already_initialized_reset_fails(self, mock_reset_server, mock_send_request):
        """Test initialization when server is already initialized but reset fails."""
        # First response: already initialized error
        error_response = {
            "jsonrpc": "2.0", 
            "id": "test-id", 
            "error": {
                "code": -32803, 
                "message": "Server already initialized"
            }
        }
        mock_send_request.return_value = (200, {}, error_response)
        
        # Reset fails
        mock_reset_server.return_value = False
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)
        self.assertFalse(self.tester.initialized)
        
        # Verify reset_server was called
        mock_reset_server.assert_called_once()
        
        # Verify send_request was called once (not twice because reset failed)
        mock_send_request.assert_called_once()

    @patch.object(MCPHttpTester, 'send_request')
    @patch.object(MCPHttpTester, 'reset_server')
    def test_initialize_already_initialized_still_initialized_after_reset(self, mock_reset_server, mock_send_request):
        """Test initialization when server is still already initialized after reset."""
        # Setup both calls to return already initialized error
        error_response = {
            "jsonrpc": "2.0", 
            "id": "test-id", 
            "error": {
                "code": -32803, 
                "message": "Server already initialized"
            }
        }
        mock_send_request.side_effect = [(200, {}, error_response), (200, {}, error_response)]
        
        # Reset succeeds but server is still in initialized state
        mock_reset_server.return_value = True
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)  # Should fail as we couldn't initialize after reset
        self.assertFalse(self.tester.initialized)
        
        # Verify reset_server was called
        mock_reset_server.assert_called_once()
        
        # Verify send_request was called twice
        self.assertEqual(mock_send_request.call_count, 2)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_with_session_id_in_body(self, mock_send_request):
        """Test initialization with session ID in different places of the response body."""
        # Test case 1: Standard sessionId in result
        body_response1 = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "sessionId": "body-session-id",
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "Test Server"},
                "capabilities": {}
            }
        }
        mock_send_request.return_value = (200, {}, body_response1)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(self.tester.session_id, "body-session-id")
        self.assertTrue(self.tester.initialized)
        
        # Reset the tester's state
        self.tester.session_id = None
        self.tester.initialized = False
        
        # Test case 2: Nested session object in result
        body_response2 = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "session": {
                    "id": "nested-session-id"
                },
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "Test Server"},
                "capabilities": {}
            }
        }
        mock_send_request.return_value = (200, {}, body_response2)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(self.tester.session_id, "nested-session-id")
        self.assertTrue(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_no_session_id(self, mock_send_request):
        """Test initialization with no session ID."""
        # Mock response with no session ID
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "Test Server"},
                "capabilities": {}
            }
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertTrue(result)
        self.assertIsNone(self.tester.session_id)  # No dummy session ID anymore
        self.assertTrue(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_error_response(self, mock_send_request):
        """Test initialization with error response."""
        # Mock response with error
        error_response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {"code": -32600, "message": "Invalid request"}
        }
        mock_send_request.return_value = (400, {}, error_response)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)
        self.assertIsNone(self.tester.session_id)
        self.assertFalse(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_missing_result(self, mock_send_request):
        """Test initialization with missing result field."""
        # Mock response with missing result
        response = {
            "jsonrpc": "2.0",
            "id": "test-id"
            # No result field
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)
        self.assertFalse(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_missing_protocol_version(self, mock_send_request):
        """Test initialization with missing protocol version."""
        # Mock response with missing protocol version
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "serverInfo": {"name": "Test Server"},
                "capabilities": {}
                # No protocolVersion field
            }
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)
        self.assertFalse(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_initialize_exception(self, mock_send_request):
        """Test initialization with exception."""
        # Mock send_request to raise exception
        mock_send_request.side_effect = Exception("Test exception")
        
        # Call method
        result = self.tester.initialize()
        
        # Verify result
        self.assertFalse(result)
        self.assertFalse(self.tester.initialized)

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_success(self, mock_send_request):
        """Test the list_tools method with a successful response."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock response with tools
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {
                "tools": [
                    {"name": "echo", "description": "Echo a message"},
                    {"name": "add", "description": "Add two numbers"}
                ]
            }
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(len(self.tester.available_tools), 2)
        self.assertEqual(self.tester.available_tools[0]["name"], "echo")
        self.assertEqual(self.tester.available_tools[1]["name"], "add")
        
        # Verify request
        mock_send_request.assert_called_with("tools/list")

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_not_initialized(self, mock_send_request):
        """Test the list_tools method when server is not initialized."""
        # Set initialized flag to False
        self.tester.initialized = False
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertFalse(result)
        self.assertFalse(hasattr(self.tester, 'available_tools'))
        
        # Verify send_request was not called
        mock_send_request.assert_not_called()

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_error_status(self, mock_send_request):
        """Test the list_tools method with an error status code."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock response with error status
        mock_send_request.return_value = (400, {}, {"error": "Bad request"})
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify request
        mock_send_request.assert_called_with("tools/list")

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_non_json_response(self, mock_send_request):
        """Test the list_tools method with a non-JSON response."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock response with non-JSON body
        mock_send_request.return_value = (200, {}, "Not a JSON object")
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertFalse(result)

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_missing_result(self, mock_send_request):
        """Test the list_tools method with missing result field."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock response with missing result
        response = {
            "jsonrpc": "2.0",
            "id": "test-id"
            # No result field
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertFalse(result)

    @patch.object(MCPHttpTester, 'send_request')
    def test_list_tools_missing_tools(self, mock_send_request):
        """Test the list_tools method with missing tools array."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock response with missing tools array
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {}  # No tools field
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method
        result = self.tester.list_tools()
        
        # Verify result
        self.assertFalse(result)

    def test_get_tool_by_name_found(self):
        """Test the get_tool_by_name method with a found tool."""
        # Set available_tools
        self.tester.available_tools = [
            {"name": "echo", "description": "Echo a message"},
            {"name": "add", "description": "Add two numbers"}
        ]
        
        # Call method
        tool = self.tester.get_tool_by_name("echo")
        
        # Verify result
        self.assertIsNotNone(tool)
        self.assertEqual(tool["name"], "echo")
        self.assertEqual(tool["description"], "Echo a message")

    def test_get_tool_by_name_not_found(self):
        """Test the get_tool_by_name method with a not found tool."""
        # Set available_tools
        self.tester.available_tools = [
            {"name": "echo", "description": "Echo a message"},
            {"name": "add", "description": "Add two numbers"}
        ]
        
        # Call method
        tool = self.tester.get_tool_by_name("unknown_tool")
        
        # Verify result
        self.assertIsNone(tool)

    def test_get_tool_by_name_no_tools_listed(self):
        """Test the get_tool_by_name method when no tools have been listed."""
        # Don't set available_tools
        
        # Call method
        tool = self.tester.get_tool_by_name("echo")
        
        # Verify result
        self.assertIsNone(tool)

    @patch.object(MCPHttpTester, 'get_tool_by_name')
    @patch.object(MCPHttpTester, 'send_request')
    def test_test_tool_success(self, mock_send_request, mock_get_tool):
        """Test the test_tool method with a successful response."""
        # Set initialized flag
        self.tester.initialized = True
        self.tester.session_id = "test-session-id"
        
        # Mock get_tool_by_name to return a tool
        tool_definition = {
            "name": "echo", 
            "description": "Echo a message",
            "parameters": {
                "message": {
                    "type": "string",
                    "description": "Message to echo"
                }
            }
        }
        mock_get_tool.return_value = tool_definition
        
        # Mock send_request response
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"message": "Hello, World!"}
        }
        mock_send_request.return_value = (200, {}, response)
        
        # Call method with test parameters
        test_params = {"message": "Hello, World!"}
        result = self.tester.test_tool("echo", test_params)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify request
        mock_get_tool.assert_called_with("echo")
        mock_send_request.assert_called_once()
        args, kwargs = mock_send_request.call_args
        self.assertEqual(args[0], "tools/call")
        
        # Check that the second positional argument contains the expected parameters
        # The implementation passes params directly as a positional argument, not as a kwarg
        self.assertEqual(args[1], {
            "name": "echo",
            "parameters": {"message": "Hello, World!"}
        })

    @patch.object(MCPHttpTester, 'get_tool_by_name')
    def test_test_tool_not_initialized(self, mock_get_tool):
        """Test the test_tool method when server is not initialized."""
        # Set initialized flag to False
        self.tester.initialized = False
        
        # Call method
        result = self.tester.test_tool("echo")
        
        # Verify result
        self.assertFalse(result)
        
        # Verify get_tool_by_name was not called
        mock_get_tool.assert_not_called()

    @patch.object(MCPHttpTester, 'get_tool_by_name')
    def test_test_tool_not_found(self, mock_get_tool):
        """Test the test_tool method when tool is not found."""
        # Set initialized flag
        self.tester.initialized = True
        
        # Mock get_tool_by_name to return None (tool not found)
        mock_get_tool.return_value = None
        
        # Call method
        result = self.tester.test_tool("unknown_tool")
        
        # Verify result (note: the implementation returns True when a tool is not found)
        self.assertTrue(result)
        
        # Verify get_tool_by_name was called
        mock_get_tool.assert_called_with("unknown_tool")

    @patch.object(MCPHttpTester, 'test_tool')
    @patch.object(MCPHttpTester, 'send_request')
    def test_test_available_tools_success(self, mock_send_request, mock_test_tool):
        """Test the test_available_tools method with successful tests."""
        # Set initialized flag and available_tools
        self.tester.initialized = True
        self.tester.available_tools = [
            {"name": "echo", "description": "Echo a message"},
            {"name": "add", "description": "Add two numbers"},
            {"name": "sleep", "description": "Sleep for seconds"}
        ]
        self.tester.protocol_version = "2025-03-26"
        
        # Make all tool tests succeed
        mock_test_tool.return_value = True
        
        # Call method
        result = self.tester.test_available_tools()
        
        # Verify result
        self.assertTrue(result)
        
        # Verify test_tool was called for each tool except sleep
        self.assertEqual(mock_test_tool.call_count, 2)
        mock_test_tool.assert_any_call("echo")
        mock_test_tool.assert_any_call("add")
        
        # Verify send_request was not called directly
        mock_send_request.assert_not_called()

    @patch.object(MCPHttpTester, 'test_tool')
    def test_test_available_tools_no_tools_listed(self, mock_test_tool):
        """Test the test_available_tools method when no tools have been listed."""
        # Set initialized flag but no available_tools
        self.tester.initialized = True
        
        # Call method
        result = self.tester.test_available_tools()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify test_tool was not called
        mock_test_tool.assert_not_called()

    @patch.object(MCPHttpTester, 'test_tool')
    def test_test_available_tools_with_failures(self, mock_test_tool):
        """Test the test_available_tools method with some tool failures."""
        # Set initialized flag and available_tools
        self.tester.initialized = True
        self.tester.available_tools = [
            {"name": "echo", "description": "Echo a message"},
            {"name": "add", "description": "Add two numbers"},
            {"name": "subtract", "description": "Subtract two numbers"}
        ]
        self.tester.protocol_version = "2024-11-05"  # Use older protocol to avoid skipping sleep
        
        # Make some tool tests fail
        mock_test_tool.side_effect = [True, False, True]
        
        # Call method
        result = self.tester.test_available_tools()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify test_tool was called for each tool
        self.assertEqual(mock_test_tool.call_count, 3)
        mock_test_tool.assert_any_call("echo")
        mock_test_tool.assert_any_call("add")
        mock_test_tool.assert_any_call("subtract")

    @patch.object(MCPHttpTester, 'send_request')
    def test_test_async_sleep_tool_success(self, mock_send_request):
        """Test the test_async_sleep_tool method with successful execution."""
        # Set initialized flag
        self.tester.initialized = True
        self.tester.protocol_version = "2025-03-26"
        
        # Mock responses for call-async and result
        mock_send_request.side_effect = [
            # First call: tools/call-async response
            (200, {}, {
                "jsonrpc": "2.0", 
                "id": "test-id", 
                "result": {"id": "task-123"}
            }),
            # Second call: tools/result response (success)
            (200, {}, {
                "jsonrpc": "2.0", 
                "id": "test-id", 
                "result": {"status": "completed", "result": {}}
            })
        ]
        
        # Call method
        result = self.tester.test_async_sleep_tool()
        
        # Verify result
        self.assertTrue(result)
        
        # Verify request calls
        self.assertEqual(mock_send_request.call_count, 2)
        first_call_args = mock_send_request.call_args_list[0][0]
        self.assertEqual(first_call_args[0], "tools/call-async")
        self.assertEqual(first_call_args[1]["name"], "sleep")
        self.assertEqual(first_call_args[1]["parameters"]["seconds"], 3)
        
        second_call_args = mock_send_request.call_args_list[1][0]
        self.assertEqual(second_call_args[0], "tools/result")
        self.assertEqual(second_call_args[1]["id"], "task-123")

    @patch.object(MCPHttpTester, 'send_request')
    def test_test_async_sleep_tool_not_initialized(self, mock_send_request):
        """Test the test_async_sleep_tool method when not initialized."""
        # Set initialized flag to False
        self.tester.initialized = False
        
        # Call method
        result = self.tester.test_async_sleep_tool()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify send_request was not called
        mock_send_request.assert_not_called()

    @patch.object(MCPHttpTester, 'send_request')
    def test_test_async_sleep_tool_old_protocol(self, mock_send_request):
        """Test the test_async_sleep_tool method with old protocol version."""
        # Set initialized flag but old protocol
        self.tester.initialized = True
        self.tester.protocol_version = "2024-11-05"
        
        # Call method
        result = self.tester.test_async_sleep_tool()
        
        # Verify result (should skip the test)
        self.assertTrue(result)
        
        # Verify send_request was not called
        mock_send_request.assert_not_called()

    @patch.object(MCPHttpTester, 'send_request')
    def test_test_async_sleep_tool_call_error(self, mock_send_request):
        """Test the test_async_sleep_tool method with error on call."""
        # Set initialized flag
        self.tester.initialized = True
        self.tester.protocol_version = "2025-03-26"
        
        # Mock error response
        mock_send_request.return_value = (400, {}, {"error": "Bad request"})
        
        # Call method
        result = self.tester.test_async_sleep_tool()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify request was called
        mock_send_request.assert_called_once()
        args = mock_send_request.call_args[0]
        self.assertEqual(args[0], "tools/call-async")

    @patch.object(MCPHttpTester, 'send_request')
    def test_test_async_sleep_tool_timeout(self, mock_send_request):
        """Test the test_async_sleep_tool method with task timeout."""
        # Set initialized flag
        self.tester.initialized = True
        self.tester.protocol_version = "2025-03-26"
        
        # First response: successful call-async
        call_response = {
            "jsonrpc": "2.0", 
            "id": "test-id", 
            "result": {"id": "task-123"}
        }
        
        # Subsequent responses: running status (never completes)
        result_response = {
            "jsonrpc": "2.0", 
            "id": "test-id", 
            "result": {"status": "running"}
        }
        
        # Set up mock to return different responses
        mock_responses = [
            (200, {}, call_response),  # First call: tools/call-async
        ]
        # Add 10 "running" responses for result checks
        mock_responses.extend([(200, {}, result_response) for _ in range(10)])
        
        mock_send_request.side_effect = mock_responses
        
        # Call method
        result = self.tester.test_async_sleep_tool()
        
        # Verify result
        self.assertFalse(result)
        
        # Verify all requests were made
        self.assertEqual(mock_send_request.call_count, 11)  # 1 call-async + 10 result checks

    @patch('requests.Session')
    def test_reset_server_success(self, mock_session):
        """Test the reset_server method with a successful response."""
        # Mock successful session
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "test", "result": {}}
        mock_session_instance.post.return_value = mock_response
        
        # Call method
        result = self.tester.reset_server()
        
        # Verify result
        self.assertTrue(result)
        
        # Verify post request was made correctly
        mock_session_instance.post.assert_called_once()
        args, kwargs = mock_session_instance.post.call_args
        self.assertEqual(args[0], "http://localhost:9000/mcp")
        self.assertIn("json", kwargs)
        self.assertEqual(kwargs["json"]["method"], "shutdown")

    @patch('requests.Session')
    def test_reset_server_error(self, mock_session):
        """Test the reset_server method with an error response."""
        # Mock error response
        mock_session_instance = mock_session.return_value
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_session_instance.post.return_value = mock_response
    
        # Call method
        result = self.tester.reset_server()
    
        # Verify result - the method always returns True regardless of status code
        self.assertTrue(result)
        
        # Verify that post was called with the right parameters
        mock_session_instance.post.assert_called_once()
        called_args = mock_session_instance.post.call_args[0]
        self.assertEqual(called_args[0], self.tester.url)

    @patch('requests.Session')
    def test_reset_server_exception(self, mock_session):
        """Test the reset_server method with an exception."""
        # Mock exception
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.side_effect = Exception("Test exception")
        
        # Call method
        result = self.tester.reset_server()
        
        # Verify result
        self.assertFalse(result)

    @patch('requests.Session.post')
    def test_reset_server_no_session_success(self, mock_post):
        """Test reset_server method success without session ID."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "test", "result": {}}
        mock_post.return_value = mock_response
        
        # Set debug for output testing
        self.tester.debug = True
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Call method
            result = self.tester.reset_server()
            
            # Verify result
            self.assertTrue(result)
            
            # Verify the log output
            output = sys.stdout.getvalue()
            self.assertIn("Sending shutdown request without session ID", output)
            
            # Verify post request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "http://localhost:9000/mcp")
            self.assertIn("json", kwargs)
            self.assertEqual(kwargs["json"]["method"], "shutdown")
            self.assertNotIn("headers", kwargs)  # No headers because no session ID
        finally:
            sys.stdout = original_stdout
            
        # Verify the session state was reset
        self.assertIsNone(self.tester.session_id)
        self.assertFalse(self.tester.initialized)

    @patch('requests.Session.post')
    def test_reset_server_with_session_success(self, mock_post):
        """Test reset_server method success with session ID."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "test", "result": {}}
        mock_post.return_value = mock_response
        
        # Set a session ID
        self.tester.session_id = "test-session-id"
        self.tester.initialized = True
        
        # Set debug for output testing
        self.tester.debug = True
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # First call without session ID fails
            mock_post.side_effect = [
                Exception("First call fails"),  # First call without session fails
                mock_response  # Second call with session succeeds
            ]
            
            # Call method
            result = self.tester.reset_server()
            
            # Verify result
            self.assertTrue(result)
            
            # Verify the log output
            output = sys.stdout.getvalue()
            self.assertIn("Sending shutdown request with existing session ID", output)
            
            # Verify post requests were attempted
            self.assertEqual(mock_post.call_count, 2)
            
            # Check the second call had the session header
            _, kwargs = mock_post.call_args_list[1]
            self.assertIn("headers", kwargs)
            self.assertEqual(kwargs["headers"]["Mcp-Session-Id"], "test-session-id")
        finally:
            sys.stdout = original_stdout
            
        # Verify the session state was reset
        self.assertIsNone(self.tester.session_id)
        self.assertFalse(self.tester.initialized)

    @patch('requests.Session.post')
    def test_reset_server_both_methods_fail(self, mock_post):
        """Test reset_server method when both approaches fail but we continue anyway."""
        # Set a session ID
        self.tester.session_id = "test-session-id"
        self.tester.initialized = True
        
        # Both calls fail
        mock_post.side_effect = Exception("Test exception")
        
        # Call method
        result = self.tester.reset_server()
        
        # Verify result - we still return True to allow testing to continue
        self.assertTrue(result)
        
        # Verify the session state was reset anyway
        self.assertIsNone(self.tester.session_id)


if __name__ == '__main__':
    unittest.main()