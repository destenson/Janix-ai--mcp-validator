# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol adapter for MCP version 2025-03-26.

This module implements the protocol adapter for the 2025-03-26 version of the MCP protocol,
which adds support for asynchronous tool execution.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union, Tuple

from protocols.base import MCPProtocolAdapter


class MCP2025_03_26Adapter(MCPProtocolAdapter):
    """
    Protocol adapter for MCP version 2025-03-26.
    
    This adapter implements the 2025-03-26 version of the MCP protocol,
    which adds support for asynchronous tool execution.
    """
    
    def __init__(self, transport, debug: bool = False, async_poll_interval: float = 0.5,
                 async_timeout: float = 60.0):
        """
        Initialize the protocol adapter.
        
        Args:
            transport: The transport implementation to use for communication
            debug: Whether to enable debug logging
            async_poll_interval: How often to poll for async operation status (in seconds)
            async_timeout: Maximum time to wait for async operations (in seconds)
        """
        super().__init__(transport, debug)
        self.async_poll_interval = async_poll_interval
        self.async_timeout = async_timeout
        self.async_operations = {}  # Track ongoing async operations
    
    @property
    def version(self) -> str:
        """
        Return the protocol version supported by this adapter.
        
        Returns:
            The protocol version string "2025-03-26"
        """
        return "2025-03-26"
    
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
            client_capabilities = {
                "asyncToolCalls": True
            }
        elif "asyncToolCalls" not in client_capabilities:
            client_capabilities["asyncToolCalls"] = True
            
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
            
            # Check if the server supports our requested protocol version
            if self.protocol_version != self.version:
                print(f"Warning: Server supports protocol version {self.protocol_version}, "
                      f"but we requested {self.version}")
            
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
            
        # Check if server supports async
        supports_async = self.server_capabilities.get("asyncToolCalls", False)
        
        # Create a copy of the params to avoid modifying the original
        params_copy = params.copy() if params else {}
        
        # Add async flag if supported
        if supports_async:
            params_copy["async"] = True
        
        # In MCP, the method name is just the tool name (no namespace)
        # This is the spec-compliant way
        method = tool_name
        
        # Prepare the tool invocation request
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params_copy
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
                        "params": params_copy
                    }
                    
                    if self.debug:
                        print(f"Trying fallback format: {json.dumps(fallback_request)}")
                    
                    fallback_response = self.transport.send_request(fallback_request)
                    
                    if self.debug:
                        print(f"Fallback response: {json.dumps(fallback_response)}")
                    
                    if "error" not in fallback_response:
                        print(f"WARNING: Server accepted non-compliant method format: '{fallback}'")
                        result = fallback_response.get("result", {})
                        
                        # Check if this is an async response
                        if supports_async and "asyncOperationId" in result:
                            operation_id = result["asyncOperationId"]
                            return await self._wait_for_async_operation(operation_id)
                        
                        return result
                
                # If all fallbacks fail, raise the original error
                raise ConnectionError(f"Tool invocation failed: {response['error']['message']} - Server is non-compliant with MCP specification")
            
            # Any other error is a failure
            if "error" in response:
                raise ConnectionError(f"Tool invocation failed: {response['error']['message']}")
                
            result = response.get("result", {})
            
            # Check if this is an async response
            if supports_async and "asyncOperationId" in result:
                operation_id = result["asyncOperationId"]
                return await self._wait_for_async_operation(operation_id)
            
            return result
        except Exception as e:
            raise ConnectionError(f"Tool invocation failed: {str(e)}")
    
    async def _wait_for_async_operation(self, operation_id: str) -> Any:
        """
        Wait for an asynchronous operation to complete.
        
        Args:
            operation_id: The ID of the async operation to wait for
            
        Returns:
            The operation's result
            
        Raises:
            ConnectionError: If polling fails
            TimeoutError: If the operation times out
        """
        if self.debug:
            print(f"Waiting for async operation {operation_id} to complete")
            
        start_time = time.time()
        while True:
            # Check if we've exceeded the timeout
            elapsed = time.time() - start_time
            if elapsed > self.async_timeout:
                raise TimeoutError(f"Async operation {operation_id} timed out after {elapsed:.1f} seconds")
                
            # Poll for operation status
            status, result = await self._poll_async_operation(operation_id)
            
            if status == "completed":
                if self.debug:
                    print(f"Async operation {operation_id} completed successfully")
                return result
            elif status == "failed":
                error_message = result.get("error", {}).get("message", "Unknown error")
                raise ConnectionError(f"Async operation {operation_id} failed: {error_message}")
                
            # Wait before polling again
            await asyncio.sleep(self.async_poll_interval)
    
    async def _poll_async_operation(self, operation_id: str) -> Tuple[str, Any]:
        """
        Poll for the status of an asynchronous operation.
        
        Args:
            operation_id: The ID of the async operation to poll
            
        Returns:
            A tuple containing the operation status and result
            
        Raises:
            ConnectionError: If polling fails
        """
        # Prepare the tools/status request
        request = {
            "jsonrpc": "2.0",
            "id": f"status_{operation_id}",
            "method": "tools/status",
            "params": {
                "operationId": operation_id
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Polling async operation {operation_id}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received status response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to poll operation: {response['error']['message']}")
                
            result = response.get("result", {})
            status = result.get("status", "unknown")
            
            return status, result.get("result", {})
        except Exception as e:
            raise ConnectionError(f"Failed to poll operation: {str(e)}")
    
    async def cancel_async_operation(self, operation_id: str) -> bool:
        """
        Cancel an ongoing asynchronous operation.
        
        Args:
            operation_id: The ID of the async operation to cancel
            
        Returns:
            True if the operation was cancelled, False otherwise
            
        Raises:
            ConnectionError: If cancellation fails
        """
        if not self.initialized:
            raise ConnectionError("Cannot cancel operation before initialization")
            
        # Prepare the tools/cancel request
        request = {
            "jsonrpc": "2.0",
            "id": f"cancel_{operation_id}",
            "method": "tools/cancel",
            "params": {
                "operationId": operation_id
            }
        }
        
        # Send the request
        if self.debug:
            print(f"Cancelling async operation {operation_id}")
            
        try:
            response = self.transport.send_request(request)
            
            if self.debug:
                print(f"Received cancel response: {json.dumps(response)}")
                
            if "error" in response:
                raise ConnectionError(f"Failed to cancel operation: {response['error']['message']}")
                
            return response.get("result", {}).get("cancelled", False)
        except Exception as e:
            raise ConnectionError(f"Failed to cancel operation: {str(e)}")
    
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