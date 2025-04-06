"""
Base protocol adapter defining the interface for all MCP protocol version implementations.

This module defines an abstract base class that all protocol version adapters must implement.
Protocol adapters handle version-specific differences in the MCP protocol, allowing the rest
of the validator to work with a consistent interface regardless of protocol version.
"""

import abc
from typing import Any, Dict, List, Optional, Union


class MCPProtocolAdapter(abc.ABC):
    """
    Abstract base class for MCP protocol version adapters.
    
    Protocol adapters handle version-specific differences in the MCP protocol,
    translating between the core validator code and the specific protocol version
    being tested.
    """
    
    def __init__(self, transport, debug: bool = False):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport implementation to use for communication
            debug: Whether to enable debug logging
        """
        self.transport = transport
        self.debug = debug
        self.initialized = False
        self.server_capabilities = None
        self.server_info = None
        self.protocol_version = None
    
    @property
    @abc.abstractmethod
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string (e.g., "2024-11-05")
        """
        pass
    
    @abc.abstractmethod
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
    
    @abc.abstractmethod
    async def send_initialized(self) -> None:
        """
        Send the 'initialized' notification to the server.
        
        This notification is sent after initialization to indicate that the
        client is ready to receive messages.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        pass
    
    @abc.abstractmethod
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the server.
        
        Returns:
            A dict containing server information (name, version, etc.)
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abc.abstractmethod
    async def get_tools_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of tools supported by the server.
        
        Returns:
            A list of tool definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        pass
    
    @abc.abstractmethod
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Invoke a tool on the server.
        
        Args:
            tool_name: The name of the tool to invoke
            params: The parameters for the tool invocation
            
        Returns:
            The tool's response
            
        Raises:
            ConnectionError: If the tool invocation fails
            ValueError: If the tool is not supported
        """
        pass
    
    @abc.abstractmethod
    async def shutdown(self) -> None:
        """
        Send a shutdown request to the server.
        
        This notifies the server that the client is about to exit.
        
        Raises:
            ConnectionError: If the shutdown request fails
        """
        pass
    
    @abc.abstractmethod
    async def exit(self) -> None:
        """
        Send an exit notification to the server.
        
        This notifies the server that the client is exiting and that the
        connection will be closed.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        pass
    
    async def close(self) -> None:
        """
        Close the connection with the server.
        
        This method performs the proper shutdown sequence and closes the transport.
        """
        if self.initialized:
            try:
                await self.shutdown()
                await self.exit()
            except Exception as e:
                if self.debug:
                    print(f"Error during shutdown sequence: {e}")
            finally:
                self.initialized = False
        
        # Close the transport
        if self.transport:
            self.transport.stop()
            self.transport = None 