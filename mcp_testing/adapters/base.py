#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base server adapter for MCP testing.

This module defines the base server adapter class that will be extended
by specific server implementations.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MCPServerAdapter(ABC):
    """
    Base class for MCP server adapters.
    
    Server adapters are responsible for starting, communicating with, and stopping
    MCP servers during testing. This abstract base class defines the interface that
    all server adapters must implement.
    """
    
    def __init__(self, protocol_version: str, debug: bool = False):
        """
        Initialize a server adapter.
        
        Args:
            protocol_version: The MCP protocol version to use
            debug: Whether to enable debug logging
        """
        self.protocol_version = protocol_version
        self.debug = debug
        self.server_info = None
        self._request_id = 0
        
    @abstractmethod
    async def start(self) -> bool:
        """
        Start the server.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
        
    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop the server.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
        
    @abstractmethod
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a request to the server and wait for a response.
        
        Args:
            method: The JSON-RPC method name
            params: The method parameters
            
        Returns:
            The server's response
            
        Raises:
            RuntimeError: If the server is not started or the request fails
        """
        pass
        
    @abstractmethod
    async def send_notification(self, method: str, params: Dict[str, Any] = None) -> None:
        """
        Send a notification to the server (no response expected).
        
        Args:
            method: The JSON-RPC method name
            params: The method parameters
            
        Raises:
            RuntimeError: If the server is not started or the notification fails
        """
        pass
        
    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize the server.
        
        This sends the standard initialize request to the server.
        
        Returns:
            The server's initialization response
            
        Raises:
            RuntimeError: If initialization fails
        """
        params = {
            "protocolVersion": self.protocol_version,
            "options": {}
        }
        
        response = await self.send_request("initialize", params)
        
        if "error" in response:
            error_msg = response.get("error", {}).get("message", "Unknown error")
            logger.error(f"Server initialization failed: {error_msg}")
            raise RuntimeError(f"Failed to initialize server: {error_msg}")
            
        if "result" not in response:
            raise RuntimeError("Invalid initialize response, missing 'result' field")
            
        self.server_info = response["result"]
        return response
        
    async def shutdown(self) -> Optional[Dict[str, Any]]:
        """
        Send a shutdown request to the server.
        
        Returns:
            The server's shutdown response, or None if the server doesn't support shutdown
        """
        try:
            response = await self.send_request("shutdown", {})
            await self.send_notification("exit")
            return response
        except Exception as e:
            logger.warning(f"Failed to shut down server: {str(e)}")
            return None
            
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Get the list of available tools from the server.
        
        Returns:
            A list of tool definitions
            
        Raises:
            RuntimeError: If the request fails
        """
        response = await self.send_request("listTools", {})
        
        if "error" in response:
            error_msg = response.get("error", {}).get("message", "Unknown error")
            raise RuntimeError(f"Failed to list tools: {error_msg}")
            
        if "result" not in response:
            raise RuntimeError("Invalid listTools response, missing 'result' field")
            
        return response["result"]
        
    async def call_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the server.
        
        Args:
            name: The name of the tool to call
            params: The tool parameters
            
        Returns:
            The tool's response
            
        Raises:
            RuntimeError: If the tool call fails
        """
        request_params = {
            "name": name,
            "params": params
        }
        
        response = await self.send_request("callTool", request_params)
        
        if "error" in response:
            error = response.get("error", {})
            error_msg = error.get("message", "Unknown error")
            logger.error(f"Tool call failed: {error_msg}")
            return response
            
        if "result" not in response:
            logger.error("Invalid callTool response, missing 'result' field")
            
        return response
        
    def _get_next_request_id(self) -> int:
        """
        Get the next request ID.
        
        Returns:
            The next request ID
        """
        self._request_id += 1
        return self._request_id 