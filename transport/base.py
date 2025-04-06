"""
Base transport layer interface for MCP Protocol Validator.

This module defines the base interface that all transport implementations
must adhere to for communicating with MCP servers.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple


class MCPTransport(ABC):
    """
    Abstract base class defining the interface for MCP transport implementations.
    
    All transport implementations (HTTP, STDIO, Docker) must implement
    this interface to provide a consistent way to communicate with
    MCP servers regardless of the underlying transport mechanism.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize the transport with common parameters.
        
        Args:
            debug: Whether to enable debug logging
        """
        self.debug = debug
        self.request_id_counter = 0
        
    def next_request_id(self) -> str:
        """
        Generate a unique request ID for the next request.
        
        Returns:
            A string containing a unique request ID
        """
        self.request_id_counter += 1
        return f"req_{self.request_id_counter}"
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the transport connection to the server.
        
        This method should handle any initialization needed for the
        transport layer, such as establishing connections or starting processes.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the transport connection to the server.
        
        This method should clean up any resources used by the transport,
        such as closing connections or terminating processes.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def send_request(self, request: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server and wait for a response.
        
        Args:
            request: Either a complete request object or a method name string
            params: Parameters to pass to the method (if request is a method name)
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            The JSON-RPC response from the server
        """
        pass
    
    @abstractmethod
    def send_notification(self, notification: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification to the server (no response expected).
        
        Args:
            notification: Either a complete notification object or a method name string
            params: Parameters to pass to the method (if notification is a method name)
        """
        pass
    
    def initialize(self, protocol_version: str, client_info: Dict[str, str], 
                  capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize the MCP server with the specified protocol version and capabilities.
        
        Args:
            protocol_version: The protocol version to use
            client_info: Client name and version info
            capabilities: Client capabilities to advertise to the server
            
        Returns:
            The server's initialize response
        """
        if capabilities is None:
            capabilities = {}
            
        init_params = {
            "protocolVersion": protocol_version,
            "clientInfo": client_info,
            "capabilities": capabilities
        }
        
        response = self.send_request("initialize", init_params)
        self.send_notification("initialized", {})
        return response
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of available tools from the server.
        
        Returns:
            List of tool descriptions
        """
        response = self.send_request("tools/list", {})
        if "result" in response and isinstance(response["result"], dict) and "tools" in response["result"]:
            return response["result"]["tools"]
        return []
    
    @staticmethod
    def format_request(method: str, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Format a JSON-RPC request object.
        
        Args:
            method: The method name to call
            params: Parameters to pass to the method
            request_id: Request ID
            
        Returns:
            A properly formatted JSON-RPC request object
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
    
    @staticmethod
    def format_notification(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a JSON-RPC notification object.
        
        Args:
            method: The method name to call
            params: Parameters to pass to the method
            
        Returns:
            A properly formatted JSON-RPC notification object
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
    
    def log_debug(self, message: str) -> None:
        """
        Log a debug message if debug mode is enabled.
        
        Args:
            message: The message to log
        """
        if self.debug:
            print(f"[DEBUG] {message}")
            
    def log_error(self, message: str) -> None:
        """
        Log an error message.
        
        Args:
            message: The error message to log
        """
        print(f"[ERROR] {message}")
    
    def log_info(self, message: str) -> None:
        """
        Log an informational message.
        
        Args:
            message: The info message to log
        """
        print(f"[INFO] {message}") 