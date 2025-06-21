# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol adapter for MCP version 2025-06-18.

This module implements the protocol adapter for the 2025-06-18 version of the MCP protocol,
which includes major changes like removal of JSON-RPC batching, structured tool output,
OAuth 2.1 compliance, elicitation support, and enhanced security requirements.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter
from mcp_testing.transports.base import MCPTransportAdapter


class MCP2025_06_18Adapter(MCP2025_03_26Adapter):
    """
    Protocol adapter for MCP version 2025-06-18.
    
    This adapter implements the 2025-06-18 protocol version, which includes
    all features from 2025-03-26 plus:
    - Removal of JSON-RPC batching support
    - Structured tool output with outputSchema
    - OAuth 2.1 compliance for HTTP transport
    - Elicitation support for user interaction
    - Enhanced security requirements
    - Resource links in tool results
    - Protocol version headers for HTTP
    - Updated lifecycle operations
    """
    
    def __init__(self, transport: MCPTransportAdapter, debug: bool = False):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport adapter to use for communication
            debug: Whether to enable debug output
        """
        super().__init__(transport, debug)
        self.elicitation_requests = {}
        self.protocol_version_header = "2025-06-18"
    
    @property
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string "2025-06-18"
        """
        return "2025-06-18"
    
    async def initialize(self, client_capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize the connection with the MCP server.
        
        For 2025-06-18, this includes enhanced capability negotiation and
        support for elicitation, OAuth 2.1, and other new features.
        
        Args:
            client_capabilities: Capabilities to advertise to the server
            
        Returns:
            The server's initialize response containing capabilities
            
        Raises:
            ConnectionError: If initialization fails
        """
        if self.initialized:
            return self.server_capabilities

        # Build enhanced client capabilities for 2025-06-18
        default_capabilities = {
            "tools": {"asyncSupported": True},
            "resources": {"subscribe": True, "listChanged": True},
            "roots": {"listChanged": True},
            "sampling": {},
            "elicitation": {},  # New in 2025-06-18
            "logging": {}
        }
        
        if client_capabilities:
            default_capabilities.update(client_capabilities)

        # Build initialize request
        request = {
            "jsonrpc": "2.0", 
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": self.version,
                "capabilities": default_capabilities,
                "clientInfo": {
                    "name": "MCP Test Client 2025-06-18",
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

            # Validate protocol version match for 2025-06-18
            if self.protocol_version != self.version:
                raise ConnectionError(f"Protocol version mismatch: expected {self.version}, got {self.protocol_version}")

            self.initialized = True
            return result

        except Exception as e:
            raise ConnectionError(f"Initialize failed: {str(e)}")
    
    async def call_tool_with_structured_output(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool and expect structured output (new in 2025-06-18).
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The tool's response with structured content
            
        Raises:
            ConnectionError: If the tool call fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot call tool before initialization")
            
        request = {
            "jsonrpc": "2.0",
            "id": f"tool_call_{uuid.uuid4()}",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }

        try:
            response = self.transport.send_request(request)
            if "result" not in response:
                raise Exception(f"Tool call failed: {response.get('error', {}).get('message', 'Unknown error')}")
            
            result = response["result"]
            
            # Validate 2025-06-18 tool response format
            if "content" not in result:
                raise Exception("Tool response missing required 'content' field")
            
            if "isError" not in result:
                raise Exception("Tool response missing required 'isError' field")
            
            # Check for structured content (new in 2025-06-18)
            if "structuredContent" in result:
                if self.debug:
                    print(f"Tool returned structured content: {json.dumps(result['structuredContent'])}")
            
            return result

        except Exception as e:
            raise Exception(f"Tool call failed: {str(e)}")
    
    async def create_elicitation_request(self, schema: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Create an elicitation request (new in 2025-06-18).
        
        This allows servers to request additional information from users.
        
        Args:
            schema: JSON schema for the expected response
            prompt: Human-readable prompt for the user
            
        Returns:
            The elicitation response from the client
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot create elicitation request before initialization")
            
        # Check if client supports elicitation
        if not self.server_capabilities.get("elicitation"):
            raise ConnectionError("Server does not support elicitation")
            
        request_id = str(uuid.uuid4())
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "elicitation/create",
            "params": {
                "schema": schema,
                "prompt": prompt
            }
        }
        
        if self.debug:
            print(f"Sending elicitation request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received elicitation response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Elicitation request failed: {response['error']['message']}")
                
            result = response.get("result", {})
            
            # Validate elicitation response format
            if "action" not in result:
                raise ConnectionError("Elicitation response missing required 'action' field")
                
            action = result["action"]
            if action not in ["accept", "reject", "cancel"]:
                raise ConnectionError(f"Invalid elicitation action: {action}")
                
            return result
        except Exception as e:
            raise ConnectionError(f"Elicitation request failed: {str(e)}")
    
    async def get_resource_with_metadata(self, resource_id: str) -> Dict[str, Any]:
        """
        Get a resource with enhanced metadata support (2025-06-18).
        
        Args:
            resource_id: The ID of the resource to get
            
        Returns:
            The resource data with metadata
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get resource before initialization")
            
        request = {
            "jsonrpc": "2.0",
            "id": "resource_get",
            "method": "resources/read",
            "params": {
                "uri": resource_id
            }
        }
        
        if self.debug:
            print(f"Sending resources/read request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received resources/read response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to read resource: {response['error']['message']}")
                
            result = response.get("result", {})
            
            # Validate 2025-06-18 resource response format
            if "contents" not in result:
                raise ConnectionError("Resource response missing required 'contents' field")
                
            contents = result["contents"]
            if not isinstance(contents, list):
                raise ConnectionError("Resource contents must be an array")
                
            for content in contents:
                if "uri" not in content:
                    raise ConnectionError("Resource content missing required 'uri' field")
                    
                if "text" not in content and "blob" not in content:
                    raise ConnectionError("Resource content must have either 'text' or 'blob' field")
                    
            return result
        except Exception as e:
            raise ConnectionError(f"Failed to read resource: {str(e)}")
    
    async def list_tools_with_output_schema(self) -> List[Dict[str, Any]]:
        """
        Get the list of tools with output schema support (2025-06-18).
        
        Returns:
            A list of tool definitions with optional output schemas
            
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
            
            # Validate 2025-06-18 tool format
            for tool in tools:
                if "name" not in tool:
                    raise Exception("Tool missing required 'name' field")
                if "description" not in tool:
                    raise Exception(f"Tool '{tool.get('name')}' missing required 'description' field")
                if "inputSchema" not in tool:
                    raise Exception(f"Tool '{tool.get('name')}' missing required 'inputSchema' field")
                    
                # Check for new fields in 2025-06-18
                if "title" in tool and self.debug:
                    print(f"Tool '{tool['name']}' has display title: {tool['title']}")
                    
                if "outputSchema" in tool and self.debug:
                    print(f"Tool '{tool['name']}' defines output schema")
                    
            return tools

        except Exception as e:
            raise Exception(f"Failed to get tools list: {str(e)}")
    
    async def send_batch_request(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Attempt to send a batch request (should fail in 2025-06-18).
        
        Args:
            requests: List of requests to send
            
        Returns:
            Should not return - should raise an exception
            
        Raises:
            ConnectionError: Always, as batching is not supported in 2025-06-18
        """
        # JSON-RPC batching is explicitly not supported in 2025-06-18
        raise ConnectionError("JSON-RPC batching is not supported in protocol version 2025-06-18")
    
    async def ping_with_enhanced_validation(self) -> Dict[str, Any]:
        """
        Send a ping with enhanced validation for 2025-06-18.
        
        Returns:
            Empty response if successful
            
        Raises:
            ConnectionError: If the ping fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot ping before initialization")
            
        request = {
            "jsonrpc": "2.0",
            "id": "ping",
            "method": "ping",
            "params": {}
        }
        
        if self.debug:
            print(f"Sending ping request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received ping response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Ping failed: {response['error']['message']}")
                
            # Validate that ping response is empty (as per 2025-06-18 spec)
            result = response.get("result", {})
            if result != {}:
                raise ConnectionError(f"Ping response should be empty, got: {result}")
                
            return result
        except Exception as e:
            raise ConnectionError(f"Ping failed: {str(e)}") 