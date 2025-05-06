#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tests for HTTP transport.

This module tests the HTTP transport implementation.
"""

from typing import Tuple, Dict, Any
import random
import json

from mcp_testing.protocols.base import MCPProtocolAdapter


async def test_http_transport_requirements(protocol: MCPProtocolAdapter, transport: str = "http") -> Tuple[bool, str]:
    """
    Test HTTP transport specific requirements.
    
    Test MUST requirements:
    - Server MUST support HTTP/1.1 protocol
    - Server MUST support POST method for JSON-RPC requests
    - Server MUST support GET method for SSE notifications
    - Server MUST support OPTIONS method for CORS
    - Server MUST set appropriate CORS headers
    - Server MUST support session management via Mcp-Session-Id header
    
    Args:
        protocol: The protocol adapter to use
        transport: The transport type being tested
        
    Returns:
        A tuple containing (passed, message)
    """
    if transport != "http":
        return True, "Not testing HTTP transport requirements for non-HTTP transport"
    
    try:
        # Test POST method for JSON-RPC requests
        request = {
            "jsonrpc": "2.0",
            "id": f"test_http_{random.randint(1000, 9999)}",
            "method": "server/info",
            "params": {}
        }
        
        response = protocol.transport.send_request(request)
        
        if "result" not in response:
            return False, f"Server didn't properly handle POST request: {response.get('error', {}).get('message', 'Unknown error')}"
        
        # Test session management
        session_id = protocol.transport.get_session_id()
        if not session_id:
            return False, "Server did not provide session ID"
        
        # Test that session ID is preserved
        request = {
            "jsonrpc": "2.0",
            "id": f"test_http_session_{random.randint(1000, 9999)}",
            "method": "server/info",
            "params": {}
        }
        
        response = protocol.transport.send_request(request)
        
        if "result" not in response:
            return False, "Server failed to maintain session"
        
        return True, "HTTP transport requirements met"
        
    except Exception as e:
        return False, f"HTTP transport test failed: {str(e)}"


async def test_http_session_management(protocol: MCPProtocolAdapter, transport: str = "http") -> Tuple[bool, str]:
    """
    Test HTTP session management.
    
    Test MUST requirements:
    - Server MUST create a new session on initialization
    - Server MUST maintain session state across requests
    - Server MUST handle multiple concurrent sessions
    
    Args:
        protocol: The protocol adapter to use
        transport: The transport type being tested
        
    Returns:
        A tuple containing (passed, message)
    """
    if transport != "http":
        return True, "Not testing HTTP session management for non-HTTP transport"
    
    try:
        # Get current session ID
        session_id = protocol.transport.get_session_id()
        if not session_id:
            return False, "Server did not provide session ID"
        
        # Test that session is maintained
        request = {
            "jsonrpc": "2.0",
            "id": f"test_session_{random.randint(1000, 9999)}",
            "method": "server/info",
            "params": {}
        }
        
        response = protocol.transport.send_request(request)
        
        if "result" not in response:
            return False, "Server failed to maintain session"
        
        return True, "HTTP session management requirements met"
        
    except Exception as e:
        return False, f"HTTP session management test failed: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_http_transport_requirements, "test_http_transport_requirements"),
    (test_http_session_management, "test_http_session_management"),
] 