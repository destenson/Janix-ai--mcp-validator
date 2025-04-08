# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol adapter for MCP version 2025-03-26.

This module implements the protocol adapter for the 2025-03-26 version of the MCP protocol,
which includes async tool call capabilities.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter
from mcp_testing.transports.base import MCPTransportAdapter


class MCP2025_03_26Adapter(MCP2024_11_05Adapter):
    """
    Protocol adapter for MCP version 2025-03-26.
    
    This adapter implements the 2025-03-26 protocol version, which includes
    all features from 2024-11-05 plus async tool calls.
    """
    
    def __init__(self, transport: MCPTransportAdapter, debug: bool = False):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport adapter to use for communication
            debug: Whether to enable debug output
        """
        super().__init__(transport, debug)
        self.pending_tool_calls = {}
    
    @property
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string "2025-03-26"
        """
        return "2025-03-26"
    
    async def call_tool_async(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool asynchronously on the server.
        
        This method is specific to the 2025-03-26 protocol version, which supports
        asynchronous tool calls.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The initial response with a tool call ID
            
        Raises:
            ConnectionError: If the tool call fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot call tool before initialization")
            
        # Generate a unique ID for this tool call
        tool_call_id = str(uuid.uuid4())
            
        # Prepare the tools/call-async request
        request = {
            "jsonrpc": "2.0",
            "id": tool_call_id,
            "method": "tools/call-async",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Sending tools/call-async request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received tools/call-async response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Async tool call failed: {response['error']['message']}")
                
            # Store the tool call ID for later use
            self.pending_tool_calls[tool_call_id] = response.get("result", {})
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Async tool call failed: {str(e)}")
    
    async def get_tool_result(self, tool_call_id: str) -> Dict[str, Any]:
        """
        Get the result of an asynchronous tool call.
        
        Args:
            tool_call_id: The ID of the tool call to get the result for
            
        Returns:
            The tool's response
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot get tool result before initialization")
            
        # Prepare the tools/result request
        request = {
            "jsonrpc": "2.0",
            "id": f"result_{tool_call_id}",
            "method": "tools/result",
            "params": {
                "id": tool_call_id
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Sending tools/result request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received tools/result response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to get tool result: {response['error']['message']}")
                
            # If the tool call is complete, remove it from pending calls
            result = response.get("result", {})
            status = result.get("status")
            
            if status == "completed" or status == "error":
                if tool_call_id in self.pending_tool_calls:
                    del self.pending_tool_calls[tool_call_id]
                    
            return result
        except Exception as e:
            raise ConnectionError(f"Failed to get tool result: {str(e)}")
    
    async def cancel_tool_call(self, tool_call_id: str) -> Dict[str, Any]:
        """
        Cancel an asynchronous tool call.
        
        Args:
            tool_call_id: The ID of the tool call to cancel
            
        Returns:
            The cancellation response
            
        Raises:
            ConnectionError: If the request fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot cancel tool call before initialization")
            
        # Prepare the tools/cancel request
        request = {
            "jsonrpc": "2.0",
            "id": f"cancel_{tool_call_id}",
            "method": "tools/cancel",
            "params": {
                "id": tool_call_id
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Sending tools/cancel request: {json.dumps(request)}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received tools/cancel response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to cancel tool call: {response['error']['message']}")
                
            # Remove the tool call from pending calls
            if tool_call_id in self.pending_tool_calls:
                del self.pending_tool_calls[tool_call_id]
                
            return response.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Failed to cancel tool call: {str(e)}")
    
    async def wait_for_tool_completion(self, tool_call_id: str, timeout: float = 30.0, 
                                     poll_interval: float = 0.5) -> Dict[str, Any]:
        """
        Wait for an asynchronous tool call to complete.
        
        Args:
            tool_call_id: The ID of the tool call to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check for completion in seconds
            
        Returns:
            The tool's final response
            
        Raises:
            ConnectionError: If the request fails
            TimeoutError: If the tool call does not complete within the timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            result = await self.get_tool_result(tool_call_id)
            status = result.get("status")
            
            if status == "completed":
                return result
            elif status == "error":
                raise ConnectionError(f"Tool call failed: {result.get('error', {}).get('message', 'Unknown error')}")
                
            # Wait before polling again
            await asyncio.sleep(poll_interval)
            
        raise TimeoutError(f"Tool call did not complete within {timeout} seconds") 