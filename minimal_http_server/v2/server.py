#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Main HTTP Server Implementation for MCP

This module provides the main HTTP server implementation for the MCP protocol.
"""

import argparse
import json
import logging
import logging.handlers
import os
import signal
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List, Tuple, Type, Union
import urllib.parse
import errno

# Use relative imports
from .base_transport import BaseTransport, HTTPJSONRPCTransport, HTTPSSETransport
from .session_manager import SessionManager, Session
from .protocol_handler import (
    ProtocolHandler, ProtocolHandlerFactory, MCPError,
    Protocol_2024_11_05, Protocol_2025_03_26
)

# Configure logging
logger = logging.getLogger('MCPHTTPServer')

# Constants
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 9000
SUPPORTED_VERSIONS = ["2024-11-05", "2025-03-26"]


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for the MCP protocol.
    
    This class handles incoming HTTP requests and routes them to the appropriate
    protocol handler based on the client's session and protocol version.
    """
    
    # Override default HTTP protocol version
    protocol_version = 'HTTP/1.1'
    server_version = 'MCPHTTPServer/2.0'
    
    def __init__(self, *args, **kwargs):
        """Initialize the request handler."""
        # Get references to server components
        self.server_state = {}
        
        try:
            super().__init__(*args, **kwargs)
        except ConnectionResetError:
            logger.debug("Client disconnected during request handling")
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
    
    @property
    def session_manager(self) -> SessionManager:
        """Get the session manager from the server."""
        return self.server.session_manager
    
    @property
    def json_rpc_transport(self) -> HTTPJSONRPCTransport:
        """Get the JSON-RPC transport from the server."""
        return self.server.json_rpc_transport
    
    @property
    def sse_transport(self) -> HTTPSSETransport:
        """Get the SSE transport from the server."""
        return self.server.sse_transport
    
    def handle(self):
        """Handle multiple requests if necessary."""
        try:
            super().handle()
        except ConnectionResetError:
            logger.debug("Client disconnected during request handling")
        except Exception as e:
            logger.error(f"Error in request handling: {str(e)}")
    
    def handle_one_request(self):
        """Handle a single HTTP request."""
        try:
            super().handle_one_request()
        except ConnectionResetError:
            logger.debug("Client disconnected during request")
        except Exception as e:
            logger.error(f"Error in request: {str(e)}")
            try:
                self.send_error(500, f"Internal Server Error: {str(e)}")
            except:
                pass  # If we can't send the error, just log it
    
    def version_string(self):
        """Return server version string."""
        return self.server_version
    
    def log_message(self, format, *args):
        """Override log_message to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        # Only handle OPTIONS requests to /mcp path
        if not self._is_mcp_endpoint():
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
            
        self.send_response(200)
        self.send_header('Allow', 'OPTIONS, POST, GET, DELETE')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        self.send_header('Access-Control-Max-Age', '86400')  # Cache preflight for 24 hours
        self.send_header('Content-Length', '0')  # Important to avoid keep-alive issues
        self.end_headers()
    
    def do_DELETE(self):
        """Handle DELETE requests for ending sessions."""
        if not self._is_mcp_endpoint():
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
            
        # Check if this is a session termination request
        session_id = self._get_session_id()
        if session_id and self.session_manager.get_session(session_id):
            # Remove session
            self.session_manager.remove_session(session_id)
            
            # Clean up any transport connections
            self.json_rpc_transport.close(session_id)
            self.sse_transport.close(session_id)
            
            # Send success response
            self._send_response(200, {"success": True})
        else:
            self._send_error(401, "Unauthorized: Valid session ID required")
    
    def do_GET(self):
        """Handle GET requests for SSE streaming."""
        if not self._is_mcp_endpoint():
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
        
        # Check if client accepts SSE
        accept_header = self.headers.get('Accept', '')
        if 'text/event-stream' not in accept_header:
            self._send_error(406, "Not Acceptable: Client must accept text/event-stream")
            return
            
        # Get session ID and verify session
        session_id = self._get_session_id()
        if not session_id:
            self._send_error(401, "Unauthorized: Session ID required")
            return
            
        session = self.session_manager.get_session(session_id)
        if not session:
            self._send_error(401, "Unauthorized: Invalid session ID")
            return
            
        if not session.initialized:
            self._send_error(403, "Forbidden: Session not initialized")
            return
            
        # Start SSE stream
        self._handle_sse_stream(session)
    
    def do_POST(self):
        """Handle POST requests for JSON-RPC."""
        if not self._is_mcp_endpoint():
            self._send_error(404, "Not Found - MCP endpoint is at /mcp")
            return
            
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_error(400, "No content received")
            return
            
        # Read request body
        try:
            body = self.rfile.read(content_length).decode('utf-8')
            logger.debug(f"Request body: {body}")
            request = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            self._send_error(400, f"Invalid JSON: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Error reading request: {str(e)}")
            self._send_error(500, f"Error reading request: {str(e)}")
            return
            
        # Process JSON-RPC request
        self._handle_jsonrpc_request(request)
    
    def _is_mcp_endpoint(self) -> bool:
        """Check if the request is for the MCP endpoint."""
        return self.path == "/mcp" or self.path.startswith("/mcp?")
    
    def _get_session_id(self) -> Optional[str]:
        """
        Get the session ID from headers or query parameters.
        
        Returns:
            Optional[str]: The session ID, or None if not found.
        """
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
    
    def _handle_jsonrpc_request(self, request: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """
        Handle a JSON-RPC request.
        
        Args:
            request: The JSON-RPC request object or batch request array.
        """
        # Check if this is a batch request
        if isinstance(request, list):
            if not request:
                # Empty batch request
                self._send_error(400, "Empty batch request")
                return
                
            responses = []
            headers = {}
            for item in request:
                response, item_headers = self._process_jsonrpc_item(item)
                if response:  # Only include responses for requests with an ID
                    responses.append(response)
                # Merge headers
                headers.update(item_headers or {})
                    
            # Send batch response
            if responses:
                self._send_response(200, responses, headers)
            else:
                # All notifications in batch, no response needed
                self._send_response(200, [], headers)
        else:
            # Single request
            response, headers = self._process_jsonrpc_item(request)
            if response:  # Only send response for requests with an ID
                self._send_response(200, response, headers)
            else:
                # Notification, no response needed
                self._send_response(204, None, headers)
    
    def _process_jsonrpc_item(self, request: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
        """
        Process a single JSON-RPC request or notification.
        
        Args:
            request: The JSON-RPC request object.
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Dict[str, str]]: 
                The JSON-RPC response (or None for notifications), and any headers to send.
        """
        # Validate JSON-RPC format
        if not isinstance(request, dict):
            return self._create_jsonrpc_error(-32600, "Invalid Request", "Request must be a JSON object"), {}
            
        if request.get("jsonrpc") != "2.0":
            return self._create_jsonrpc_error(-32600, "Invalid Request", "Invalid JSON-RPC version"), {}
            
        if "method" not in request:
            return self._create_jsonrpc_error(-32600, "Invalid Request", "Method not specified"), {}
        
        # Check if this is a notification (no ID)
        request_id = request.get("id")
        is_notification = "id" not in request
        
        # Get method and params
        method = request["method"]
        params = request.get("params", {})
        
        # Initialize session for this request
        session = None
        
        # Handle initialization request specially
        if method == "initialize":
            try:
                # Create a new session
                session = self.session_manager.create_session()
                
                # Get protocol version from request
                protocol_version = params.get("protocolVersion")
                if protocol_version not in SUPPORTED_VERSIONS:
                    raise MCPError(-32602, f"Unsupported protocol version: {protocol_version}")
                
                # Create a protocol handler for this session
                handler = ProtocolHandlerFactory.create_handler(session, protocol_version)
                
                # Initialize the handler
                result = handler.initialize(params)
                
                # Return the response with session ID in header
                response = {
                    "jsonrpc": "2.0",
                    "result": result
                }
                
                if not is_notification:
                    response["id"] = request_id
                    
                # Create headers for the response with the session ID
                headers = {"Mcp-Session-Id": session.id}
                
                # Return the response (don't set headers here)
                return response, headers
            except MCPError as e:
                return self._create_jsonrpc_error(e.code, e.message, e.data, request_id), {}
            except Exception as e:
                logger.error(f"Error initializing: {str(e)}")
                return self._create_jsonrpc_error(-32603, "Internal error", str(e), request_id), {}
        
        # For all other methods, get the session from the request
        session_id = self._get_session_id()
        if not session_id:
            return self._create_jsonrpc_error(-32001, "No session ID provided", None, request_id), {}
            
        session = self.session_manager.get_session(session_id)
        if not session:
            return self._create_jsonrpc_error(-32001, "Invalid session ID", None, request_id), {}
            
        # Create a protocol handler for this session
        try:
            handler = ProtocolHandlerFactory.create_handler(session)
            
            # Handle the request
            result = handler.handle_request(method, params)
            
            # Create the response
            if is_notification:
                return None, {}
                
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }, {}
        except MCPError as e:
            if is_notification:
                return None, {}
                
            return self._create_jsonrpc_error(e.code, e.message, e.data, request_id), {}
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            
            if is_notification:
                return None, {}
                
            return self._create_jsonrpc_error(-32603, "Internal error", str(e), request_id), {}
    
    def _handle_sse_stream(self, session: Session) -> None:
        """
        Handle a Server-Sent Events (SSE) stream for notifications.
        
        Args:
            session: The session for this stream.
        """
        try:
            # Set up SSE response headers
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()
            
            # Create connection record
            import uuid
            conn_id = str(uuid.uuid4())
            connection_info = {
                "id": conn_id,
                "session_id": session.id,
                "created": time.time(),
                "last_active": time.time(),
                "connection": self.connection,
                "wfile": self.wfile
            }
            
            # Register with transport
            self.sse_transport.register_connection(session.id, connection_info)
            
            # Send initial keepalive
            self.wfile.write(b": keepalive\n\n")
            self.wfile.flush()
            
            # Keep connection alive
            while True:
                # Check if session is still valid
                if not self.session_manager.get_session(session.id):
                    logger.info(f"Session {session.id} no longer valid, closing SSE connection")
                    break
                    
                # Send keepalive every 30 seconds
                time.sleep(30)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                connection_info["last_active"] = time.time()
        except (BrokenPipeError, ConnectionResetError):
            logger.info(f"Client disconnected: {conn_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream: {str(e)}")
        finally:
            # Clean up connection
            try:
                self.connection.close()
            except:
                pass
    
    def _create_jsonrpc_error(self, code: int, message: str, data: Any = None, 
                             request_id: Any = None) -> Dict[str, Any]:
        """
        Create a JSON-RPC error response.
        
        Args:
            code: The error code.
            message: The error message.
            data: Additional error data.
            request_id: The request ID.
            
        Returns:
            Dict[str, Any]: The JSON-RPC error response.
        """
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
            
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
    
    def _send_response(self, status_code: int, response_data: Any, headers: Dict[str, str] = None) -> None:
        """
        Send an HTTP response.
        
        Args:
            status_code: The HTTP status code.
            response_data: The response data to send.
            headers: Additional headers to send.
        """
        self.send_response(status_code)
        
        # Set Content-Type for JSON responses
        if response_data is not None:
            self.send_header('Content-Type', 'application/json')
            response_json = json.dumps(response_data)
            response_bytes = response_json.encode('utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
        else:
            # No content
            self.send_header('Content-Length', '0')
            
        # Set CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Mcp-Session-Id')
        
        # Set additional headers
        if headers:
            for name, value in headers.items():
                self.send_header(name, value)
                
        self.end_headers()
        
        # Send response body
        if response_data is not None:
            self.wfile.write(response_bytes)
            self.wfile.flush()
    
    def _send_error(self, status_code: int, message: str, headers: Dict[str, str] = None) -> None:
        """
        Send an HTTP error response.
        
        Args:
            status_code: The HTTP status code.
            message: The error message.
            headers: Additional headers to send.
        """
        # Create JSON-RPC error response
        error = self._create_jsonrpc_error(-32000, message)
        self._send_response(status_code, error, headers)


class MCPHTTPServer(ThreadingHTTPServer):
    """
    HTTP server for the MCP protocol.
    
    This class extends ThreadingHTTPServer to add MCP-specific functionality.
    """
    
    def __init__(self, server_address, RequestHandlerClass):
        """
        Initialize the HTTP server.
        
        Args:
            server_address: The server address (host, port).
            RequestHandlerClass: The request handler class.
        """
        # Initialize base class
        super().__init__(server_address, RequestHandlerClass)
        
        # Initialize components
        self.session_manager = SessionManager()
        self.json_rpc_transport = HTTPJSONRPCTransport()
        self.sse_transport = HTTPSSETransport()
        
        # Initialize all components
        self.session_manager.start()
        self.json_rpc_transport.initialize()
        self.sse_transport.initialize()
        
        # Track whether the server is running
        self.running = False
    
    def serve_forever(self, poll_interval=0.5):
        """
        Start the server and serve requests until shutdown.
        
        Args:
            poll_interval: The polling interval.
        """
        self.running = True
        try:
            super().serve_forever(poll_interval)
        finally:
            self.running = False
    
    def shutdown(self):
        """Shut down the server and all components."""
        super().shutdown()
        self.server_close()
        
        # Stop all components
        self.session_manager.stop()
        self.json_rpc_transport.close()
        self.sse_transport.close()
        
        # Let all listeners know we're shutting down
        logger.info("Server shutdown complete")


def setup_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        debug: Whether to enable debug logging.
        log_file: The log file to write to.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Error setting up log file {log_file}: {str(e)}")


def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """
    Find an available port, starting from start_port.
    
    Args:
        start_port: The port to start searching from.
        max_attempts: The maximum number of ports to try.
        
    Returns:
        int: An available port.
        
    Raises:
        OSError: If no available port could be found.
    """
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            if result != 0:  # Port is available
                return port
    
    raise OSError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, 
               debug: bool = False, auto_port: bool = False,
               log_file: Optional[str] = None) -> None:
    """
    Run the MCP HTTP server.
    
    Args:
        host: The host to bind to.
        port: The port to bind to.
        debug: Whether to enable debug logging.
        auto_port: Whether to automatically find an available port.
        log_file: The log file to write to.
    """
    # Set up logging
    setup_logging(debug, log_file)
    
    # Find an available port if requested
    if auto_port:
        try:
            port = find_available_port(port)
            logger.info(f"Found available port: {port}")
        except OSError as e:
            logger.error(f"Could not find available port: {str(e)}")
            sys.exit(1)
    
    try:
        # Create server
        server = MCPHTTPServer((host, port), MCPHTTPRequestHandler)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down")
            server.shutdown()
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start server
        server_addr = f"{host}:{port}"
        logger.info(f"Starting MCP HTTP Server on {server_addr}")
        server.serve_forever()
        
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            logger.error(f"Port {port} is already in use")
            if not auto_port:
                logger.info("Try using --auto-port to automatically find an available port")
        else:
            logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error starting server: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MCP HTTP Server')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                        help=f'Host to listen on (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--auto-port', action='store_true',
                        help='Automatically find an available port if the specified port is in use')
    parser.add_argument('--log-file', type=str,
                        help='Log file to write to (in addition to stdout)')
    
    args = parser.parse_args()
    
    run_server(args.host, args.port, args.debug, args.auto_port, args.log_file)


if __name__ == "__main__":
    main() 