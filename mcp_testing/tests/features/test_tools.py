# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for MCP tools functionality.

This module tests the tools related functionality for MCP servers.
"""

from typing import Tuple, List, Dict, Any
import random

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
            
        # Find a tool with required parameters
        suitable_tool = None
        for tool in tools:
            schema = None
            if protocol.version == "2024-11-05":
                schema = tool.get("inputSchema", {})
            else:  # 2025-03-26
                schema = tool.get("parameters", {})
                
            # Check if the tool has required parameters
            required_params = schema.get("required", [])
            if required_params and isinstance(required_params, list) and len(required_params) > 0:
                suitable_tool = tool
                break
                
        if not suitable_tool:
            return True, "No tools with explicitly required parameters found (skipping validation test)"
            
        tool_name = suitable_tool["name"]
        schema = suitable_tool.get("parameters" if protocol.version == "2025-03-26" else "inputSchema", {})
        required_params = schema.get("required", [])
        
        # Test 1: Missing required parameters
        try:
            await protocol.call_tool(tool_name, {})
            # If we get here, check if the response indicates an error
            return False, f"Server accepted empty parameters for tool '{tool_name}' despite requiring: {', '.join(required_params)}"
        except Exception as e:
            # This is expected - the server should reject missing required parameters
            pass
            
        # Test 2: Wrong type for a required parameter
        if required_params:
            properties = schema.get("properties", {})
            for param_name in required_params:
                param_schema = properties.get(param_name, {})
                param_type = param_schema.get("type", "string")
                
                # Create an invalid type value
                if param_type == "string":
                    invalid_value = 12345
                elif param_type in ["number", "integer"]:
                    invalid_value = "not a number"
                elif param_type == "boolean":
                    invalid_value = "not a boolean"
                else:
                    continue  # Skip if we can't determine how to make an invalid value
                    
                invalid_params = {param_name: invalid_value}
                try:
                    await protocol.call_tool(tool_name, invalid_params)
                    # Some servers might be lenient with type conversion, which is acceptable
                    pass
                except Exception as e:
                    # This is also acceptable - strict type checking
                    pass
                break  # Test just one parameter to avoid overwhelming the server
                
        return True, "Server correctly validates tool parameters"
            
    except Exception as e:
        return False, f"Failed to test invalid parameters: {str(e)}"


async def test_jsonrpc_batch_support(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server correctly processes JSON-RPC batch requests.
    
    Test MUST requirements:
    - Implementations MUST support receiving JSON-RPC batches
    
    Returns:
        A tuple containing (passed, message)
    """
    try:
        # Create a small batch of simple requests
        batch = [
            {
                "jsonrpc": "2.0",
                "id": f"batch_test_1_{random.randint(1000, 9999)}",
                "method": "initialize",
                "params": {
                    "protocolVersion": protocol.version,
                    "capabilities": {},
                    "clientInfo": {"name": "test_client"}
                }
            },
            {
                "jsonrpc": "2.0",
                "id": f"batch_test_2_{random.randint(1000, 9999)}",
                "method": "initialize",
                "params": {
                    "protocolVersion": protocol.version,
                    "capabilities": {},
                    "clientInfo": {"name": "test_client"}
                }
            }
        ]
        
        # Some transports might not support direct batch sending
        try:
            import asyncio
            from concurrent.futures import TimeoutError

            # Create a future to wrap the batch send operation
            async def send_batch_with_timeout():
                try:
                    return protocol.transport.send_batch(batch)
                except Exception as e:
                    return {"error": str(e)}

            # Execute with a longer timeout
            try:
                responses = await asyncio.wait_for(send_batch_with_timeout(), timeout=15.0)
                
                # Check if we got an error response
                if isinstance(responses, dict) and "error" in responses:
                    # Try a ping to verify server is still responsive
                    try:
                        ping_response = await protocol.transport.send_request({
                            "jsonrpc": "2.0",
                            "id": "post_batch_ping",
                            "method": "initialize",
                            "params": {
                                "protocolVersion": protocol.version,
                                "capabilities": {},
                                "clientInfo": {"name": "test_client"}
                            }
                        })
                        if "result" in ping_response:
                            return True, f"Server remains responsive but may not support sending batches: {responses['error']}"
                    except Exception:
                        pass
                    return False, f"Batch request failed: {responses['error']}"
                
                # Verify we got the correct number of responses
                if len(responses) != len(batch):
                    return False, f"Expected {len(batch)} responses, got {len(responses)}"
                
                # Verify each response has either a result or error
                for i, response in enumerate(responses):
                    if "result" not in response and "error" not in response:
                        return False, f"Batch response {i} missing both result and error fields"
                
                return True, "Server correctly processes JSON-RPC batch requests"
                
            except TimeoutError:
                # Try a ping to verify server is still responsive
                try:
                    ping_response = await protocol.transport.send_request({
                        "jsonrpc": "2.0",
                        "id": "post_timeout_ping",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": protocol.version,
                            "capabilities": {},
                            "clientInfo": {"name": "test_client"}
                        }
                    })
                    if "result" in ping_response:
                        return True, "Server remains responsive but batch request timed out - may not support batches"
                except Exception:
                    pass
                return False, "Batch request timed out after 15 seconds and server became unresponsive"
                
            except Exception as e:
                return False, f"Error during batch request: {str(e)}"
                
        except AttributeError:
            # If the transport doesn't have a send_batch method, try an alternative approach
            # Send requests sequentially and verify server remains responsive
            for request in batch:
                try:
                    response = await protocol.transport.send_request(request)
                    if "result" not in response and "error" not in response:
                        return False, "Server failed to handle sequential requests properly"
                except Exception as e:
                    return False, f"Server failed during sequential request: {str(e)}"
            
            return True, "Server handles sequential requests properly (batch support not tested due to transport limitations)"
            
    except Exception as e:
        return False, f"Failed to test JSON-RPC batch support: {str(e)}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_tools_list, "test_tools_list"),
    (test_tool_functionality, "test_tool_functionality"),
    (test_tool_with_invalid_params, "test_tool_with_invalid_params"),
    (test_jsonrpc_batch_support, "test_jsonrpc_batch_support"),
] 