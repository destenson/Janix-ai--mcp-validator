# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Protocol adapter for MCP version 2024-11-05.

This module implements the protocol adapter for the 2024-11-05 version of the MCP protocol,
which is the original MCP specification.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union

from protocols.base import MCPProtocolAdapter


class MCP2024_11_05Adapter(MCPProtocolAdapter):
    """
    Protocol adapter for MCP version 2024-11-05.
    
    This adapter implements the original MCP specification as defined in the
    2024-11-05 protocol version.
    """
    
    @property
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string "2024-11-05"
        """
        return "2024-11-05"
    
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
        if not client_capabilities:
            client_capabilities = {}
            
        # Make sure the transport is started
        if not self.transport.start():
            raise ConnectionError("Failed to start transport")
            
        # Prepare the initialize request
        request = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": self.version,
                "capabilities": client_capabilities,
                "clientInfo": {
                    "name": "MCPProtocolValidator",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send the initialize request
        if self.debug:
            print(f"Sending initialize request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received initialize response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Initialization failed: {response['error']['message']}")
                
            # Extract and store server information
            self.protocol_version = response.get("result", {}).get("protocolVersion")
            self.server_capabilities = response.get("result", {}).get("capabilities", {})
            self.server_info = response.get("result", {}).get("serverInfo", {})
            
            # Mark as initialized
            self.initialized = True
            
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Initialization failed: {str(e)}")
    
    async def send_initialized(self) -> None:
        """
        Send the 'initialized' notification to the server.
        
        This notification is sent after initialization to indicate that the
        client is ready to receive messages.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot send 'initialized' notification before initialization")
            
        # Prepare the initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        # Send the notification
        if self.debug:
            print(f"Sending initialized notification: {json.dumps(notification)}")
            
        try:
            self.transport.send_notification(notification)
        except Exception as e:
            raise ConnectionError(f"Failed to send initialized notification: {str(e)}")
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the server.
        
        Returns:
            A dict containing server information (name, version, etc.)
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get server info before initialization")
            
        return self.server_info
    
    async def get_tools_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of tools supported by the server.
        
        Returns:
            A list of tool definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get tools list before initialization")
            
        # Prepare the tools/list request
        request = {
            "jsonrpc": "2.0",
            "id": "tools_list",
            "method": "tools/list",
            "params": {}
        }
        
        # Send the request
        if self.debug:
            print(f"Sending tools/list request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received tools/list response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to get tools list: {response['error']['message']}")
                
            return response.get("result", {}).get("tools", [])
        except Exception as e:
            raise ConnectionError(f"Failed to get tools list: {str(e)}")
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Invoke a tool on the server.
        
        According to the MCP specification, tools are invoked by using their name
        directly as the method name.
        
        Args:
            tool_name: The name of the tool to invoke
            params: The parameters for the tool invocation
            
        Returns:
            The tool's response
            
        Raises:
            ConnectionError: If the tool invocation fails
            ValueError: If the tool is not supported
        """
        if not self.initialized:
            raise ConnectionError("Cannot invoke tool before initialization")
            
        # In MCP, the method name is just the tool name (no namespace)
        # This is the spec-compliant way
        method = tool_name
        
        # Prepare the tool invocation request
        request = {
            "jsonrpc": "2.0",
            "id": f"tool_{tool_name}",
            "method": method,
            "params": params
        }
        
        # Send the request
        if self.debug:
            print(f"Sending tool invocation request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received tool invocation response: {json.dumps(response)}")
                
            # Check for "Method not found" errors which might indicate a non-compliant server
            if "error" in response and response["error"].get("code") == -32601:
                error_msg = f"Server is non-compliant with MCP specification: Tool '{tool_name}' should be invoked with method='{tool_name}'"
                print(f"WARNING: {error_msg}")
                
                # Try alternate formats as a fallback to make testing possible
                # But make it clear this is non-compliant behavior
                fallback_formats = [
                    f"tools/{tool_name}",      # Tools namespace
                    f"filesystem/{tool_name}",  # Filesystem namespace
                    f"fs/{tool_name}"           # Short filesystem namespace
                ]
                
                if self.debug:
                    print(f"Attempting non-compliant fallback formats: {fallback_formats}")
                
                for fallback in fallback_formats:
                    fallback_request = {
                        "jsonrpc": "2.0",
                        "id": f"tool_{tool_name}_{fallback}",
                        "method": fallback,
                        "params": params
                    }
                    
                    if self.debug:
                        print(f"Trying fallback format: {json.dumps(fallback_request)}")
                    
                    fallback_response = self.transport.send_request(fallback_request)
                    
                    if self.debug:
                        print(f"Fallback response: {json.dumps(fallback_response)}")
                    
                    if "error" not in fallback_response:
                        print(f"WARNING: Server accepted non-compliant method format: '{fallback}'")
                        return fallback_response.get("result", {})
                
                # If all fallbacks fail, raise the original error
                raise ConnectionError(f"Tool invocation failed: {response['error']['message']} - Server is non-compliant with MCP specification")
            
            # Any other error is a failure
            if "error" in response:
                raise ConnectionError(f"Tool invocation failed: {response['error']['message']}")
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Tool invocation failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """
        Send a shutdown request to the server.
        
        This notifies the server that the client is about to exit.
        
        Raises:
            ConnectionError: If the shutdown request fails
        """
        if not self.initialized:
            return
            
        # Prepare the shutdown request
        request = {
            "jsonrpc": "2.0",
            "id": "shutdown",
            "method": "shutdown",
            "params": {}
        }
        
        # Send the request
        if self.debug:
            print(f"Sending shutdown request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received shutdown response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Shutdown failed: {response['error']['message']}")
        except Exception as e:
            raise ConnectionError(f"Shutdown failed: {str(e)}")
    
    async def exit(self) -> None:
        """
        Send an exit notification to the server.
        
        This notifies the server that the client is exiting and that the
        connection will be closed.
        
        Raises:
            ConnectionError: If sending the notification fails
        """
        # Prepare the exit notification
        notification = {
            "jsonrpc": "2.0",
            "method": "exit",
            "params": {}
        }
        
        # Send the notification
        if self.debug:
            print(f"Sending exit notification: {json.dumps(notification)}")
            
        try:
            self.transport.send_notification(notification)
        except Exception as e:
            if self.debug:
                print(f"Failed to send exit notification: {str(e)}")
            # Don't raise here, as we're exiting anyway 