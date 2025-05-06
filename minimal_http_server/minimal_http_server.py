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
import errno

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MinimalHTTPMCPServer')

# Server state
server_state = {
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
        try:
            super().__init__(*args, **kwargs)
        except ConnectionResetError:
            self.logger.debug("Client disconnected during request handling")
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
    
    def handle(self):
        """Handle multiple requests if necessary."""
        try:
            super().handle()
        except ConnectionResetError:
            self.logger.debug("Client disconnected during request handling")
        except Exception as e:
            self.logger.error(f"Error in request handling: {str(e)}")
    
    def handle_one_request(self):
        """Handle a single HTTP request."""
        try:
            super().handle_one_request()
        except ConnectionResetError:
            self.logger.debug("Client disconnected during request")
        except Exception as e:
            self.logger.error(f"Error in request: {str(e)}")
            try:
                self.send_error(500, f"Internal Server Error: {str(e)}")
            except:
                pass  # If we can't send the error, just log it
    
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
            
            # Determine session_id for header, if applicable
            session_id_for_header = None
            if request.get("method") == "initialize" and "session" in response and "id" in response["session"]:
                session_id_for_header = response["session"]["id"]
            
            # Check if the response from _handle_request is an error structure
            if "error" in response and response.get("jsonrpc") == "2.0":
                # This indicates _handle_request decided it's an error but didn't raise
                # This path needs to be robust. For now, let's assume JSONRPCError is raised.
                # If not, we might need to determine the HTTP status code differently.
                # For simplicity, let's assume _send_error path is taken for actual errors.
                # If we reach here with an error structure, it's a bit ambiguous.
                # The current structure is that _handle_request returns a dict,
                # and _send_response is called.
                # Let's ensure _send_response gets the correct status code.
                # JSON-RPC errors should ideally map to appropriate HTTP status codes.
                # However, the spec often uses 200 OK with an error in the body.
                # Let's stick to 200 OK if _handle_request returns.
                self._send_response(200, response, session_id=session_id_for_header)
            else:
                # Successful response
                self._send_response(200, response, session_id=session_id_for_header)
            
        except JSONRPCError as e: # Catch errors from _handle_request
            # Map JSON-RPC errors to HTTP status codes if desired, or use a default like 400/500
            # For now, _send_error uses a status code passed to it or a default.
            # Here, we need to decide what HTTP status code to use for JSONRPCError.
            # The existing _send_error takes a status code. Let's map some common ones.
            http_status_code = 500 # Default server error
            if e.code == -32700: # Parse error
                http_status_code = 400
            elif e.code == -32600: # Invalid Request
                http_status_code = 400
            elif e.code == -32601: # Method not found
                http_status_code = 404
            elif e.code == -32602: # Invalid params
                http_status_code = 400
            elif e.code == -32001: # Session errors (custom)
                 http_status_code = 401 # Unauthorized or bad session
            elif e.code == -32002: # Already initialized (custom)
                 http_status_code = 409 # Conflict

            # Create the JSON-RPC error response body
            # error_response_body = self._create_error(e.code, e.message, e.data) # No longer needed here
            # self._send_error(http_status_code, error_response_body["error"]["message"]) # _send_error will wrap this
            self._send_error(http_status_code, e.message, rpc_error_code=e.code, rpc_error_data=e.data)
            return

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
    
    def _send_error(self, status_code: int, message: str, rpc_error_code: Optional[int] = None, rpc_error_data: Optional[Any] = None) -> None:
        """
        Send an error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
            rpc_error_code: Optional JSON-RPC error code
            rpc_error_data: Optional JSON-RPC error data
        """
        error_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": rpc_error_code if rpc_error_code is not None else -32000,  # Server error
                "message": message
            },
            "id": None
        }
        if rpc_error_data is not None:
            error_data["error"]["data"] = rpc_error_data
        
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
    
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a JSON-RPC request and return a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object
        """
        self.logger.debug(f"Processing request: {request}")
        
        try:
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
                return self._create_error(-32001, "No session ID provided")
            
            # Verify session is valid
            if not self._verify_session():
                self.logger.error("Invalid session")
                return self._create_error(-32001, "Invalid session")
            
            # Handle other methods
            method = request["method"]
            self.logger.debug(f"Handling method: {method}")
            
            try:
                # Extract params from request to pass to handler methods
                params = request.get("params", {})
                
                if method == "server/info":
                    result = self._handle_server_info(params)
                elif method == "tools/list":
                    result = self._handle_tools_list(params)
                elif method == "tools/call":
                    result = self._handle_tool_call(params)
                elif method == "tools/call-async":
                    result = self._handle_tools_call_async(params)
                elif method == "tools/result":
                    result = self._handle_tools_result(params)
                elif method == "tools/cancel":
                    result = self._handle_tools_cancel(params)
                elif method == "resources/list":
                    result = self._handle_resources_list(params)
                elif method == "resources/get":
                    result = self._handle_resources_get(params)
                elif method == "notifications/send":
                    result = self._handle_send_notification(params)
                elif method == "notifications/poll":
                    result = self._handle_notifications_poll(params)
                else:
                    self.logger.error(f"Unknown method: {method}")
                    return self._create_error(-32601, f"Method not found: {method}")
                    
                # Format successful response
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result
                }
                
            except JSONRPCError as e:
                return self._create_error(e.code, e.message, e.data)
            except Exception as e:
                self.logger.error(f"Error handling method {method}: {str(e)}")
                return self._create_error(-32603, f"Internal error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return self._create_error(-32603, f"Internal error: {str(e)}")

    def _create_error(self, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create a JSON-RPC error response."""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": None
        }

    def _handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the initialize method.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            Server info and capabilities
            
        Raises:
            JSONRPCError: If initialization fails
        """
        self.logger.info("Processing initialize request")
        
        # Get params from request
        params = request.get("params", {})
        self.logger.debug(f"Initialize params: {params}")
        
        # Validate required parameters
        if not isinstance(params, dict):
            self.logger.error("Invalid params: not a dictionary")
            raise JSONRPCError(-32602, "Invalid params: must be a dictionary")
            
        if "protocolVersion" not in params:
            self.logger.error("Missing required parameter: protocolVersion")
            raise JSONRPCError(-32602, "Missing required parameter: protocolVersion")
            
        if "clientInfo" not in params:
            self.logger.error("Missing required parameter: clientInfo")
            raise JSONRPCError(-32602, "Missing required parameter: clientInfo")
            
        if "capabilities" not in params:
            self.logger.error("Missing required parameter: capabilities")
            raise JSONRPCError(-32602, "Missing required parameter: capabilities")
        
        # Validate protocol version
        protocol_version = params["protocolVersion"]
        if protocol_version not in SUPPORTED_VERSIONS:
            self.logger.error(f"Unsupported protocol version: {protocol_version}")
            raise JSONRPCError(-32602, f"Unsupported protocol version: {protocol_version}")
        
        # Create new session if one isn't already part of the context (e.g. from headers)
        # For initialize, we always create a new one as per typical MCP flow.
        session_id = self._create_session()
        self.logger.info(f"Created new session for initialize: {session_id}")
        
        # Store session info, including protocol version and initialized status
        server_state["sessions"][session_id]["protocol_version"] = protocol_version
        server_state["sessions"][session_id]["initialized"] = True
        server_state["sessions"][session_id]["capabilities"] = params["capabilities"]
        # 'created' and 'last_active' are already set by _create_session
        
        # Create response
        response = {
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
            },
            "session": {
                "id": session_id
            }
        }
        
        self.logger.debug(f"Initialize response: {response}")
        
        # Add session ID to response headers
        # self.send_header('Mcp-Session-Id', session_id) # Removed: _send_response will handle this
        
        return response
    
    def _handle_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the server/info method.
        
        Args:
            params: The method parameters
            
        Returns:
            Server information
        
        Raises:
            JSONRPCError: If session is invalid or not initialized
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")
            
        return {
            "name": "Minimal MCP HTTP Server",
            "version": "1.0.0",
            "supportedVersions": SUPPORTED_VERSIONS
        }
    
    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/list method.
        Args:
            params: The method parameters (expected to be empty for tools/list)
        Returns:
            List of available tools
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            # This case should ideally be caught by _verify_session in _handle_request
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if not protocol_version:
            # Should not happen if session is initialized
            raise JSONRPCError(-32004, "Protocol version not set for session")

        # Adapt tool format for 2024-11-05 if needed
        tools_list = []
        for tool in TOOLS:
            tool_copy = tool.copy()
            
            # For 2024-11-05, convert 'parameters' to 'inputSchema'
            if protocol_version == "2024-11-05":
                if "parameters" in tool_copy:
                    tool_copy["inputSchema"] = tool_copy.pop("parameters")
            
            tools_list.append(tool_copy)
        
        return {"tools": tools_list}
    
    def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/call method.
        Args:
            params: The method parameters, e.g., {"name": "tool_name", "parameters": {...}}
        Returns:
            The tool call result
        Raises:
            JSONRPCError: If the tool call fails
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if not protocol_version:
            raise JSONRPCError(-32004, "Protocol version not set for session")

        self.logger.debug(f"_handle_tool_call: Received params: {params}, type: {type(params)}")
        
        # Add more detailed debugging
        self.logger.info(f"Tool call params details: {json.dumps(params, indent=2)}")
        self.logger.info(f"Protocol version from session: {protocol_version}")
        
        # Validate params for the tool call itself (e.g., presence of "name")
        if "name" not in params:
            self.logger.error(f"_handle_tool_call: 'name' not in params. Keys: {list(params.keys()) if isinstance(params, dict) else 'Not a dict'}. Params content: {params}")
            raise JSONRPCError(-32602, "Missing required parameter: name for tool call")
        
        tool_name = params["name"]
        
        # Get the tool arguments based on protocol version stored in the session
        if protocol_version == "2025-03-26":
            arguments = params.get("parameters", {})
            self.logger.info(f"Using 'parameters' key for 2025-03-26: {arguments}")
        else: # 2024-11-05
            arguments = params.get("arguments", {})
            self.logger.info(f"Using 'arguments' key for 2024-11-05: {arguments}")
        
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
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if protocol_version != "2025-03-26": # call-async is 2025-03-26 specific
            raise JSONRPCError(-32601, f"Method tools/call-async not supported in protocol version {protocol_version}")

        # Validate params for the call-async itself
        if "name" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: name for tools/call-async")
        
        tool_name = params["name"]
        # For 2025-03-26, tool arguments are under "parameters"
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
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")
        
        protocol_version = session.get("protocol_version")
        if protocol_version != "2025-03-26":
            raise JSONRPCError(-32601, f"Method tools/result not supported in protocol version {protocol_version}")

        # Validate params for tools/result
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id for tools/result")
        
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
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if protocol_version != "2025-03-26":
            raise JSONRPCError(-32601, f"Method tools/cancel not supported in protocol version {protocol_version}")

        # Validate params for tools/cancel
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id for tools/cancel")
        
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
            params: The method parameters (expected to be empty)
        Returns:
            List of available resources
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if protocol_version != "2025-03-26":
            raise JSONRPCError(-32601, f"Method resources/list not supported in protocol version {protocol_version}")

        return {"resources": RESOURCES}
    
    def _handle_resources_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the resources/get method (2025-03-26 only).
        Args:
            params: The method parameters, e.g., {"id": "resource_id"}
        Returns:
            The requested resource
        Raises:
            JSONRPCError: If the resource is not found
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID")

        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized")

        protocol_version = session.get("protocol_version")
        if protocol_version != "2025-03-26":
            raise JSONRPCError(-32601, f"Method resources/get not supported in protocol version {protocol_version}")

        # Validate params for resources/get
        if "id" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: id for resources/get")
        
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
            params: The method parameters, e.g., {"type": "...", "data": {...}, "sessionId": "optional_target"}
        Returns:
            Success status
        Raises:
            JSONRPCError: If sending the notification fails
        """
        current_session_id = self._get_session_id()
        if not current_session_id or current_session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID for sending notification")

        current_session = server_state["sessions"][current_session_id]
        if not current_session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized for sending notification")

        # Validate params for the notification itself
        if "type" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: type for notification")
        if "data" not in params:
            raise JSONRPCError(-32602, "Missing required parameter: data for notification")
            
        notification_type = params["type"]
        notification_data = params["data"]
        target_session_id_param = params.get("sessionId") # Optional specific target for the notification
        
        # Create notification object
        notification = {
            "type": notification_type,
            "data": notification_data
        }
        
        try:
            # If target session specified, send only to that session
            if target_session_id_param:
                if target_session_id_param not in server_state["sessions"]:
                    raise JSONRPCError(-32602, f"Invalid target session ID for notification: {target_session_id_param}")
                # Also check if the target session is initialized (optional, depends on requirements)
                # target_session_for_notification = server_state["sessions"][target_session_id_param]
                # if not target_session_for_notification.get("initialized"):
                #     raise JSONRPCError(-32003, f"Target session {target_session_id_param} not initialized")
                send_sse_message_to_session(target_session_id_param, notification, "notification")
            else:
                # Broadcast to all SSE connections of the *current* session if no target is specified
                # Or, if this is meant to be a global broadcast (e.g. admin initiated), 
                # then broadcast_sse_message() would be used. Current design implies session context.
                # For now, let's assume if no target_session_id_param, it's for the current session's SSE streams.
                send_sse_message_to_session(current_session_id, notification, "notification")
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise JSONRPCError(-32603, f"Failed to send notification: {str(e)}")
    
    def _handle_notifications_poll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the notifications/poll method.
        Args:
            params: The method parameters (expected to be empty)
        Returns:
            List of pending notifications
        Raises:
            JSONRPCError: If polling fails
        """
        session_id = self._get_session_id()
        if not session_id or session_id not in server_state["sessions"]:
            raise JSONRPCError(-32001, "Invalid or missing session ID for polling")
            
        session = server_state["sessions"][session_id]
        if not session.get("initialized"):
            raise JSONRPCError(-32003, "Session not initialized for polling")

        # Rate limit polling - check last poll time
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

def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    logger = logging.getLogger('MCPHTTPServer')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
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

def run_server(host: str, port: int, debug: bool = False) -> None:
    """Run the HTTP server."""
    logger = setup_logging(debug)
    logger.info(f"Starting MCP HTTP Server on {host}:{port}")
    
    try:
        # Create server with proper error handling
        server = ThreadingHTTPServer((host, port), MCPHTTPRequestHandler)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down")
            server.shutdown()
            server.server_close()
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start server
        logger.info("Server started and ready to accept connections")
        server.serve_forever()
        
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            logger.error(f"Port {port} is already in use")
        else:
            logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error starting server: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MCP HTTP Server')
    parser.add_argument('--host', type=str, default='localhost', help='Host to listen on (default: localhost)')
    parser.add_argument('--port', type=int, default=9000, help='Port to listen on (default: 9000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    run_server(args.host, args.port, args.debug)


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