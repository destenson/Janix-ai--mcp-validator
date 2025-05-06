#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Protocol Handlers for MCP HTTP Server

This module defines the protocol handlers for different MCP protocol versions.
"""

import abc
import logging
import time
from typing import Dict, Any, Optional, List, Tuple

# Use relative import for session_manager
from .session_manager import Session

logger = logging.getLogger('MCPHTTPServer.Protocol')

# Basic tool definitions shared across protocol versions
COMMON_TOOLS = [
    {
        "name": "echo",
        "description": "Echo back the message sent to the server",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "add",
        "description": "Add two numbers together",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "sleep",
        "description": "Sleep for a specified number of seconds",
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "Number of seconds to sleep"
                }
            },
            "required": ["seconds"]
        }
    }
]

# Resource definitions (for 2025-03-26)
RESOURCES = [
    {
        "id": "example",
        "name": "Example Resource",
        "uri": "https://example.com/resource",
        "description": "An example resource for testing"
    }
]

class MCPError(Exception):
    """Exception class for MCP protocol errors."""
    
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class ProtocolHandler(abc.ABC):
    """
    Abstract base class for protocol handlers.
    
    This class defines the interface that all protocol handlers must implement.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the protocol handler.
        
        Args:
            session: The session this handler is associated with.
        """
        self.session = session
        self.version = None
    
    @abc.abstractmethod
    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a request.
        
        Args:
            method: The method name.
            params: The method parameters.
            
        Returns:
            Dict[str, Any]: The result of the request.
            
        Raises:
            MCPError: If the request cannot be handled.
        """
        pass
    
    @abc.abstractmethod
    def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the protocol handler.
        
        Args:
            params: The initialization parameters.
            
        Returns:
            Dict[str, Any]: The initialization result.
            
        Raises:
            MCPError: If initialization fails.
        """
        pass
    
    @abc.abstractmethod
    def get_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get server information.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The server information.
            
        Raises:
            MCPError: If the information cannot be retrieved.
        """
        pass
    
    @abc.abstractmethod
    def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available tools.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The list of available tools.
            
        Raises:
            MCPError: If the tools cannot be listed.
        """
        pass
    
    @abc.abstractmethod
    def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the tool call.
            
        Raises:
            MCPError: If the tool call fails.
        """
        pass
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.
            
        Returns:
            Dict[str, Any]: The result of the tool execution.
            
        Raises:
            MCPError: If the tool execution fails.
        """
        # Find the tool definition
        tool = next((t for t in COMMON_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise MCPError(-32602, f"Unknown tool: {tool_name}")
        
        # Execute the tool based on its name
        if tool_name == "echo":
            if "message" not in arguments:
                raise MCPError(-32602, "Missing required parameter: message")
            return {"message": arguments["message"]}
        
        elif tool_name == "add":
            if "a" not in arguments or "b" not in arguments:
                raise MCPError(-32602, "Missing required parameters: a, b")
            
            try:
                a = float(arguments["a"])
                b = float(arguments["b"])
                return {"result": a + b}
            except (ValueError, TypeError):
                raise MCPError(-32602, "Invalid parameters: a and b must be numbers")
        
        elif tool_name == "sleep":
            if "seconds" not in arguments:
                raise MCPError(-32602, "Missing required parameter: seconds")
            
            try:
                seconds = float(arguments["seconds"])
                if seconds > 10:  # Limit sleep time for safety
                    seconds = 10
                time.sleep(seconds)
                return {"slept": seconds}
            except (ValueError, TypeError):
                raise MCPError(-32602, "Invalid parameter: seconds must be a number")
        
        else:
            raise MCPError(-32601, f"Tool not implemented: {tool_name}")


class Protocol_2024_11_05(ProtocolHandler):
    """
    Protocol handler for the 2024-11-05 version of the MCP protocol.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the protocol handler.
        
        Args:
            session: The session this handler is associated with.
        """
        super().__init__(session)
        self.version = "2024-11-05"
    
    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a request.
        
        Args:
            method: The method name.
            params: The method parameters.
            
        Returns:
            Dict[str, Any]: The result of the request.
            
        Raises:
            MCPError: If the request cannot be handled.
        """
        # Check for initialization
        if not self.session.initialized and method != "initialize":
            raise MCPError(-32003, "Session not initialized")
        
        # Route to appropriate method handler
        if method == "initialize":
            return self.initialize(params)
        elif method == "server/info":
            return self.get_server_info(params)
        elif method == "tools/list":
            return self.list_tools(params)
        elif method == "tools/call":
            return self.call_tool(params)
        else:
            raise MCPError(-32601, f"Method not found: {method}")
    
    def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the protocol handler.
        
        Args:
            params: The initialization parameters.
            
        Returns:
            Dict[str, Any]: The initialization result.
            
        Raises:
            MCPError: If initialization fails.
        """
        # Validate required parameters
        if "protocolVersion" not in params:
            raise MCPError(-32602, "Missing required parameter: protocolVersion")
        
        if "clientInfo" not in params:
            raise MCPError(-32602, "Missing required parameter: clientInfo")
        
        if params["protocolVersion"] != self.version:
            raise MCPError(-32602, f"Unsupported protocol version: {params['protocolVersion']}")
        
        # Update session with client info
        self.session.client_info = params.get("clientInfo", {})
        self.session.capabilities = params.get("capabilities", {})
        self.session.protocol_version = self.version
        self.session.initialized = True
        
        # Return initialization result
        return {
            "serverInfo": {
                "name": "MCP HTTP Server",
                "version": "2.0.0",
                "protocolVersion": self.version
            },
            "capabilities": {
                "protocolVersion": self.version,
                "tools": True
            },
            "session": {
                "id": self.session.id
            }
        }
    
    def get_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get server information.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The server information.
        """
        return {
            "name": "MCP HTTP Server",
            "version": "2.0.0",
            "supportedVersions": ["2024-11-05", "2025-03-26"]
        }
    
    def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available tools.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The list of available tools.
        """
        # Convert tools to 2024-11-05 format (using inputSchema instead of parameters)
        tools = []
        for tool in COMMON_TOOLS:
            tool_copy = tool.copy()
            if "parameters" in tool_copy:
                tool_copy["inputSchema"] = tool_copy.pop("parameters")
            tools.append(tool_copy)
        
        return {"tools": tools}
    
    def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the tool call.
            
        Raises:
            MCPError: If the tool call fails.
        """
        # Validate required parameters
        if "name" not in params:
            raise MCPError(-32602, "Missing required parameter: name")
        
        tool_name = params["name"]
        # In 2024-11-05, tool arguments are under the "arguments" key
        arguments = params.get("arguments", {})
        
        # Execute the tool
        result = self._execute_tool(tool_name, arguments)
        
        return result


class Protocol_2025_03_26(ProtocolHandler):
    """
    Protocol handler for the 2025-03-26 version of the MCP protocol.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the protocol handler.
        
        Args:
            session: The session this handler is associated with.
        """
        super().__init__(session)
        self.version = "2025-03-26"
    
    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a request.
        
        Args:
            method: The method name.
            params: The method parameters.
            
        Returns:
            Dict[str, Any]: The result of the request.
            
        Raises:
            MCPError: If the request cannot be handled.
        """
        # Check for initialization
        if not self.session.initialized and method != "initialize":
            raise MCPError(-32003, "Session not initialized")
        
        # Route to appropriate method handler
        if method == "initialize":
            return self.initialize(params)
        elif method == "server/info":
            return self.get_server_info(params)
        elif method == "tools/list":
            return self.list_tools(params)
        elif method == "tools/call":
            return self.call_tool(params)
        elif method == "tools/call-async":
            return self.call_tool_async(params)
        elif method == "tools/result":
            return self.get_tool_result(params)
        elif method == "tools/cancel":
            return self.cancel_tool(params)
        elif method == "resources/list":
            return self.list_resources(params)
        elif method == "resources/get":
            return self.get_resource(params)
        elif method == "notifications/send":
            return self.send_notification(params)
        else:
            raise MCPError(-32601, f"Method not found: {method}")
    
    def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the protocol handler.
        
        Args:
            params: The initialization parameters.
            
        Returns:
            Dict[str, Any]: The initialization result.
            
        Raises:
            MCPError: If initialization fails.
        """
        # Validate required parameters
        if "protocolVersion" not in params:
            raise MCPError(-32602, "Missing required parameter: protocolVersion")
        
        if "clientInfo" not in params:
            raise MCPError(-32602, "Missing required parameter: clientInfo")
        
        if "capabilities" not in params:
            raise MCPError(-32602, "Missing required parameter: capabilities")
        
        if params["protocolVersion"] != self.version:
            raise MCPError(-32602, f"Unsupported protocol version: {params['protocolVersion']}")
        
        # Update session with client info and capabilities
        self.session.client_info = params.get("clientInfo", {})
        self.session.capabilities = params.get("capabilities", {})
        self.session.protocol_version = self.version
        self.session.initialized = True
        
        # Get client capabilities
        client_async_support = params.get("capabilities", {}).get("tools", {}).get("asyncSupported", False)
        
        # Return initialization result
        return {
            "serverInfo": {
                "name": "MCP HTTP Server",
                "version": "2.0.0",
                "protocolVersion": self.version
            },
            "capabilities": {
                "protocolVersion": self.version,
                "tools": {
                    "asyncSupported": True
                },
                "resources": True
            },
            "session": {
                "id": self.session.id
            }
        }
    
    def get_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get server information.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The server information.
        """
        return {
            "name": "MCP HTTP Server",
            "version": "2.0.0",
            "supportedVersions": ["2024-11-05", "2025-03-26"]
        }
    
    def list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available tools.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The list of available tools.
        """
        # In 2025-03-26, the tools are returned as-is with "parameters"
        return {"tools": COMMON_TOOLS}
    
    def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the tool call.
            
        Raises:
            MCPError: If the tool call fails.
        """
        # Validate required parameters
        if "name" not in params:
            raise MCPError(-32602, "Missing required parameter: name")
        
        tool_name = params["name"]
        # In 2025-03-26, tool arguments are under the "parameters" key
        arguments = params.get("parameters", {})
        
        # Execute the tool
        result = self._execute_tool(tool_name, arguments)
        
        return result
    
    def call_tool_async(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool asynchronously.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the asynchronous tool call.
            
        Raises:
            MCPError: If the asynchronous tool call fails.
        """
        # Validate required parameters
        if "name" not in params:
            raise MCPError(-32602, "Missing required parameter: name")
        
        tool_name = params["name"]
        # In 2025-03-26, tool arguments are under the "parameters" key
        arguments = params.get("parameters", {})
        
        # Find the tool definition
        tool = next((t for t in COMMON_TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise MCPError(-32602, f"Unknown tool: {tool_name}")
        
        # Generate a unique ID for this async call
        import uuid
        call_id = str(uuid.uuid4())
        
        # Store the call info in the session
        self.session.pending_async_calls[call_id] = {
            "tool": tool_name,
            "arguments": arguments,
            "status": "running",
            "start_time": time.time(),
            "result": None
        }
        
        # For the sleep tool, we'll simulate a real async operation
        if tool_name == "sleep" and "seconds" in arguments:
            self.session.pending_async_calls[call_id]["sleep_seconds"] = float(arguments["seconds"])
        
        # Return the call ID
        return {"id": call_id}
    
    def get_tool_result(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the result of an asynchronous tool call.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the asynchronous tool call.
            
        Raises:
            MCPError: If the result cannot be retrieved.
        """
        # Validate required parameters
        if "id" not in params:
            raise MCPError(-32602, "Missing required parameter: id")
        
        call_id = params["id"]
        
        # Check if the call exists
        if call_id not in self.session.pending_async_calls:
            raise MCPError(-32602, f"Unknown async call: {call_id}")
        
        # Get the call info
        call_info = self.session.pending_async_calls[call_id]
        
        # If it's a sleep call, check if it's completed
        if call_info["tool"] == "sleep" and "sleep_seconds" in call_info:
            elapsed = time.time() - call_info["start_time"]
            if elapsed >= call_info["sleep_seconds"]:
                call_info["status"] = "completed"
                call_info["result"] = self._execute_tool(call_info["tool"], call_info["arguments"])
        
        # Return the status and result
        result = {
            "status": call_info["status"]
        }
        
        if call_info["status"] == "completed":
            result["result"] = call_info["result"]
        elif call_info["status"] == "error":
            result["error"] = call_info.get("error", {"message": "Unknown error"})
        
        return result
    
    def cancel_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cancel an asynchronous tool call.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of the cancellation.
            
        Raises:
            MCPError: If the cancellation fails.
        """
        # Validate required parameters
        if "id" not in params:
            raise MCPError(-32602, "Missing required parameter: id")
        
        call_id = params["id"]
        
        # Check if the call exists
        if call_id not in self.session.pending_async_calls:
            return {"success": False, "message": f"Unknown async call: {call_id}"}
        
        # Get the call info
        call_info = self.session.pending_async_calls[call_id]
        
        # Check if it's already completed
        if call_info["status"] in ["completed", "error", "cancelled"]:
            return {"success": False, "message": f"Call already in state: {call_info['status']}"}
        
        # Cancel the call
        call_info["status"] = "cancelled"
        
        return {"success": True}
    
    def list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available resources.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The list of available resources.
        """
        return {"resources": RESOURCES}
    
    def get_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a resource.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The requested resource.
            
        Raises:
            MCPError: If the resource cannot be found.
        """
        # Validate required parameters
        if "id" not in params:
            raise MCPError(-32602, "Missing required parameter: id")
        
        resource_id = params["id"]
        
        # Find the resource
        resource = next((r for r in RESOURCES if r["id"] == resource_id), None)
        if not resource:
            raise MCPError(-32602, f"Resource not found: {resource_id}")
        
        return resource
    
    def send_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            params: The request parameters.
            
        Returns:
            Dict[str, Any]: The result of sending the notification.
            
        Raises:
            MCPError: If the notification cannot be sent.
        """
        # Validate required parameters
        if "type" not in params:
            raise MCPError(-32602, "Missing required parameter: type")
        
        if "data" not in params:
            raise MCPError(-32602, "Missing required parameter: data")
        
        # We'll just acknowledge the notification for now
        # In a real implementation, this would send the notification to the client
        return {"success": True}


class ProtocolHandlerFactory:
    """
    Factory for creating protocol handlers.
    """
    
    @staticmethod
    def create_handler(session: Session, version: Optional[str] = None) -> ProtocolHandler:
        """
        Create a protocol handler for the specified version.
        
        Args:
            session: The session to associate with the handler.
            version: The protocol version to create a handler for.
                If None, the session's protocol version will be used.
                
        Returns:
            ProtocolHandler: A protocol handler for the specified version.
            
        Raises:
            ValueError: If the specified version is not supported.
        """
        # Use the session's protocol version if none is specified
        if version is None:
            version = session.protocol_version
        
        # If the session doesn't have a protocol version yet, default to the latest
        if version is None:
            version = "2025-03-26"
        
        # Create the appropriate handler
        if version == "2024-11-05":
            return Protocol_2024_11_05(session)
        elif version == "2025-03-26":
            return Protocol_2025_03_26(session)
        else:
            raise ValueError(f"Unsupported protocol version: {version}") 