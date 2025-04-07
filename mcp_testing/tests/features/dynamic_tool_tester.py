"""
Dynamic tool testing for MCP servers.

This module discovers and tests tools provided by an MCP server, automatically
adapting to the available tools and their schemas rather than having hardcoded
expectations.
"""

import json
import random
import string
from typing import Tuple, List, Dict, Any, Optional

from mcp_testing.protocols.base import MCPProtocolAdapter


async def test_dynamic_tool_discovery(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server can provide a list of tools and that they meet basic requirements.
    
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
        valid_tools = []
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                return False, f"Tool at index {i} is not an object"
                
            if "name" not in tool:
                return False, f"Tool at index {i} is missing required 'name' property"
                
            if "description" not in tool:
                return False, f"Tool at index {i} is missing required 'description' property"
            
            # A valid tool has all required properties
            valid_tools.append(tool)
        
        # Store tool information for later tests
        setattr(protocol, "discovered_tools", valid_tools)
        
        return True, f"Successfully discovered {len(tools)} tools"
    except Exception as e:
        return False, f"Failed to discover tools: {str(e)}"


async def test_each_tool(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test each tool provided by the server with appropriate arguments based on its schema.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # Get the discovered tools from the previous test
        tools = getattr(protocol, "discovered_tools", [])
        
        if not tools:
            # Try to get tools if not already done
            tools = await protocol.get_tools_list()
            setattr(protocol, "discovered_tools", tools)
        
        if not tools:
            return True, "No tools available to test"
        
        results = []
        failed_tools = []
        
        for tool in tools:
            tool_name = tool.get("name", "unknown")
            
            # Generate appropriate arguments based on the tool's schema
            try:
                args = generate_arguments_from_schema(tool.get("parameters", {}))
                
                # Call the tool
                try:
                    response = await protocol.call_tool(tool_name, args)
                    
                    # Verify basic response structure
                    if "content" not in response:
                        failed_tools.append((tool_name, "Response missing 'content' property"))
                        continue
                    
                    results.append(f"Tool '{tool_name}' works")
                except Exception as e:
                    error_msg = str(e)
                    
                    # Check if the error is about missing arguments
                    if "Missing required argument" in error_msg or "Missing required arguments" in error_msg:
                        # If we provided empty or partial arguments, this is expected and not a failure
                        if not args or len(args) < len(tool.get("parameters", {})):
                            results.append(f"Tool '{tool_name}' correctly requires arguments")
                        else:
                            failed_tools.append((tool_name, error_msg))
                    else:
                        failed_tools.append((tool_name, error_msg))
            except Exception as e:
                failed_tools.append((tool_name, str(e)))
        
        if failed_tools:
            failed_msg = "; ".join([f"'{name}': {error}" for name, error in failed_tools])
            return False, f"Failed to test {len(failed_tools)} tools: {failed_msg}"
        
        return True, f"Successfully tested {len(results)} tools"
    except Exception as e:
        return False, f"Failed to test tools: {str(e)}"


async def test_invalid_tool_name(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server properly rejects calls to non-existent tools.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # Generate a random tool name that is unlikely to exist
        random_name = "nonexistent_tool_" + ''.join(random.choices(string.ascii_lowercase, k=8))
        
        # Try to call the non-existent tool
        await protocol.call_tool(random_name, {})
        
        # If we get here, the server didn't reject the invalid tool
        return False, f"Server did not reject call to non-existent tool '{random_name}'"
    except Exception as e:
        # This is expected - the server should reject the invalid tool
        return True, f"Server correctly rejected invalid tool call: {str(e)}"


async def test_invalid_tool_arguments(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server properly rejects calls with invalid arguments.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # Get the discovered tools
        tools = getattr(protocol, "discovered_tools", [])
        
        if not tools:
            # Try to get tools if not already done
            tools = await protocol.get_tools_list()
            setattr(protocol, "discovered_tools", tools)
        
        if not tools:
            return True, "No tools available to test invalid arguments"
        
        # Find a tool with required parameters
        suitable_tool = None
        for tool in tools:
            parameters = tool.get("parameters", {})
            if parameters and any(parameters.get(param, {}).get("required", False) for param in parameters):
                suitable_tool = tool
                break
        
        if not suitable_tool:
            # Try the first tool anyway
            suitable_tool = tools[0]
        
        tool_name = suitable_tool.get("name", "unknown")
        
        # Call the tool with empty arguments
        await protocol.call_tool(tool_name, {})
        
        # If we get here and the tool had required parameters, the server didn't reject the invalid args
        parameters = suitable_tool.get("parameters", {})
        required_params = [p for p in parameters if parameters[p].get("required", False)]
        
        if required_params:
            return False, f"Server did not reject call to '{tool_name}' with missing required parameters {required_params}"
        else:
            return True, f"Tool '{tool_name}' doesn't have required parameters, so empty arguments were accepted"
            
    except Exception as e:
        # This is expected if the tool had required parameters
        return True, f"Server correctly rejected tool call with invalid arguments: {str(e)}"


def generate_arguments_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate appropriate arguments based on a tool's parameter schema.
    
    Args:
        schema: The parameter schema for the tool
        
    Returns:
        A dictionary of generated arguments
    """
    args = {}
    
    for param_name, param_def in schema.items():
        # Skip optional parameters sometimes
        if not param_def.get("required", False) and random.random() < 0.5:
            continue
            
        param_type = param_def.get("type", "string")
        
        if param_type == "string":
            args[param_name] = f"test_value_for_{param_name}"
        elif param_type == "number" or param_type == "integer":
            args[param_name] = random.randint(1, 100)
        elif param_type == "boolean":
            args[param_name] = random.choice([True, False])
        elif param_type == "array":
            # Create a small array of simple items
            args[param_name] = ["item1", "item2"]
        elif param_type == "object":
            # Create a simple object with one property
            args[param_name] = {"property": "value"}
    
    return args


# Create a list of all test cases in this module
TEST_CASES = [
    (test_dynamic_tool_discovery, "test_dynamic_tool_discovery"),
    (test_each_tool, "test_each_tool"),
    (test_invalid_tool_name, "test_invalid_tool_name"),
    (test_invalid_tool_arguments, "test_invalid_tool_arguments"),
] 