#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Minimal HTTP MCP Server

This is a minimal implementation of the MCP (Model Conversation Protocol) over HTTP.
It supports both the 2024-11-05 and 2025-03-26 protocol versions.
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional, Union, Tuple
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MinimalHTTPMCPServer')

# Server state
server_state = {
    "initialized": False,
    "protocol_version": None,
    "pending_async_calls": {},
    "resources": {},
    "shutdown_requested": False,
    "sessions": {},  # Track active sessions
    "sse_connections": []  # Track SSE connections
}

# Supported protocol versions
SUPPORTED_VERSIONS = ["2024-11-05", "2025-03-26"]

# Basic tool definitions
TOOLS = [
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

class JSONRPCError(Exception):
    """Exception class for JSON-RPC errors."""
    
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP protocol."""
    
    protocol_version = 'HTTP/1.1'
    
    def log_message(self, format, *args):
        """Override log_message to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        # Only handle OPTIONS requests to /mcp path
        if self.path != "/mcp":
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
            
        self.send_response(200)
        self.send_header('Allow', 'OPTIONS, POST, GET, DELETE')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        self.end_headers()
    
    def do_DELETE(self):
        """Handle DELETE requests for ending sessions."""
        # Only handle DELETE requests to /mcp path
        if self.path != "/mcp":
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
            
        # Check if this is a session termination request
        session_id = self.headers.get('Mcp-Session-Id')
        if session_id and session_id in server_state["sessions"]:
            # Remove the session
            del server_state["sessions"][session_id]
            logger.info(f"Session terminated: {session_id}")
            self.send_response(204)  # No Content
            self.end_headers()
        else:
            self._send_error(404, "Session not found")
    
    def do_GET(self):
        """Handle GET requests for SSE streaming."""
        # Only handle GET requests to /mcp path
        if self.path != "/mcp":
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
        
        # Any path is acceptable for the SSE endpoint
        # Check if client accepts SSE
        accept_header = self.headers.get('Accept', '')
        if 'text/event-stream' not in accept_header:
            self._send_error(406, "Not Acceptable: Client must accept text/event-stream")
            return
            
        # Set up SSE response
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Create a message queue for this connection
        message_queue = queue.Queue()
        
        # Add this connection to the list of SSE connections
        connection_id = str(uuid.uuid4())
        
        # If session ID is provided, associate this connection with the session
        session_id = self._get_session_id()
        
        connection_info = {
            "id": connection_id,
            "queue": message_queue,
            "wfile": self.wfile,
            "session_id": session_id,
            "created": time.time()
        }
        
        server_state["sse_connections"].append(connection_info)
        
        logger.info(f"SSE connection established: {connection_id} for session: {session_id}")
        
        try:
            # Send initial connection message
            self.wfile.write(f"event: connected\ndata: {{'connectionId': '{connection_id}'}}\n\n".encode('utf-8'))
            self.wfile.flush()
            
            # Keep the connection open
            while not server_state["shutdown_requested"]:
                try:
                    # Check for messages in the queue (non-blocking)
                    try:
                        message = message_queue.get(block=True, timeout=1.0)
                        
                        # Format the message as an SSE event
                        event_type = message.get("event", "message")
                        message_data = json.dumps(message.get("data", {}))
                        
                        # Send the message as an SSE event
                        self.wfile.write(f"event: {event_type}\ndata: {message_data}\n\n".encode('utf-8'))
                        self.wfile.flush()
                        
                    except queue.Empty:
                        # Send a keep-alive comment every second
                        self.wfile.write(": keep-alive\n\n".encode('utf-8'))
                        self.wfile.flush()
                        
                except (BrokenPipeError, ConnectionResetError):
                    # Connection closed by client
                    break
        
        except Exception as e:
            logger.error(f"SSE connection error: {str(e)}")
            
        finally:
            # Remove this connection from the list
            server_state["sse_connections"] = [
                conn for conn in server_state["sse_connections"]
                if conn["id"] != connection_id
            ]
            logger.info(f"SSE connection closed: {connection_id}")
    
    def do_POST(self):
        """Handle POST requests containing JSON-RPC requests."""
        try:
            # According to the 2025-03-26 MCP spec, all MCP requests should go to /mcp endpoint
            # Debug: Print all request information
            logger.debug(f"Received POST request to path: {self.path}")
            logger.debug(f"Headers: {dict(self.headers)}")
            
            # Check that this is a request to the MCP endpoint
            if self.path != "/mcp":
                self._send_error(404, "Not Found - MCP endpoint is at /mcp")
                return
            
            # Check Accept header
            accept_header = self.headers.get('Accept', 'application/json')
            supports_json = 'application/json' in accept_header
            supports_sse = 'text/event-stream' in accept_header
            logger.debug(f"Accept header: {accept_header} (JSON: {supports_json}, SSE: {supports_sse})")
            
            # Content-Type check - more lenient
            content_type = self.headers.get('Content-Type', '')
            logger.debug(f"Content-Type: {content_type}")
            
            # Get content length from headers
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(400, "Content-Length header is required")
                return
            
            # Read the request body
            request_body = self.rfile.read(content_length).decode('utf-8')
            logger.debug(f"Received request body: {request_body}")
            
            # Parse the request as JSON
            try:
                if request_body.strip().startswith('['):
                    # Handle batch request
                    request_data = json.loads(request_body)
                    if not isinstance(request_data, list):
                        self._send_error(400, "Invalid batch request format")
                        return
                    
                    # Process each request in the batch
                    responses = []
                    notifications_only = True
                    
                    for request in request_data:
                        response = self._process_request(request)
                        if response:  # Only add responses for non-notifications
                            responses.append(response)
                            notifications_only = False
                    
                    # Send appropriate response
                    if notifications_only:
                        # If only notifications, return 202 Accepted with no body
                        self._send_response(202, None)
                    else:
                        # Send batch response
                        self._send_response(200, responses, 
                                          content_type="text/event-stream" if supports_sse else "application/json")
                else:
                    # Handle single request
                    request_data = json.loads(request_body)
                    response = self._process_request(request_data)
                    
                    # Send response (if not a notification)
                    if response:
                        # If client supports SSE and this is a request (not a response),
                        # consider using SSE for the response
                        if supports_sse and "method" in request_data:
                            self._send_response(200, response, content_type="text/event-stream")
                        else:
                            self._send_response(200, response, content_type="application/json")
                    else:
                        # For notifications, send an empty 202 response
                        self._send_response(202, None)
                
                # Check if shutdown was requested
                if server_state["shutdown_requested"]:
                    logger.info("Shutdown requested, stopping server")
                    # Use a thread to avoid blocking the current request
                    threading.Thread(target=stop_server).start()
                
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON")
                
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}")
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def _send_response(self, status_code: int, data: Any, content_type: str = "application/json"):
        """Send an HTTP response with the given status code and data."""
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        
        # Check if we have a session ID to include in the response
        if hasattr(self, 'session_id'):
            self.send_header('Mcp-Session-Id', self.session_id)
        
        if data is not None:
            self.send_header('Content-Type', content_type)
            response_json = json.dumps(data)
            response_bytes = response_json.encode('utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        else:
            self.end_headers()
    
    def _send_error(self, status_code: int, message: str):
        """Send an HTTP error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        error_data = {"error": message}
        error_json = json.dumps(error_data)
        error_bytes = error_json.encode('utf-8')
        self.send_header('Content-Length', str(len(error_bytes)))
        self.end_headers()
        self.wfile.write(error_bytes)
    
    def _get_session_id(self):
        """Get the session ID from headers."""
        return self.headers.get('Mcp-Session-Id')
    
    def _verify_session(self):
        """Verify the session ID is valid."""
        session_id = self._get_session_id()
        if not session_id:
            return False
            
        # Check if session exists
        if session_id not in server_state["sessions"]:
            return False
            
        return True
    
    def _process_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a JSON-RPC request and return a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object, or None for notifications
        """
        try:
            # Validate JSON-RPC request format
            if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
                raise JSONRPCError(-32600, "Invalid Request: jsonrpc field must be '2.0'")
            
            # Check if it's a notification (no id)
            is_notification = "id" not in request
            
            # Get the method and params
            if "method" not in request:
                raise JSONRPCError(-32600, "Invalid Request: method field is required")
            
            method = request["method"]
            params = request.get("params", {})
            request_id = request.get("id")
            
            # For methods other than initialize, verify session if required
            if method != "initialize" and server_state["initialized"]:
                # If we have active sessions, require session ID
                if server_state["sessions"] and not self._verify_session():
                    raise JSONRPCError(-32000, "Invalid or missing session ID")
            
            # Process the method
            result = self._handle_method(method, params)
            
            # Return the response (unless it's a notification)
            if not is_notification:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            else:
                return None
                
        except JSONRPCError as e:
            # Return JSON-RPC error response (unless it's a notification)
            if "id" in request:
                error_data = {"code": e.code, "message": e.message}
                if e.data:
                    error_data["data"] = e.data
                
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": error_data
                }
            else:
                return None
    
    def _handle_method(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Handle a JSON-RPC method call.
        
        Args:
            method: The method name
            params: The method parameters
            
        Returns:
            The method result
            
        Raises:
            JSONRPCError: If the method is invalid or fails
        """
        # Check if the server is initialized (except for initialize method)
        if method != "initialize" and not server_state["initialized"]:
            raise JSONRPCError(-32803, "Server not initialized")
        
        # Initialize method
        if method == "initialize":
            return self._handle_initialize(params)
        
        # Handle shutdown request
        elif method == "shutdown":
            return self._handle_shutdown(params)
        
        # Server info
        elif method == "server/info":
            return self._handle_server_info(params)
        
        # Tools methods (depends on protocol version)
        elif method == "tools/list" or method == "mcp/tools":
            return self._handle_tools_list(params)
        
        elif method == "tools/call" or method == "mcp/tools/call":
            return self._handle_tools_call(params)
        
        # 2025-03-26 async tools methods
        elif (method == "tools/call-async" or method == "mcp/tools/async") and server_state["protocol_version"] == "2025-03-26":
            return self._handle_tools_call_async(params)
            
        elif method == "tools/result" and server_state["protocol_version"] == "2025-03-26":
            return self._handle_tools_result(params)
            
        elif method == "tools/cancel" and server_state["protocol_version"] == "2025-03-26":
            return self._handle_tools_cancel(params)
        
        # 2025-03-26 resources methods
        elif method == "resources/list" and server_state["protocol_version"] == "2025-03-26":
            return self._handle_resources_list(params)
            
        elif method == "resources/get" and server_state["protocol_version"] == "2025-03-26":
            return self._handle_resources_get(params)
        
        # SSE methods
        elif method == "notifications/send" and server_state["protocol_version"] == "2025-03-26":
            return self._handle_send_notification(params)
        
        # Handle individual tool calls (direct method call)
        elif any(tool["name"] == method for tool in TOOLS):
            return self._call_tool(method, params)
        
        # Unknown method
        else:
            raise JSONRPCError(-32601, f"Method not found: {method}")
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the initialize method.
        
        Args:
            params: The method parameters
            
        Returns:
            The initialization result
            
        Raises:
            JSONRPCError: If initialization fails
        """
        if server_state["initialized"]:
            raise JSONRPCError(-32803, "Server already initialized")
        
        # Check protocol version
        protocol_version = params.get("protocolVersion")
        if not protocol_version or protocol_version not in SUPPORTED_VERSIONS:
            raise JSONRPCError(-32602, f"Unsupported protocol version: {protocol_version}")
        
        # Get client capabilities
        client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        # Set server state
        server_state["initialized"] = True
        server_state["protocol_version"] = protocol_version
        
        # Generate a session ID (visible ASCII characters only)
        session_id = str(uuid.uuid4())
        
        # Store session info
        server_state["sessions"][session_id] = {
            "created": time.time(),
            "client_info": client_info,
            "protocol_version": protocol_version
        }
        
        # Store the session ID to be included in the response headers later
        # We can't directly send headers here as they must be sent before the body
        # The _send_response method will add this header
        self.session_id = session_id
        
        # Prepare server capabilities
        server_capabilities = {
            "tools": True
        }
        
        # Add 2025-03-26 specific capabilities
        if protocol_version == "2025-03-26":
            server_capabilities["tools"] = {
                "asyncSupported": True
            }
            server_capabilities["resources"] = True
        
        # Return initialization result
        return {
            "protocolVersion": protocol_version,
            "serverInfo": {
                "name": "Minimal MCP HTTP Server",
                "version": "1.0.0",
                "supportedVersions": SUPPORTED_VERSIONS
            },
            "capabilities": server_capabilities
        }
    
    def _handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the shutdown method.
        
        Args:
            params: The method parameters
            
        Returns:
            An empty result
        """
        # Set shutdown flag (will exit after response is sent)
        server_state["shutdown_requested"] = True
        return {}
    
    def _handle_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the server/info method.
        
        Args:
            params: The method parameters
            
        Returns:
            Server information
        """
        return {
            "name": "Minimal MCP HTTP Server",
            "version": "1.0.0",
            "supportedVersions": SUPPORTED_VERSIONS
        }
    
    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/list method.
        
        Args:
            params: The method parameters
            
        Returns:
            List of available tools
        """
        # Adapt tool format for 2024-11-05 if needed
        tools_list = []
        for tool in TOOLS:
            tool_copy = tool.copy()
            
            # For 2024-11-05, convert 'parameters' to 'inputSchema'
            if server_state["protocol_version"] == "2024-11-05":
                if "parameters" in tool_copy:
                    tool_copy["inputSchema"] = tool_copy.pop("parameters")
            
            tools_list.append(tool_copy)
        
        return {"tools": tools_list}
    
    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/call method.
        
        Args:
            params: The method parameters
            
        Returns:
            The tool call result
            
        Raises:
            JSONRPCError: If the tool call fails
        """
        # Validate params
        if "name" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: name")
        
        tool_name = params["name"]
        
        # Get the tool arguments based on protocol version
        if server_state["protocol_version"] == "2025-03-26":
            arguments = params.get("parameters", {})
        else:
            arguments = params.get("arguments", {})
        
        # Call the tool
        return self._call_tool(tool_name, arguments)
    
    def _handle_tools_call_async(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/call-async method (2025-03-26 only).
        
        Args:
            params: The method parameters
            
        Returns:
            The async task ID
            
        Raises:
            JSONRPCError: If the async tool call fails
        """
        # Validate params
        if "name" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: name")
        
        tool_name = params["name"]
        arguments = params.get("parameters", {})
        
        # Find the tool
        tool = next((t for t in TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise JSONRPCError(-32602, f"Unknown tool: {tool_name}")
        
        # Generate a unique ID for this async call
        call_id = str(uuid.uuid4())
        
        # Store task info
        server_state["pending_async_calls"][call_id] = {
            "tool": tool_name,
            "arguments": arguments,
            "status": "running",
            "start_time": time.time(),
            "result": None
        }
        
        # For "sleep" tool, actually sleep in a separate thread
        if tool_name == "sleep" and "seconds" in arguments:
            # In a real server, we would start a thread to execute this
            # For this simple example, we'll just record the parameters
            # and simulate the behavior in the result method
            server_state["pending_async_calls"][call_id]["sleep_seconds"] = float(arguments["seconds"])
        
        # Return the task ID
        return {"id": call_id}
    
    def _handle_tools_result(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/result method (2025-03-26 only).
        
        Args:
            params: The method parameters
            
        Returns:
            The tool result status
            
        Raises:
            JSONRPCError: If the result check fails
        """
        # Validate params
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id")
        
        call_id = params["id"]
        
        # Check if the call exists
        if call_id not in server_state["pending_async_calls"]:
            raise JSONRPCError(-32602, f"Unknown async call: {call_id}")
        
        # Get call info
        call_info = server_state["pending_async_calls"][call_id]
        
        # Check if it's a sleep call and simulate completion
        if call_info["tool"] == "sleep" and "sleep_seconds" in call_info:
            elapsed = time.time() - call_info["start_time"]
            if elapsed >= call_info["sleep_seconds"]:
                call_info["status"] = "completed"
                call_info["result"] = None
        
        # Return status and result
        result = {
            "status": call_info["status"]
        }
        
        if call_info["status"] == "completed":
            result["result"] = self._call_tool(call_info["tool"], call_info["arguments"])
        elif call_info["status"] == "error":
            result["error"] = call_info.get("error", {"message": "Unknown error"})
        
        return result
    
    def _handle_tools_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/cancel method (2025-03-26 only).
        
        Args:
            params: The method parameters
            
        Returns:
            Cancellation success status
            
        Raises:
            JSONRPCError: If the cancellation fails
        """
        # Validate params
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id")
        
        call_id = params["id"]
        
        # Check if the call exists
        if call_id not in server_state["pending_async_calls"]:
            return {"success": False, "message": f"Unknown async call: {call_id}"}
        
        # Get call info
        call_info = server_state["pending_async_calls"][call_id]
        
        # Check if already completed
        if call_info["status"] in ["completed", "error", "cancelled"]:
            return {"success": False, "message": f"Call already in state: {call_info['status']}"}
        
        # Cancel the call
        call_info["status"] = "cancelled"
        
        return {"success": True}
    
    def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the resources/list method (2025-03-26 only).
        
        Args:
            params: The method parameters
            
        Returns:
            List of available resources
        """
        return {"resources": RESOURCES}
    
    def _handle_resources_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the resources/get method (2025-03-26 only).
        
        Args:
            params: The method parameters
            
        Returns:
            The requested resource
            
        Raises:
            JSONRPCError: If the resource is not found
        """
        # Validate params
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id")
        
        resource_id = params["id"]
        
        # Find the resource
        resource = next((r for r in RESOURCES if r["id"] == resource_id), None)
        if not resource:
            raise JSONRPCError(-32602, f"Resource not found: {resource_id}")
        
        return resource
    
    def _handle_send_notification(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle sending a notification via SSE.
        
        Args:
            params: The notification parameters
            
        Returns:
            Success status
            
        Raises:
            JSONRPCError: If sending fails
        """
        # Validate params
        if "event" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: event")
        
        if "data" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: data")
        
        # Get target session ID (optional)
        target_session = params.get("sessionId")
        
        # Broadcast or send to specific session
        sent_count = 0
        
        if target_session:
            # Send to specific session
            for conn in server_state["sse_connections"]:
                if conn.get("session_id") == target_session:
                    try:
                        conn["queue"].put({
                            "event": params["event"],
                            "data": params["data"]
                        })
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send notification to connection {conn['id']}: {str(e)}")
        else:
            # Broadcast to all connections
            for conn in server_state["sse_connections"]:
                try:
                    conn["queue"].put({
                        "event": params["event"],
                        "data": params["data"]
                    })
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to connection {conn['id']}: {str(e)}")
        
        return {
            "success": sent_count > 0,
            "sentCount": sent_count
        }
    
    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool with the given arguments.
        
        Args:
            tool_name: The name of the tool to call
            arguments: The tool arguments
            
        Returns:
            The tool result
            
        Raises:
            JSONRPCError: If the tool call fails
        """
        # Find the tool
        tool = next((t for t in TOOLS if t["name"] == tool_name), None)
        if not tool:
            raise JSONRPCError(-32602, f"Unknown tool: {tool_name}")
        
        # Execute the tool
        if tool_name == "echo":
            if "message" not in arguments:
                raise JSONRPCError(-32602, "Missing required parameter: message")
            return {"message": arguments["message"]}
            
        elif tool_name == "add":
            if "a" not in arguments or "b" not in arguments:
                raise JSONRPCError(-32602, "Missing required parameters: a, b")
            
            try:
                a = float(arguments["a"])
                b = float(arguments["b"])
                return {"result": a + b}
            except (ValueError, TypeError):
                raise JSONRPCError(-32602, "Invalid parameters: a and b must be numbers")
                
        elif tool_name == "sleep":
            if "seconds" not in arguments:
                raise JSONRPCError(-32602, "Missing required parameter: seconds")
            
            try:
                seconds = float(arguments["seconds"])
                if seconds > 10:  # Limit sleep time for safety
                    seconds = 10
                time.sleep(seconds)
                return {"slept": seconds}
            except (ValueError, TypeError):
                raise JSONRPCError(-32602, "Invalid parameter: seconds must be a number")
                
        else:
            raise JSONRPCError(-32601, f"Tool not implemented: {tool_name}")


# Global server variable
http_server = None

def stop_server():
    """Stop the server."""
    global http_server
    if http_server:
        http_server.shutdown()

def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info("Received signal %s, shutting down", sig)
    stop_server()

def run_server(host: str, port: int, debug: bool = False):
    """
    Run the HTTP server.
    
    Args:
        host: The host to bind to
        port: The port to bind to
        debug: Whether to enable debug logging
    """
    global http_server
    
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start the server
    server_address = (host, port)
    http_server = ThreadingHTTPServer(server_address, MCPHTTPRequestHandler)
    logger.info(f"Starting server on {host}:{port}")
    
    try:
        # Run the server
        http_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    finally:
        # Clean up
        http_server.server_close()
        logger.info("Server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Minimal HTTP MCP Server"
    )
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Run the server
    run_server(args.host, args.port, args.debug)


if __name__ == "__main__":
    main()

# Function to broadcast a message to all SSE connections
def broadcast_sse_message(message: Dict[str, Any], event_type: str = "message"):
    """
    Broadcast a message to all SSE connections.
    
    Args:
        message: The message to broadcast
        event_type: The SSE event type
    """
    for connection in server_state["sse_connections"]:
        try:
            connection["queue"].put({
                "event": event_type,
                "data": message
            })
        except Exception as e:
            logger.error(f"Failed to queue message for connection {connection['id']}: {str(e)}")

# Function to send a message to a specific session's SSE connections
def send_sse_message_to_session(session_id: str, message: Dict[str, Any], event_type: str = "message"):
    """
    Send a message to all SSE connections for a specific session.
    
    Args:
        session_id: The target session ID
        message: The message to send
        event_type: The SSE event type
    """
    sent = False
    
    for connection in server_state["sse_connections"]:
        if connection.get("session_id") == session_id:
            try:
                connection["queue"].put({
                    "event": event_type,
                    "data": message
                })
                sent = True
            except Exception as e:
                logger.error(f"Failed to queue message for connection {connection['id']}: {str(e)}")
    
    return sent 