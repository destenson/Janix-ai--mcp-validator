# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol adapter for MCP version 2024-11-05.

This module implements the protocol adapter for the 2024-11-05 version of the MCP protocol,
which is the original MCP specification.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Union

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.transports.base import MCPTransportAdapter


class MCP2024_11_05Adapter(MCPProtocolAdapter):
    """
    Protocol adapter for MCP version 2024-11-05.
    
    This adapter implements the original MCP specification as defined in the
    2024-11-05 protocol version.
    """
    
    def __init__(self, transport: MCPTransportAdapter, debug: bool = False):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport adapter to use for communication
            debug: Whether to enable debug output
        """
        super().__init__(transport, debug)
    
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
        if self.initialized:
            return self.server_capabilities

        # Build initialize request
        request = {
            "jsonrpc": "2.0",
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": self.version,
                "capabilities": client_capabilities or {},
                "clientInfo": {
                    "name": "MCP Test Client",
                    "version": "1.0.0"
                }
            }
        }

        try:
            response = self.transport.send_request(request)
            if "result" not in response:
                raise ConnectionError(f"Initialize failed: {response.get('error', {}).get('message', 'Unknown error')}")

            result = response["result"]
            self.server_capabilities = result.get("capabilities", {})
            self.server_info = result.get("serverInfo", {})
            self.protocol_version = result.get("protocolVersion")

            # For 2024-11-05, capabilities are simple booleans
            if isinstance(self.server_capabilities.get("tools"), bool):
                self.server_capabilities["tools"] = {"supported": self.server_capabilities["tools"]}

            self.initialized = True
            return result

        except Exception as e:
            raise ConnectionError(f"Initialize failed: {str(e)}")
    
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
            
        request = {
            "jsonrpc": "2.0",
            "id": "tools_list",
            "method": "tools/list"
        }

        try:
            response = self.transport.send_request(request)
            if "result" not in response:
                raise Exception(f"Failed to get tools list: {response.get('error', {}).get('message', 'Unknown error')}")

            tools = response["result"].get("tools", [])
            
            # For 2024-11-05, validate tool schema format
            for tool in tools:
                if "inputSchema" in tool and "parameters" not in tool:
                    # Convert inputSchema to parameters format for consistency
                    tool["parameters"] = tool["inputSchema"]
                    
            return tools

        except Exception as e:
            raise Exception(f"Failed to get tools list: {str(e)}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
        if not self.initialized:
            raise ConnectionError("Cannot call tool before initialization")
            
        request = {
            "jsonrpc": "2.0",
            "id": "tool_call",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        try:
            response = self.transport.send_request(request)
            if "result" not in response:
                raise Exception(f"Tool call failed: {response.get('error', {}).get('message', 'Unknown error')}")
            return response["result"]

        except Exception as e:
            raise Exception(f"Tool call failed: {str(e)}")
    
    async def get_resources_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of resources available on the server.
        
        Returns:
            A list of resource definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get resources list before initialization")
            
        # Prepare the resources/list request
        request = {
            "jsonrpc": "2.0",
            "id": "resources_list",
            "method": "resources/list",
            "params": {}
        }
        
        # Send the request
        if self.debug:
            print(f"Sending resources/list request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received resources/list response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to get resources list: {response['error']['message']}")
                
            return response.get("result", {}).get("resources", [])
        except Exception as e:
            raise ConnectionError(f"Failed to get resources list: {str(e)}")
    
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
        if not self.initialized:
            raise ConnectionError("Cannot get resource before initialization")
            
        # Prepare the resources/get request
        request = {
            "jsonrpc": "2.0",
            "id": "resource_get",
            "method": "resources/get",
            "params": {
                "id": resource_id
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Sending resources/get request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received resources/get response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to get resource: {response['error']['message']}")
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Failed to get resource: {str(e)}")
    
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
        if not self.initialized:
            raise ConnectionError("Cannot create resource before initialization")
            
        # Prepare the resources/create request
        request = {
            "jsonrpc": "2.0",
            "id": "resource_create",
            "method": "resources/create",
            "params": {
                "type": resource_type,
                "content": content
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Sending resources/create request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received resources/create response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to create resource: {response['error']['message']}")
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Failed to create resource: {str(e)}")
    
    async def get_prompt_models(self) -> List[Dict[str, Any]]:
        """
        Get the list of prompt models supported by the server.
        
        Returns:
            A list of prompt model definitions
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get prompt models before initialization")
            
        # Prepare the prompt/models request
        request = {
            "jsonrpc": "2.0",
            "id": "prompt_models",
            "method": "prompt/models",
            "params": {}
        }
        
        # Send the request
        if self.debug:
            print(f"Sending prompt/models request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received prompt/models response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to get prompt models: {response['error']['message']}")
                
            return response.get("result", {}).get("models", [])
        except Exception as e:
            raise ConnectionError(f"Failed to get prompt models: {str(e)}")
    
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
        if not self.initialized:
            raise ConnectionError("Cannot request prompt completion before initialization")
            
        # Prepare the prompt/completion request
        params = {
            "model": model,
            "prompt": prompt
        }
        
        if options:
            params.update(options)
            
        request = {
            "jsonrpc": "2.0",
            "id": "prompt_completion",
            "method": "prompt/completion",
            "params": params
        }
        
        # Send the request
        if self.debug:
            print(f"Sending prompt/completion request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received prompt/completion response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Prompt completion failed: {response['error']['message']}")
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Prompt completion failed: {str(e)}")
    
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