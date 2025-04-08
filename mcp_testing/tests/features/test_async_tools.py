# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for MCP async tools functionality (2025-03-26 specific).

This module tests the async tools functionality introduced in the 2025-03-26 version
of the MCP protocol.
"""

import asyncio
from typing import Tuple, List, Dict, Any

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter


async def test_async_tool_support(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server supports async tool calls (2025-03-26 specific).
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    # Skip if not using 2025-03-26 protocol
    if protocol.version != "2025-03-26":
        return True, "Async tool calls only supported in 2025-03-26 (skipping)"
    
    # Check if the protocol adapter is the right type
    if not isinstance(protocol, MCP2025_03_26Adapter):
        return False, "Protocol adapter does not support async tool calls"
    
    # Verify the server capabilities
    tools_capabilities = protocol.server_capabilities.get("tools", {})
    if not tools_capabilities.get("asyncSupported", False):
        return False, "Server does not advertise async tool support in capabilities"
    
    return True, "Server supports async tool calls"


async def test_async_echo_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test an asynchronous echo tool call (2025-03-26 specific).
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    # Skip if not using 2025-03-26 protocol
    if protocol.version != "2025-03-26":
        return True, "Async tool calls only supported in 2025-03-26 (skipping)"
    
    # Check if the protocol adapter is the right type
    if not isinstance(protocol, MCP2025_03_26Adapter):
        return False, "Protocol adapter does not support async tool calls"
    
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if echo tool is available
        echo_tools = [t for t in tools if t.get("name") == "echo"]
        if not echo_tools:
            return True, "Echo tool not available (skipping test)"
        
        # Call the echo tool asynchronously
        test_message = "Hello, Async MCP Testing Framework!"
        response = await protocol.call_tool_async("echo", {"text": test_message})
        
        # Verify the initial response
        if "id" not in response:
            return False, "Async tool call response is missing 'id' property"
        
        tool_call_id = response["id"]
        
        # Wait for the tool call to complete
        result = await protocol.wait_for_tool_completion(tool_call_id, timeout=10.0)
        
        # Verify the result
        if "status" not in result:
            return False, "Async tool result is missing 'status' property"
        
        if result["status"] != "completed":
            return False, f"Async tool call did not complete. Status: {result['status']}"
        
        if "content" not in result:
            return False, "Async tool result is missing 'content' property"
        
        # Check the echo result
        content = result["content"]
        if not isinstance(content, dict) or "echo" not in content:
            return False, f"Echo tool did not return the expected format. Expected a dict with 'echo' key, got '{content}'"
        
        if content["echo"] != test_message:
            return False, f"Echo tool did not return the same text. Expected '{test_message}', got '{content['echo']}'"
        
        return True, "Async echo tool works correctly"
    except Exception as e:
        return False, f"Failed to test async echo tool: {str(e)}"


async def test_async_long_running_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test a long-running asynchronous tool call (2025-03-26 specific).
    
    This test uses the 'sleep' tool if available, which should simulate a
    long-running operation.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    # Skip if not using 2025-03-26 protocol
    if protocol.version != "2025-03-26":
        return True, "Async tool calls only supported in 2025-03-26 (skipping)"
    
    # Check if the protocol adapter is the right type
    if not isinstance(protocol, MCP2025_03_26Adapter):
        return False, "Protocol adapter does not support async tool calls"
    
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if sleep tool is available
        sleep_tools = [t for t in tools if t.get("name") == "sleep"]
        if not sleep_tools:
            return True, "Sleep tool not available (skipping test)"
        
        # Call the sleep tool asynchronously with a short duration
        sleep_duration = 1.0  # 1 second
        response = await protocol.call_tool_async("sleep", {"duration": sleep_duration})
        
        # Verify the initial response
        if "id" not in response:
            return False, "Async tool call response is missing 'id' property"
        
        tool_call_id = response["id"]
        
        # Check the status immediately - should be "running"
        immediate_result = await protocol.get_tool_result(tool_call_id)
        if "status" not in immediate_result:
            return False, "Async tool result is missing 'status' property"
        
        # The tool might already be completed if it's very fast, so accept either "running" or "completed"
        if immediate_result["status"] not in ["running", "completed"]:
            return False, f"Unexpected initial status: {immediate_result['status']}"
        
        # Wait for the tool call to complete
        result = await protocol.wait_for_tool_completion(tool_call_id, timeout=sleep_duration + 5.0)
        
        # Verify the result
        if result["status"] != "completed":
            return False, f"Async tool call did not complete. Status: {result['status']}"
        
        return True, "Async long-running tool works correctly"
    except Exception as e:
        return False, f"Failed to test async long-running tool: {str(e)}"


async def test_async_tool_cancellation(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test cancellation of an asynchronous tool call (2025-03-26 specific).
    
    This test uses the 'sleep' tool if available, which should be cancelable.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    # Skip if not using 2025-03-26 protocol
    if protocol.version != "2025-03-26":
        return True, "Async tool calls only supported in 2025-03-26 (skipping)"
    
    # Check if the protocol adapter is the right type
    if not isinstance(protocol, MCP2025_03_26Adapter):
        return False, "Protocol adapter does not support async tool calls"
    
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if sleep tool is available
        sleep_tools = [t for t in tools if t.get("name") == "sleep"]
        if not sleep_tools:
            return True, "Sleep tool not available (skipping test)"
        
        # Call the sleep tool asynchronously with a longer duration
        sleep_duration = 10.0  # 10 seconds
        response = await protocol.call_tool_async("sleep", {"duration": sleep_duration})
        
        # Verify the initial response
        if "id" not in response:
            return False, "Async tool call response is missing 'id' property"
        
        tool_call_id = response["id"]
        
        # Give the tool a moment to start
        await asyncio.sleep(0.5)
        
        # Cancel the tool call
        cancel_result = await protocol.cancel_tool_call(tool_call_id)
        
        # Verify the cancel result
        if "success" not in cancel_result:
            return False, "Cancel result is missing 'success' property"
        
        if not cancel_result["success"]:
            return False, "Failed to cancel tool call"
        
        # Check the status after cancellation
        try:
            status_result = await protocol.get_tool_result(tool_call_id)
            if "status" not in status_result:
                return False, "Status result is missing 'status' property"
            
            # The status should be "cancelled" or "error"
            if status_result["status"] not in ["cancelled", "error"]:
                return False, f"Unexpected status after cancellation: {status_result['status']}"
                
        except Exception as e:
            # Some servers might not allow querying the status of a cancelled tool call
            # and might return an error, which is acceptable
            pass
        
        return True, "Async tool cancellation works correctly"
    except Exception as e:
        return False, f"Failed to test async tool cancellation: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_async_tool_support, "test_async_tool_support"),
    (test_async_echo_tool, "test_async_echo_tool"),
    (test_async_long_running_tool, "test_async_long_running_tool"),
    (test_async_tool_cancellation, "test_async_tool_cancellation"),
] 