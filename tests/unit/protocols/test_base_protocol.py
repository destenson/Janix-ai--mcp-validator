"""
Tests for the MCPProtocolAdapter base class.
"""

import pytest
from unittest.mock import MagicMock
from abc import ABC

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.transports.base import MCPTransportAdapter


def test_abstract_class():
    """Test that MCPProtocolAdapter is an abstract class."""
    assert issubclass(MCPProtocolAdapter, ABC)
    
    with pytest.raises(TypeError):
        # Should raise TypeError when trying to instantiate an abstract class
        MCPProtocolAdapter(MagicMock())


def test_required_abstract_methods():
    """Test that MCPProtocolAdapter has the required abstract methods."""
    abstract_methods = [
        'version',
        'initialize',
        'send_initialized',
        'get_tools_list',
        'call_tool',
        'get_resources_list',
        'get_resource',
        'create_resource',
        'get_prompt_models',
        'prompt_completion',
        'shutdown',
        'exit'
    ]
    
    for method in abstract_methods:
        assert method in MCPProtocolAdapter.__abstractmethods__


def test_init():
    """Test the initialization of MCPProtocolAdapter with a concrete implementation."""
    # Create a concrete subclass that implements all abstract methods
    class ConcreteMCPProtocolAdapter(MCPProtocolAdapter):
        @property
        def version(self): return "test-version"
        async def initialize(self, client_capabilities=None): pass
        async def send_initialized(self): pass
        async def get_tools_list(self): pass
        async def call_tool(self, name, arguments): pass
        async def get_resources_list(self): pass
        async def get_resource(self, resource_id): pass
        async def create_resource(self, resource_type, content): pass
        async def get_prompt_models(self): pass
        async def prompt_completion(self, model, prompt, options=None): pass
        async def shutdown(self): pass
        async def exit(self): pass
    
    # Create a mock transport
    mock_transport = MagicMock(spec=MCPTransportAdapter)
    
    # Initialize the adapter
    adapter = ConcreteMCPProtocolAdapter(mock_transport, debug=True)
    
    # Check that the adapter was initialized correctly
    assert adapter.transport == mock_transport
    assert adapter.debug is True
    assert adapter.initialized is False
    assert adapter.server_capabilities == {}
    assert adapter.server_info == {}
    assert adapter.protocol_version is None 