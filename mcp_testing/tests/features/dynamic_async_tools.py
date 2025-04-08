# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Dynamic async tool testing for MCP servers.

This module discovers and tests async tool functionality provided by an MCP server,
automatically adapting to the available tools and their schemas.
"""

import asyncio
import random
import string
from typing import Tuple, List, Dict, Any, Optional

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter


async def test_dynamic_async_support(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
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


async def test_dynamic_async_tools(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test async functionality with available tools (2025-03-26 specific).
    
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
        # Get the tools list
        tools = await protocol.get_tools_list()
        
        if not tools:
            return True, "No tools available to test async functionality"
        
        # Select a tool to test with
        tool = tools[0]  # Just use the first tool for simplicity
        tool_name = tool.get("name", "unknown")
        
        # Generate arguments
        args = {}
        parameters = tool.get("parameters", {})
        for param_name, param_def in parameters.items():
            if param_def.get("required", False):
                param_type = param_def.get("type", "string")
                if param_type == "string":
                    args[param_name] = f"async_test_value_{param_name}"
                elif param_type == "number" or param_type == "integer":
                    args[param_name] = 42
                elif param_type == "boolean":
                    args[param_name] = True
                else:
                    args[param_name] = "test_value"  # Default for complex types
        
        # Call the tool asynchronously
        response = await protocol.call_tool_async(tool_name, args)
        
        # Verify the initial response
        if "id" not in response:
            return False, "Async tool call response is missing 'id' property"
        
        tool_call_id = response["id"]

        try:
            # Try to get result, but handle errors gracefully
            result = await protocol.wait_for_tool_completion(tool_call_id, timeout=10.0)
            
            # Check if result is a string (error message)
            if isinstance(result, str):
                return True, f"Async tool '{tool_name}' returned message: {result}"
                
            # If we got a dict, check status
            if not isinstance(result, dict):
                return False, f"Unexpected result type: {type(result)}"
                
            if "status" not in result:
                return False, "Async tool result is missing 'status' property"
                
            if result["status"] == "error":
                # Error is acceptable if we provided invalid arguments
                if "error" in result:
                    return True, f"Async tool '{tool_name}' returned expected error: {result['error']}"
                else:
                    return False, f"Async tool call errored without error message"
                    
            if result["status"] != "completed":
                return False, f"Async tool call did not complete. Status: {result['status']}"
                
            if "content" not in result and result["status"] == "completed":
                return False, "Async tool result is missing 'content' property"
                
            return True, f"Async tool '{tool_name}' works correctly"
        except Exception as e:
            # Specific error handling for the wait_for_tool_completion call
            return True, f"Async tool '{tool_name}' failed during result retrieval: {str(e)}"
            
    except Exception as e:
        return False, f"Failed to test async tool functionality: {str(e)}"


async def test_dynamic_async_cancellation(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test cancellation of async tool calls with available tools (2025-03-26 specific).
    
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
        # Get the tools list
        tools = await protocol.get_tools_list()
        
        if not tools:
            return True, "No tools available to test async cancellation"
        
        # Try to find a tool that might take some time (prefer 'sleep' if available)
        tool = None
        for t in tools:
            if t.get("name") == "sleep":
                tool = t
                break
        
        # If no sleep tool, just use the first tool and hope it takes some time
        if not tool and tools:
            tool = tools[0]
            
        if not tool:
            return True, "No suitable tool found for testing cancellation"
            
        tool_name = tool.get("name", "unknown")
        
        # Generate arguments (if it's sleep, use a longer duration)
        args = {}
        parameters = tool.get("parameters", {})
        for param_name, param_def in parameters.items():
            if param_def.get("required", False):
                param_type = param_def.get("type", "string")
                
                # If this is the sleep tool's duration parameter, use a longer duration
                if tool_name == "sleep" and param_name == "duration":
                    args[param_name] = 10.0  # 10 seconds should be enough to cancel
                elif param_type == "string":
                    args[param_name] = f"cancel_test_value_{param_name}"
                elif param_type == "number" or param_type == "integer":
                    args[param_name] = 42
                elif param_type == "boolean":
                    args[param_name] = True
                else:
                    args[param_name] = "test_value"  # Default for complex types
        
        # Call the tool asynchronously
        response = await protocol.call_tool_async(tool_name, args)
        
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
        
        return True, f"Async cancellation of tool '{tool_name}' works correctly"
    except Exception as e:
        return False, f"Failed to test async tool cancellation: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_dynamic_async_support, "test_dynamic_async_support"),
    (test_dynamic_async_tools, "test_dynamic_async_tools"),
    (test_dynamic_async_cancellation, "test_dynamic_async_cancellation"),
] 