# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base Protocol Adapter for MCP Testing.

This module defines the base interface for protocol adapters used in the MCP testing framework.
Protocol adapters handle the communication protocol with the MCP server for a specific protocol version.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union

from mcp_testing.transports.base import MCPTransportAdapter


class MCPProtocolAdapter(ABC):
    """Base class for MCP protocol adapters."""
    
    def __init__(self, transport: MCPTransportAdapter, debug: bool = False):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport adapter to use for communication
            debug: Whether to enable debug output
        """
        self.transport = transport
        self.debug = debug
        self.initialized = False
        self.server_capabilities = {}
        self.server_info = {}
        self.protocol_version = None
    
    @property
    @abstractmethod
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string (e.g., "2024-11-05")
        """
        pass
    
    @abstractmethod
    async def initialize(self, client_capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize the connection with the MCP server.
        
        Args:
            client_capabilities: Capabilities to advertise to the server
            
        Returns:
            The server's initialize response containing capabilities
            
        Raises:
            ConnectionError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def send_initialized(self) -> None:
        """
        Send the 'initialized' notification to the server.
        
        This notification is sent after initialization to indicate that the
        client is ready to receive messages.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        pass
    
    @abstractmethod
    async def get_tools_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of tools supported by the server.
        
        Returns:
            A list of tool definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the server.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The tool's response
            
        Raises:
            ConnectionError: If the tool call fails
        """
        pass
    
    @abstractmethod
    async def get_resources_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of resources available on the server.
        
        Returns:
            A list of resource definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """
        Get a resource from the server.
        
        Args:
            resource_id: The ID of the resource to get
            
        Returns:
            The resource data
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def create_resource(self, resource_type: str, content: Any) -> Dict[str, Any]:
        """
        Create a resource on the server.
        
        Args:
            resource_type: The type of resource to create
            content: The content of the resource
            
        Returns:
            The created resource data including its ID
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def get_prompt_models(self) -> List[Dict[str, Any]]:
        """
        Get the list of prompt models supported by the server.
        
        Returns:
            A list of prompt model definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def prompt_completion(self, model: str, prompt: str, 
                               options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Request a completion for a prompt.
        
        Args:
            model: The model to use for completion
            prompt: The prompt text
            options: Additional options for the completion
            
        Returns:
            The completion response
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Send a shutdown request to the server.
        
        This notifies the server that the client is about to exit.
        
        Raises:
            ConnectionError: If the shutdown request fails
        """
        pass
    
    @abstractmethod
    async def exit(self) -> None:
        """
        Send an exit notification to the server.
        
        This notifies the server that the client is exiting and that the
        connection will be closed.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        pass 