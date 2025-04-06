"""
Protocol version adapters for the MCP Protocol Validator.

This package contains adapters for different versions of the MCP protocol,
allowing the validator to test servers implementing different protocol versions.
"""

from protocols.base import MCPProtocolAdapter
from protocols.v2024_11_05 import MCP2024_11_05Adapter
from protocols.v2025_03_26 import MCP2025_03_26Adapter

# A mapping of protocol versions to their adapter classes
PROTOCOL_ADAPTERS = {
    "2024-11-05": MCP2024_11_05Adapter,
    "2025-03-26": MCP2025_03_26Adapter
}

def get_protocol_adapter(version: str, transport, debug: bool = False) -> MCPProtocolAdapter:
    """
    Get the appropriate protocol adapter for the specified version.
    
    Args:
        version: The protocol version to get an adapter for
        transport: The transport to use for communication
        debug: Whether to enable debug logging
        
    Returns:
        An instance of the appropriate protocol adapter
        
    Raises:
        ValueError: If the specified version is not supported
    """
    if version not in PROTOCOL_ADAPTERS:
        supported_versions = ", ".join(PROTOCOL_ADAPTERS.keys())
        raise ValueError(f"Unsupported protocol version: {version}. "
                        f"Supported versions are: {supported_versions}")
    
    adapter_class = PROTOCOL_ADAPTERS[version]
    return adapter_class(transport, debug=debug)

__all__ = [
    'MCPProtocolAdapter',
    'MCP2024_11_05Adapter',
    'MCP2025_03_26Adapter',
    'PROTOCOL_ADAPTERS',
    'get_protocol_adapter'
] 