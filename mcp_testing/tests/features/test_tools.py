"""
Tests for MCP tools functionality.

This module tests the tools related functionality for MCP servers.
"""

from typing import Tuple, List, Dict, Any

from mcp_testing.protocols.base import MCPProtocolAdapter


async def test_tools_list(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that tools/list returns a valid response.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        tools = await protocol.get_tools_list()
        
        if not isinstance(tools, list):
            return False, f"Expected tools list to be an array, got {type(tools)}"
            
        # Check that all tools have required properties
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                return False, f"Tool at index {i} is not an object"
                
            if "name" not in tool:
                return False, f"Tool at index {i} is missing required 'name' property"
                
            if "description" not in tool:
                return False, f"Tool at index {i} is missing required 'description' property"
        
        return True, f"Successfully retrieved {len(tools)} tools"
    except Exception as e:
        return False, f"Failed to retrieve tools list: {str(e)}"


async def test_echo_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test the 'echo' tool if available.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if echo tool is available
        echo_tools = [t for t in tools if t.get("name") == "echo"]
        if not echo_tools:
            return True, "Echo tool not available (skipping test)"
            
        # Call the echo tool
        test_message = "Hello, MCP Testing Framework!"
        response = await protocol.call_tool("echo", {"text": test_message})
        
        # Verify the response
        if "content" not in response:
            return False, "Echo tool response is missing 'content' property"
            
        # The server returns {"echo": "message"} inside the content property
        if not isinstance(response["content"], dict) or "echo" not in response["content"]:
            return False, f"Echo tool did not return the expected format. Expected a dict with 'echo' key, got '{response['content']}'"
            
        if response["content"]["echo"] != test_message:
            return False, f"Echo tool did not return the same text. Expected '{test_message}', got '{response['content']['echo']}'"
            
        return True, "Echo tool works correctly"
    except Exception as e:
        return False, f"Failed to test echo tool: {str(e)}"


async def test_add_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test the 'add' tool if available.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if add tool is available
        add_tools = [t for t in tools if t.get("name") == "add"]
        if not add_tools:
            return True, "Add tool not available (skipping test)"
            
        # Call the add tool
        a, b = 42, 58
        response = await protocol.call_tool("add", {"a": a, "b": b})
        
        # Verify the response
        if "content" not in response:
            return False, "Add tool response is missing 'content' property"
            
        # The server returns {"sum": value} inside the content property
        if not isinstance(response["content"], dict) or "sum" not in response["content"]:
            return False, f"Add tool did not return the expected format. Expected a dict with 'sum' key, got '{response['content']}'"
            
        expected = a + b
        if float(response["content"]["sum"]) != expected:
            return False, f"Add tool returned incorrect result. Expected {expected}, got {response['content']['sum']}"
            
        return True, "Add tool works correctly"
    except Exception as e:
        return False, f"Failed to test add tool: {str(e)}"


async def test_invalid_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test calling a non-existent tool.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # Call a tool that doesn't exist
        await protocol.call_tool("non_existent_tool", {})
        
        # If we get here, the server didn't reject the invalid tool
        return False, "Server did not reject call to non-existent tool"
    except Exception as e:
        # This is expected - the server should reject the invalid tool
        return True, f"Server correctly rejected invalid tool call: {str(e)}"


async def test_tool_with_invalid_params(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test calling a tool with invalid parameters.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        # Check if echo tool is available (it's the simplest to test)
        echo_tools = [t for t in tools if t.get("name") == "echo"]
        if not echo_tools:
            # Try add tool as fallback
            add_tools = [t for t in tools if t.get("name") == "add"]
            if not add_tools:
                return True, "No suitable tools available for this test (skipping)"
            
            # Call add tool with wrong parameter names
            await protocol.call_tool("add", {"x": 1, "y": 2})
        else:
            # Call echo tool without required parameter
            await protocol.call_tool("echo", {})
        
        # If we get here, the server didn't reject the invalid parameters
        return False, "Server did not reject tool call with invalid parameters"
    except Exception as e:
        # This is expected - the server should reject the invalid parameters
        return True, f"Server correctly rejected tool call with invalid parameters: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_tools_list, "test_tools_list"),
    (test_echo_tool, "test_echo_tool"),
    (test_add_tool, "test_add_tool"),
    (test_invalid_tool, "test_invalid_tool"),
    (test_tool_with_invalid_params, "test_tool_with_invalid_params"),
] 