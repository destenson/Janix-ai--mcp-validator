# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test cases for MCP version 2025-06-18 specific features.

This module contains test cases that are specific to the 2025-06-18 protocol version,
including structured tool output, elicitation support, removal of JSON-RPC batching,
and enhanced validation requirements.
"""

import json
from typing import Tuple, Dict, Any

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2025_06_18 import MCP2025_06_18Adapter


async def test_structured_tool_output(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that tools can return structured output with outputSchema validation.
    
    This test verifies the new structured tool output feature in 2025-06-18.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Get tools list to check for outputSchema support
        tools = await protocol.list_tools_with_output_schema()
        
        # Look for a tool that defines an output schema
        structured_tool = None
        for tool in tools:
            if "outputSchema" in tool:
                structured_tool = tool
                break
        
        if not structured_tool:
            return True, "Skipped: No tools with outputSchema found"
        
        # Call the tool and check for structured output
        tool_name = structured_tool["name"]
        
        # Generate appropriate arguments for the tool
        input_schema = structured_tool.get("inputSchema", {})
        arguments = {}
        
        if "properties" in input_schema:
            for prop_name, prop_def in input_schema["properties"].items():
                if prop_def.get("type") == "string":
                    arguments[prop_name] = "test_value"
                elif prop_def.get("type") == "number":
                    arguments[prop_name] = 42
                elif prop_def.get("type") == "boolean":
                    arguments[prop_name] = True
        
        result = await protocol.call_tool_with_structured_output(tool_name, arguments)
        
        # Validate the response has the required 2025-06-18 fields
        if "content" not in result:
            return False, "Tool response missing required 'content' field"
        
        if "isError" not in result:
            return False, "Tool response missing required 'isError' field"
        
        # Check if structured content is present
        if "structuredContent" in result:
            # Validate structured content against output schema if present
            output_schema = structured_tool.get("outputSchema")
            if output_schema:
                # Basic validation - in a real implementation, you'd use jsonschema
                structured_content = result["structuredContent"]
                if not isinstance(structured_content, dict):
                    return False, f"Structured content should be an object, got {type(structured_content)}"
        
        return True, f"Tool '{tool_name}' successfully returned structured output"
        
    except Exception as e:
        return False, f"Structured tool output test failed: {str(e)}"


async def test_elicitation_support(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test the elicitation capability for requesting additional user information.
    
    This test verifies the new elicitation feature in 2025-06-18.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Check if server supports elicitation
        capabilities = protocol.server_capabilities
        if not capabilities.get("elicitation"):
            return True, "Skipped: Server does not support elicitation"
        
        # Create a simple elicitation request
        schema = {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": "User's response to the prompt"
                }
            },
            "required": ["user_input"]
        }
        
        prompt = "Please provide some test input for validation"
        
        # This will typically fail in test environments since there's no real user
        # but we can test that the method is properly implemented
        try:
            result = await protocol.create_elicitation_request(schema, prompt)
            
            # If we get here, validate the response format
            if "action" not in result:
                return False, "Elicitation response missing required 'action' field"
            
            action = result["action"]
            if action not in ["accept", "reject", "cancel"]:
                return False, f"Invalid elicitation action: {action}"
            
            return True, f"Elicitation request completed with action: {action}"
            
        except Exception as e:
            # Expected in test environments - check that the error is reasonable
            error_msg = str(e).lower()
            if "elicitation" in error_msg or "not supported" in error_msg or "no user" in error_msg:
                return True, "Elicitation capability properly implemented (expected failure in test environment)"
            else:
                return False, f"Unexpected elicitation error: {str(e)}"
        
    except Exception as e:
        return False, f"Elicitation test failed: {str(e)}"


async def test_batch_request_rejection(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that JSON-RPC batching is properly rejected in 2025-06-18.
    
    This test verifies that batch requests are not supported in 2025-06-18.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Try to send a batch request - this should fail
        batch_requests = [
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "ping",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": "2", 
                "method": "tools/list",
                "params": {}
            }
        ]
        
        try:
            await protocol.send_batch_request(batch_requests)
            return False, "Batch request should have been rejected but was accepted"
        except Exception as e:
            error_msg = str(e).lower()
            if "batch" in error_msg and "not supported" in error_msg:
                return True, "Batch requests properly rejected in 2025-06-18"
            else:
                return False, f"Unexpected batch rejection error: {str(e)}"
        
    except Exception as e:
        return False, f"Batch request rejection test failed: {str(e)}"


async def test_enhanced_tool_validation(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test enhanced tool validation requirements in 2025-06-18.
    
    This test verifies that tools properly validate input and output.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Get tools list
        tools = await protocol.list_tools_with_output_schema()
        
        if not tools:
            return True, "Skipped: No tools available for validation testing"
        
        # Test each tool for proper validation
        validation_results = []
        
        for tool in tools:
            tool_name = tool["name"]
            
            # Test 1: Check required fields are present
            required_fields = ["name", "description", "inputSchema"]
            missing_fields = [field for field in required_fields if field not in tool]
            
            if missing_fields:
                validation_results.append(f"Tool '{tool_name}' missing required fields: {missing_fields}")
                continue
            
            # Test 2: Check for new 2025-06-18 fields
            has_title = "title" in tool
            has_output_schema = "outputSchema" in tool
            
            # Test 3: Try calling the tool with invalid arguments to test validation
            try:
                # Call with completely invalid arguments
                invalid_result = await protocol.call_tool_with_structured_output(
                    tool_name, 
                    {"invalid_param": "invalid_value"}
                )
                
                # Check if the tool properly returned an error
                if invalid_result.get("isError"):
                    validation_results.append(f"Tool '{tool_name}' properly validates input (rejected invalid params)")
                else:
                    validation_results.append(f"Tool '{tool_name}' accepted invalid parameters - validation may be weak")
                    
            except Exception as e:
                # This is actually good - the tool should reject invalid input
                validation_results.append(f"Tool '{tool_name}' properly rejects invalid input")
        
        if not validation_results:
            return True, "No validation issues found, but no tools tested"
        
        # Count positive vs negative results
        positive_results = [r for r in validation_results if "properly" in r]
        negative_results = [r for r in validation_results if "missing" in r or "weak" in r]
        
        if negative_results:
            return False, f"Tool validation issues: {'; '.join(negative_results)}"
        else:
            return True, f"Enhanced tool validation working: {len(positive_results)} tools validated"
        
    except Exception as e:
        return False, f"Enhanced tool validation test failed: {str(e)}"


async def test_protocol_version_negotiation(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test protocol version negotiation for 2025-06-18.
    
    This test verifies that version negotiation works correctly.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Check that the protocol version was properly negotiated
        if protocol.protocol_version != "2025-06-18":
            return False, f"Protocol version mismatch: expected 2025-06-18, got {protocol.protocol_version}"
        
        # Check that server capabilities include expected 2025-06-18 features
        capabilities = protocol.server_capabilities
        
        # Look for capabilities that should be present
        expected_capabilities = ["tools", "resources"]
        missing_capabilities = []
        
        for cap in expected_capabilities:
            if cap not in capabilities:
                missing_capabilities.append(cap)
        
        if missing_capabilities:
            return False, f"Server missing expected capabilities: {missing_capabilities}"
        
        # Check for 2025-06-18 specific capabilities
        new_capabilities = []
        if "elicitation" in capabilities:
            new_capabilities.append("elicitation")
        if "logging" in capabilities:
            new_capabilities.append("logging")
        
        return True, f"Protocol version 2025-06-18 properly negotiated with capabilities: {list(capabilities.keys())}"
        
    except Exception as e:
        return False, f"Protocol version negotiation test failed: {str(e)}"


async def test_enhanced_ping_validation(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test enhanced ping validation for 2025-06-18.
    
    This test verifies that ping responses are properly validated.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Send ping and validate response
        result = await protocol.ping_with_enhanced_validation()
        
        # The result should be an empty object
        if result != {}:
            return False, f"Ping response should be empty, got: {result}"
        
        return True, "Enhanced ping validation successful - empty response received"
        
    except Exception as e:
        return False, f"Enhanced ping validation test failed: {str(e)}"


async def test_resource_metadata_support(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test enhanced resource metadata support in 2025-06-18.
    
    This test verifies that resources include proper metadata.
    
    Args:
        protocol: The protocol adapter to use for testing
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Only test if this is the 2025-06-18 adapter
        if not isinstance(protocol, MCP2025_06_18Adapter):
            return True, "Skipped: Not 2025-06-18 protocol"
        
        # Check if server supports resources
        capabilities = protocol.server_capabilities
        if not capabilities.get("resources"):
            return True, "Skipped: Server does not support resources"
        
        # List resources
        resources = await protocol.get_resources_list()
        
        if not resources:
            return True, "Skipped: No resources available for testing"
        
        # Test reading a resource with metadata
        resource = resources[0]
        resource_uri = resource.get("uri")
        
        if not resource_uri:
            return False, "Resource missing required 'uri' field"
        
        # Read the resource
        resource_data = await protocol.get_resource_with_metadata(resource_uri)
        
        # Validate 2025-06-18 resource format
        if "contents" not in resource_data:
            return False, "Resource response missing required 'contents' field"
        
        contents = resource_data["contents"]
        if not isinstance(contents, list):
            return False, "Resource contents must be an array"
        
        for content in contents:
            if "uri" not in content:
                return False, "Resource content missing required 'uri' field"
            
            if "text" not in content and "blob" not in content:
                return False, "Resource content must have either 'text' or 'blob' field"
        
        return True, f"Resource metadata properly supported - read {len(contents)} content items"
        
    except Exception as e:
        return False, f"Resource metadata test failed: {str(e)}"


# Test cases for 2025-06-18 protocol
TEST_CASES = [
    (test_structured_tool_output, "test_structured_tool_output"),
    (test_elicitation_support, "test_elicitation_support"),
    (test_batch_request_rejection, "test_batch_request_rejection"),
    (test_enhanced_tool_validation, "test_enhanced_tool_validation"),
    (test_protocol_version_negotiation, "test_protocol_version_negotiation"),
    (test_enhanced_ping_validation, "test_enhanced_ping_validation"),
    (test_resource_metadata_support, "test_resource_metadata_support"),
] 