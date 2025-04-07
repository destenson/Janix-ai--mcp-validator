"""
Base Transport Adapter for MCP Testing.

This module defines the base interface for transport adapters used in the MCP testing framework.
Transport adapters handle the communication between the test client and the MCP server.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List


class MCPTransportAdapter(ABC):
    """Base class for MCP transport adapters."""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the transport adapter.
        
        Args:
            debug: Whether to enable debug output
        """
        self.debug = debug
        self.is_started = False
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the transport. This may involve launching a subprocess or
        establishing a connection to a server.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the transport. This may involve terminating a subprocess or
        closing a connection.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and wait for a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object
            
        Raises:
            ConnectionError: If the transport is not started or the request fails
        """
        pass
    
    @abstractmethod
    def send_notification(self, notification: Dict[str, Any]) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            notification: The JSON-RPC notification object
            
        Raises:
            ConnectionError: If the transport is not started or the notification fails
        """
        pass
    
    @abstractmethod
    def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Send a batch of JSON-RPC requests and wait for responses.
        
        Args:
            requests: A list of JSON-RPC request objects
            
        Returns:
            A list of JSON-RPC response objects
            
        Raises:
            ConnectionError: If the transport is not started or the batch request fails
        """
        pass 