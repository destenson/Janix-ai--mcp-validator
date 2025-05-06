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
import logging.handlers
import os
import signal
import sys
import threading
import time
import uuid
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional, Union, Tuple
import queue
import socket
import urllib.parse

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
    "sse_connections": [],  # Track SSE connections
    "notifications": {}  # Track notifications for each session
}

# Add these constants at the top of the file after the imports
RATE_LIMIT_WINDOW = 1.0  # Minimum time between polls in seconds
MAX_CONNECTIONS_PER_SESSION = 5  # Maximum number of SSE connections per session
CONNECTION_TIMEOUT = 60  # Connection timeout in seconds

# Function to broadcast a message to all SSE connections
def broadcast_sse_message(message: Dict[str, Any], event_type: str = "message"):
    """
    Broadcast a message to all SSE connections.
    
    Args:
        message: The message to broadcast
        event_type: The SSE event type
    """
    # Convert message to JSON
    message_json = json.dumps(message)
    
    # Format as SSE event
    sse_data = f"event: {event_type}\ndata: {message_json}\n\n"
    sse_bytes = sse_data.encode('utf-8')
    
    # Send to all active connections
    for conn in server_state["sse_connections"][:]:  # Create copy to avoid modification during iteration
        try:
            conn["wfile"].write(sse_bytes)
            conn["wfile"].flush()
            conn["last_active"] = time.time()
        except (BrokenPipeError, ConnectionResetError):
            # Connection is dead, clean it up
            try:
                conn["connection"].close()
            except:
                pass
            if conn in server_state["sse_connections"]:
                server_state["sse_connections"].remove(conn)
                logger.info(f"Removed dead connection: {conn['id']} for session: {conn['session_id']}")

def send_sse_message_to_session(session_id: str, message: Dict[str, Any], event_type: str = "message"):
    """
    Send a message to all SSE connections for a specific session.
    
    Args:
        session_id: The target session ID
        message: The message to send
        event_type: The SSE event type
    """
    # Convert message to JSON
    message_json = json.dumps(message)
    
    # Format as SSE event
    sse_data = f"event: {event_type}\ndata: {message_json}\n\n"
    sse_bytes = sse_data.encode('utf-8')
    
    # Send to all connections for this session
    for conn in server_state["sse_connections"][:]:  # Create copy to avoid modification during iteration
        if conn["session_id"] == session_id:
            try:
                conn["wfile"].write(sse_bytes)
                conn["wfile"].flush()
                conn["last_active"] = time.time()
            except (BrokenPipeError, ConnectionResetError):
                # Connection is dead, clean it up
                try:
                    conn["connection"].close()
                except:
                    pass
                if conn in server_state["sse_connections"]:
                    server_state["sse_connections"].remove(conn)
                    logger.info(f"Removed dead connection: {conn['id']} for session: {session_id}")

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
    server_version = 'MinimalHTTPMCPServer/1.0'
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('MCPHTTPServer')
        super().__init__(*args, **kwargs)
    
    def version_string(self):
        """Return server version string."""
        return self.server_version
    
    def send_response(self, code, message=None):
        """Send the response header and log the response code."""
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header('Server', self.version_string())
        self.send_header('Date', self.date_time_string())
    
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
        self.send_header('Allow', 'OPTIONS, POST, GET')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        self.send_header('Access-Control-Max-Age', '86400')  # Cache preflight for 24 hours
        self.send_header('Content-Length', '0')  # Important to avoid keep-alive issues
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
            # Remove session
            del server_state["sessions"][session_id]
            if session_id in server_state["notifications"]:
                del server_state["notifications"][session_id]
            
            # Send success response
            self._send_response(200, {"success": True})
        else:
            self._send_error(401, "Unauthorized: Valid session ID required")
    
    def do_GET(self):
        """Handle GET requests for SSE streaming."""
        # Only handle GET requests to /mcp path
        if self.path != "/mcp":
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
        
        # Check if client accepts SSE
        accept_header = self.headers.get('Accept', '')
        if 'text/event-stream' not in accept_header:
            self._send_error(406, "Not Acceptable: Client must accept text/event-stream")
            return
            
        # Get session ID and verify session
        session_id = self.headers.get('Mcp-Session-Id')
        if not session_id or session_id not in server_state["sessions"]:
            self._send_error(401, "Unauthorized: Valid session ID required")
            return
            
        # Initialize notifications queue for this session if it doesn't exist
        if session_id not in server_state["notifications"]:
            server_state["notifications"][session_id] = []
            
        # Start SSE stream
        try:
            self._send_sse_response(session_id)
        except (ConnectionError, BrokenPipeError):
            # Clean up if client disconnects
            if session_id in server_state["notifications"]:
                del server_state["notifications"][session_id]
                
    def do_POST(self):
        """Handle POST requests."""
        self.logger.debug(f"Received POST request to {self.path}")
        self.logger.debug(f"Headers: {self.headers}")
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.logger.error("No content received")
            self._send_error(400, "No content received")
            return
            
        # Read request body
        try:
            body = self.rfile.read(content_length).decode('utf-8')
            self.logger.debug(f"Request body: {body}")
            request = json.loads(body)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {str(e)}")
            self._send_error(400, f"Invalid JSON: {str(e)}")
            return
        except Exception as e:
            self.logger.error(f"Error reading request: {str(e)}")
            self._send_error(500, f"Error reading request: {str(e)}")
            return
            
        # Process request
        try:
            response = self._handle_request(request)
            self.logger.debug(f"Response: {response}")
            
            # Send response
            self._send_response(response)
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            self._send_error(500, f"Internal server error: {str(e)}")
            return
    
    def _send_response(self, status_code: int, response_data: Dict[str, Any], session_id: Optional[str] = None) -> None:
        """
        Send an HTTP response with proper headers and status line.
        
        Args:
            status_code: HTTP status code
            response_data: Response data to send as JSON
            session_id: Optional session ID to include in response headers
        """
        # Convert response data to JSON
        response_json = json.dumps(response_data)
        response_bytes = response_json.encode('utf-8')
        
        # Send HTTP status line and headers
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        
        # Add session ID header if provided
        if session_id:
            self.send_header('Mcp-Session-Id', session_id)
        
        # End headers section
        self.end_headers()
        
        # Send response body
        self.wfile.write(response_bytes)
        self.wfile.flush()
    
    def _send_sse_response(self, session_id: str) -> None:
        """Send Server-Sent Events response."""
        # Verify session is valid
        if not self._verify_session():
            return
        
        # Check connection limits
        current_connections = count_session_connections(session_id)
        if current_connections >= MAX_CONNECTIONS_PER_SESSION:
            self._send_error(429, f"Too many connections for session (max {MAX_CONNECTIONS_PER_SESSION})")
            return
        
        # Set up SSE response headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()
        
        # Create connection record
        conn_id = str(uuid.uuid4())
        connection_info = {
            "id": conn_id,
            "session_id": session_id,
            "created": time.time(),
            "last_active": time.time(),
            "connection": self.connection,
            "wfile": self.wfile
        }
        
        try:
            # Add to active connections
            server_state["sse_connections"].append(connection_info)
            
            # Send initial keepalive
            self.wfile.write(b": keepalive\n\n")
            self.wfile.flush()
            
            # Keep connection alive
            while not server_state["shutdown_requested"]:
                # Check if connection is still valid
                if time.time() - connection_info["last_active"] > CONNECTION_TIMEOUT:
                    logger.info(f"Connection {conn_id} timed out")
                    break
                
                # Send keepalive every 30 seconds
                time.sleep(30)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                connection_info["last_active"] = time.time()
                
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"Client disconnected: {conn_id}")
        finally:
            # Clean up connection
            if connection_info in server_state["sse_connections"]:
                server_state["sse_connections"].remove(connection_info)
            try:
                self.connection.close()
            except:
                pass
    
    def _send_error(self, status_code: int, message: str) -> None:
        """
        Send an error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
        """
        error_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,  # Server error
                "message": message
            },
            "id": None
        }
        
        # Convert error data to JSON
        error_json = json.dumps(error_data)
        error_bytes = error_json.encode('utf-8')
        
        # Send HTTP status line and headers
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(error_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        self.end_headers()
        
        # Send error body
        self.wfile.write(error_bytes)
        self.wfile.flush()
    
    def _get_session_id(self) -> Optional[str]:
        """Get session ID from headers or query parameters."""
        # Check headers first (case-insensitive)
        for header, value in self.headers.items():
            if header.lower() == 'mcp-session-id':
                return value
        
        # Check query parameters if no header found
        path = self.path.split('?')
        if len(path) > 1:
            params = urllib.parse.parse_qs(path[1])
            if 'session' in params:
                return params['session'][0]
        
        return None

    def _verify_session(self) -> bool:
        """Verify that the session is valid and active."""
        session_id = self._get_session_id()
        if not session_id:
            self._send_error(401, "No session ID provided")
            return False
        
        if session_id not in server_state["sessions"]:
            self._send_error(401, "Invalid session ID")
            return False
        
        # Update session last activity time
        server_state["sessions"][session_id]["last_active"] = time.time()
        return True

    def _create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        server_state["sessions"][session_id] = {
            "created": time.time(),
            "last_active": time.time(),
            "initialized": False,
            "protocol_version": None
        }
        return session_id
    
    def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle a JSON-RPC request and return a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object, or None for notifications
        """
        self.logger.debug(f"Processing request: {request}")
        
        # Validate request format
        if not isinstance(request, dict):
            self.logger.error("Request must be a JSON object")
            return self._create_error(-32600, "Request must be a JSON object")
            
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            self.logger.error("Invalid JSON-RPC version")
            return self._create_error(-32600, "Invalid JSON-RPC version")
            
        if "method" not in request:
            self.logger.error("Method not specified")
            return self._create_error(-32600, "Method not specified")
            
        # Handle initialization
        if request["method"] == "initialize":
            self.logger.info("Processing initialize request")
            return self._handle_initialize(request)
            
        # Get session ID
        session_id = self._get_session_id()
        if not session_id:
            self.logger.error("No session ID provided")
            return self._create_error(401, "No session ID provided")
            
        # Verify session is valid
        if not self._verify_session():
            self.logger.error("Invalid session")
            return self._create_error(401, "Invalid session")
            
        # Handle other methods
        method = request["method"]
        self.logger.debug(f"Handling method: {method}")
        
        try:
            if method == "server/info":
                return self._handle_server_info(request)
            elif method == "tools/list":
                return self._handle_tools_list(request)
            elif method == "tools/call":
                return self._handle_tool_call(request)
            elif method == "tools/call-async":
                return self._handle_tools_call_async(request)
            elif method == "tools/result":
                return self._handle_tools_result(request)
            elif method == "tools/cancel":
                return self._handle_tools_cancel(request)
            elif method == "resources/list":
                return self._handle_resources_list(request)
            elif method == "resources/get":
                return self._handle_resources_get(request)
            elif method == "notifications/send":
                return self._handle_send_notification(request)
            elif method == "notifications/poll":
                return self._handle_notifications_poll(request)
            else:
                self.logger.error(f"Unknown method: {method}")
                return self._create_error(-32601, f"Method not found: {method}")
        except Exception as e:
            self.logger.error(f"Error handling method {method}: {str(e)}")
            return self._create_error(-32603, f"Internal error: {str(e)}")
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the initialize method.
        
        Args:
            params: The method parameters
            
        Returns:
            Server info and capabilities
            
        Raises:
            JSONRPCError: If initialization fails
        """
        # Check if already initialized
        if server_state["initialized"]:
            raise JSONRPCError(-32002, "Server already initialized")
        
        # Validate required parameters
        if "protocolVersion" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: protocolVersion")
        if "clientInfo" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: clientInfo")
        if "capabilities" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: capabilities")
        
        # Validate protocol version
        protocol_version = params["protocolVersion"]
        if protocol_version not in SUPPORTED_VERSIONS:
            raise JSONRPCError(-32602, f"Unsupported protocol version: {protocol_version}")
        
        # Store protocol version
        server_state["protocol_version"] = protocol_version
        server_state["initialized"] = True
        
        # Create new session if none exists
        session_id = self._create_session()
        self.send_header('Mcp-Session-Id', session_id)
        
        # Store session info
        server_state["sessions"][session_id] = {
            "id": session_id,
            "created": time.time(),
            "last_poll_time": time.time(),
            "capabilities": params["capabilities"],
            "protocol_version": protocol_version
        }
        
        # Return server info and capabilities
        return {
            "serverInfo": {
                "name": "MinimalHTTPMCPServer",
                "version": "1.0.0",
                "protocolVersion": protocol_version
            },
            "capabilities": {
                "protocolVersion": protocol_version,
                "tools": {
                    "asyncSupported": True
                },
                "resources": True
            }
        }
    
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
    
    def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
        Handle the notifications/send method.
        
        Args:
            params: The method parameters
            
        Returns:
            Success status
            
        Raises:
            JSONRPCError: If sending the notification fails
        """
        # Validate params
        if "type" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: type")
        if "data" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: data")
            
        notification_type = params["type"]
        notification_data = params["data"]
        target_session = params.get("sessionId")
        
        # Create notification object
        notification = {
            "type": notification_type,
            "data": notification_data
        }
        
        try:
            # If target session specified, send only to that session
            if target_session:
                if target_session not in server_state["sessions"]:
                    raise JSONRPCError(-32602, f"Invalid session ID: {target_session}")
                send_sse_message_to_session(target_session, notification, "notification")
            else:
                # Broadcast to all sessions
                broadcast_sse_message(notification, "notification")
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise JSONRPCError(-32603, f"Failed to send notification: {str(e)}")
    
    def _handle_notifications_poll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the notifications/poll method.
        
        Args:
            params: The method parameters
            
        Returns:
            List of pending notifications
            
        Raises:
            JSONRPCError: If polling fails
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32002, "Invalid session")
            
        # Rate limit polling - check last poll time
        session = server_state["sessions"][session_id]
        current_time = time.time()
        if "last_poll_time" in session:
            time_since_last_poll = current_time - session["last_poll_time"]
            if time_since_last_poll < RATE_LIMIT_WINDOW:
                raise JSONRPCError(
                    -32000, 
                    f"Rate limit exceeded - wait at least {RATE_LIMIT_WINDOW} seconds between polls"
                )
        
        # Update last poll time
        session["last_poll_time"] = current_time
        
        # Clean up any stale connections before processing notifications
        cleanup_stale_connections()
        
        # Get and clear pending notifications for this session
        notifications = server_state["notifications"].get(session_id, [])
        server_state["notifications"][session_id] = []
        
        return {"notifications": notifications}
    
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
    http_server.protocol_version = 'HTTP/1.1'
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


def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    logger = logging.getLogger('MCPHTTPServer')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        '/tmp/mcp_http_server.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    return logger

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MCP HTTP Server')
    parser.add_argument('--port', type=int, default=9000, help='Port to listen on (default: 9000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    logger = setup_logging(args.debug)
    logger.info(f"Starting MCP HTTP Server on port {args.port}")
    
    server = MCPHTTPServer(('', args.port), MCPHTTPRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()

def cleanup_stale_connections():
    """Clean up stale SSE connections and sessions."""
    current_time = time.time()
    
    # Clean up stale SSE connections
    for conn in server_state["sse_connections"][:]:  # Create copy to avoid modification during iteration
        if current_time - conn["last_active"] > CONNECTION_TIMEOUT:
            logger.info(f"Removing stale connection: {conn['id']} for session: {conn['session_id']}")
            try:
                conn["connection"].close()
            except:
                pass
            if conn in server_state["sse_connections"]:
                server_state["sse_connections"].remove(conn)
    
    # Clean up stale sessions
    for session_id in list(server_state["sessions"].keys()):
        session = server_state["sessions"][session_id]
        if current_time - session["last_active"] > (CONNECTION_TIMEOUT * 2):  # Give sessions longer timeout
            logger.info(f"Removing stale session: {session_id}")
            # Clean up any remaining connections for this session
            for conn in server_state["sse_connections"][:]:
                if conn["session_id"] == session_id:
                    try:
                        conn["connection"].close()
                    except:
                        pass
                    if conn in server_state["sse_connections"]:
                        server_state["sse_connections"].remove(conn)
            # Remove session
            del server_state["sessions"][session_id]
            # Clean up notifications
            if session_id in server_state["notifications"]:
                del server_state["notifications"][session_id]

def count_session_connections(session_id: str) -> int:
    """Count active SSE connections for a session."""
    # Clean up stale connections first
    cleanup_stale_connections()
    # Count remaining active connections
    return sum(1 for conn in server_state["sse_connections"] if conn["session_id"] == session_id) 