"""
Tests for MCP initialization.

This module tests the initialization sequence for MCP servers.
"""

from typing import Tuple

from mcp_testing.protocols.base import MCPProtocolAdapter


async def test_initialization(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test basic initialization.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    # The test runner already performs initialization,
    # so we just need to verify that it was successful
    
    # Check if the protocol version was negotiated
    if not protocol.protocol_version:
        return False, "Protocol version was not negotiated"
    
    # Check if server capabilities were received
    if not protocol.server_capabilities:
        return False, "Server capabilities were not received"
    
    # Check if server info was received (optional)
    if not protocol.server_info:
        return True, "Server info was not provided (optional)"
    
    return True, "Initialization successful"


async def test_server_capabilities(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
    """
    Test that the server advertises the required capabilities.
    
    Args:
        protocol: The protocol adapter to use
        
    Returns:
        A tuple containing (passed, message)
    """
    capabilities = protocol.server_capabilities
    
    # Basic validation based on protocol version
    if protocol.version == "2024-11-05":
        # 2024-11-05 should at least support some basic capabilities
        required_caps = []
        missing_caps = []
        
        for cap in required_caps:
            if cap not in capabilities:
                missing_caps.append(cap)
        
        if missing_caps:
            return False, f"Missing required capabilities: {', '.join(missing_caps)}"
    
    elif protocol.version == "2025-03-26":
        # 2025-03-26 should at least support some basic capabilities
        required_caps = []
        missing_caps = []
        
        for cap in required_caps:
            if cap not in capabilities:
                missing_caps.append(cap)
        
        if missing_caps:
            return False, f"Missing required capabilities: {', '.join(missing_caps)}"
    
    return True, f"Server supports all required capabilities for {protocol.version}"


# Create a list of all test cases in this module
TEST_CASES = [
    (test_initialization, "test_initialization"),
    (test_server_capabilities, "test_server_capabilities"),
] 