# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
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
                
            # Check schema format based on protocol version
            if protocol.version == "2024-11-05":
                if "inputSchema" not in tool:
                    return False, f"Tool at index {i} is missing required 'inputSchema' property for protocol version 2024-11-05"
            else:  # 2025-03-26
                if "parameters" not in tool:
                    return False, f"Tool at index {i} is missing required 'parameters' property for protocol version 2025-03-26"
        
        return True, f"Successfully retrieved {len(tools)} tools"
    except Exception as e:
        return False, f"Failed to retrieve tools list: {str(e)}"


async def test_tool_functionality(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test the functionality of any available tool.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # First get the tools list
        tools = await protocol.get_tools_list()
        
        if not tools:
            return True, "No tools available to test"
            
        # Test the first available tool
        tool = tools[0]
        tool_name = tool["name"]
        
        # Generate test parameters based on tool schema
        test_params = {}
        schema = None
        
        # Get schema based on protocol version
        if protocol.version == "2024-11-05":
            schema = tool.get("inputSchema", {})
        else:  # 2025-03-26
            schema = tool.get("parameters", {})
            
        if not schema:
            return True, f"Tool {tool_name} does not have a parameter schema"
            
        if "properties" in schema:
            for prop_name, prop_details in schema["properties"].items():
                # Generate a test value based on the property type
                prop_type = prop_details.get("type", "string")
                if prop_type == "string":
                    if prop_name == "url" or "format" in prop_details and prop_details["format"] in ["uri", "url"]:
                        test_params[prop_name] = "https://example.com"
                    else:
                        test_params[prop_name] = "test_value"
                elif prop_type in ["number", "integer"]:
                    test_params[prop_name] = 42
                elif prop_type == "boolean":
                    test_params[prop_name] = True
                elif prop_type == "array":
                    test_params[prop_name] = []
                elif prop_type == "object":
                    test_params[prop_name] = {}
        
        # Call the tool
        response = await protocol.call_tool(tool_name, test_params)
        
        # Basic response validation
        if not isinstance(response, dict):
            return False, f"Tool {tool_name} returned invalid response type: {type(response)}"
            
        # Check response format based on protocol version
        if protocol.version == "2024-11-05":
            # 2024-11-05 just requires content array
            if not isinstance(response.get("content"), list):
                return False, f"Tool {tool_name} response missing required 'content' array"
            for item in response["content"]:
                if not isinstance(item, dict) or "type" not in item or "text" not in item:
                    return False, f"Tool {tool_name} response contains invalid content item"
        else:  # 2025-03-26
            # 2025-03-26 requires content array and isError flag
            if not isinstance(response.get("content"), list) or "isError" not in response:
                return False, f"Tool {tool_name} response missing required fields for protocol version 2025-03-26"
            for item in response["content"]:
                if not isinstance(item, dict) or "type" not in item or "text" not in item:
                    return False, f"Tool {tool_name} response contains invalid content item"
        
        return True, f"Successfully tested tool: {tool_name}"
    except Exception as e:
        return False, f"Failed to test tool functionality: {str(e)}"


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
        
        if not tools:
            return True, "No tools available to test invalid parameters"
            
        # Use the first available tool
        tool = tools[0]
        tool_name = tool["name"]
        
        # Call the tool with empty parameters
        try:
            await protocol.call_tool(tool_name, {})
            # If we get here, the server didn't reject the invalid parameters
            return False, "Server did not reject tool call with invalid parameters"
        except Exception as e:
            # This is expected - the server should reject the invalid parameters
            return True, f"Server correctly rejected tool call with invalid parameters: {str(e)}"
            
    except Exception as e:
        return False, f"Failed to test invalid parameters: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_tools_list, "test_tools_list"),
    (test_tool_functionality, "test_tool_functionality"),
    (test_tool_with_invalid_params, "test_tool_with_invalid_params"),
] 