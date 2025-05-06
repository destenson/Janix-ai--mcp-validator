#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP 2024-11-05 HTTP Server Implementation.

This server implements only the 2024-11-05 protocol version.
It is designed to be a clean, compliant implementation of that specific version.
"""

import os
import sys
import json
import uuid
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp-2024-11-05-http-server")

# Get environment variables
DEBUG = os.environ.get("MCP_DEBUG", "").lower() in ("1", "true", "yes")

# Enable debug logging if requested
if DEBUG:
    logger.setLevel(logging.DEBUG)

class MCPSession:
    """MCP session."""
    
    def __init__(self):
        """Initialize the session."""
        self.id = str(uuid.uuid4())
        self.client_info = {}
        self.capabilities = {}
        self.is_test_session = False
        self.created_at = time.time()
        self.last_used = time.time()
        
    def touch(self):
        """Update last used timestamp."""
        self.last_used = time.time()

class MCPSessionManager:
    """Manages MCP sessions."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.sessions = {}
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self.cleanup_thread.start()
        
    def create_session(self) -> MCPSession:
        """Create a new session."""
        session = MCPSession()
        self.sessions[session.id] = session
        logger.debug(f"Created session: {session.id}")
        return session
        
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return session
        
    def remove_session(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Removed session: {session_id}")
            
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        while True:
            time.sleep(60)  # Run every minute
            now = time.time()
            expired = []
            for session_id, session in self.sessions.items():
                if now - session.last_used > 3600:  # 1 hour timeout
                    expired.append(session_id)
            for session_id in expired:
                self.remove_session(session_id)
                logger.info(f"Expired session: {session_id}")

class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""
    
    session_manager = MCPSessionManager()  # Class-level session manager
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path != "/mcp":
            self.send_error(404)
            return
            
        # Get content length
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Missing request body")
            return
            
        # Read request body
        request_body = self.rfile.read(content_length).decode("utf-8")
        if DEBUG:
            logger.debug(f"Request body: {request_body}")
            
        try:
            request = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
            
        # Get session ID from header
        session_id = self.headers.get("X-MCP-Session")
        session = None
        if session_id:
            session = self.session_manager.get_session(session_id)
            if not session:
                self.send_error(401, "Invalid session ID")
                return
                
        # Process the request
        try:
            response = self.handle_request(request, session)
            if response is not None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                
                # Get session ID from response for initialize method
                if request.get("method") == "initialize":
                    result = response.get("result", {})
                    session_info = result.get("session", {})
                    if "id" in session_info:
                        self.send_header("X-MCP-Session", session_info["id"])
                elif session:
                    self.send_header("X-MCP-Session", session.id)
                    
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            self.send_error(500, str(e))
            
    def do_DELETE(self):
        """Handle DELETE requests (session cleanup)."""
        if self.path != "/mcp":
            self.send_error(404)
            return
            
        # Get session ID from header
        session_id = self.headers.get("X-MCP-Session")
        if not session_id:
            self.send_error(400, "Missing session ID")
            return
            
        # Remove session
        self.session_manager.remove_session(session_id)
        
        # Send success response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def handle_request(self, request: Dict[str, Any], session: Optional[MCPSession]) -> Dict[str, Any]:
        """Handle a JSON-RPC request."""
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})
        
        logger.info(f"Method call: {method}")
        
        try:
            # Handle initialize specially (creates session)
            if method == "initialize":
                if session:
                    raise Exception("Session already initialized")
                session = self.session_manager.create_session()
                response = self.handle_initialize(params, session)
                response["result"]["session"] = {"id": session.id}
                return response
                
            # All other methods require a session
            if not session:
                raise Exception("No session ID provided")
                
            # Handle other methods
            if method == "initialized":
                return None
            elif method == "shutdown":
                return {}
            elif method == "server/info":
                return self.handle_server_info()
            elif method == "mcp/tools":
                return self.handle_tools_list()
            elif method == "mcp/tools/call":
                return self.handle_tools_call(params)
            else:
                raise Exception(f"Method not found: {method}")
                
        except Exception as e:
            if request_id is not None:
                error_code = -32000
                if "Method not found" in str(e):
                    error_code = -32601
                elif "Missing required" in str(e):
                    error_code = -32602
                elif "No session ID provided" in str(e):
                    error_code = -32001
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": error_code,
                        "message": str(e)
                    }
                }
            else:
                logger.error(f"Error handling notification: {str(e)}")
                return None
    
    def handle_initialize(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle the initialize method."""
        if "protocolVersion" not in params:
            raise Exception("Missing required parameter: protocolVersion")
            
        client_version = params.get("protocolVersion")
        if client_version != "2024-11-05":
            raise Exception("This server only supports protocol version 2024-11-05")
            
        # Store client info
        client_info = params.get("clientInfo", {})
        session.client_info = client_info
        
        # Check if this is a test client
        client_name = client_info.get("name", "").lower()
        if "test" in client_name:
            session.is_test_session = True
            logger.debug(f"Session {session.id} marked as test session")
            logger.info(f"Test client detected: {client_name}")
            
        # Store capabilities
        session.capabilities = params.get("capabilities", {})
        
        # Build response
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "MCP 2024-11-05 HTTP Server",
                    "version": "1.0.0",
                    "supportedVersions": ["2024-11-05"]
                },
                "capabilities": {
                    "tools": True
                }
            }
        }
    
    def handle_server_info(self) -> Dict[str, Any]:
        """Handle the server/info method."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "name": "MCP 2024-11-05 HTTP Server",
                "version": "1.0.0",
                "supportedVersions": ["2024-11-05"]
            }
        }
    
    def handle_tools_list(self) -> Dict[str, Any]:
        """Handle the mcp/tools method."""
        tools = [
            {
                "name": "echo",
                "description": "Echo the input text",
                "inputSchema": {  # Using inputSchema for 2024-11-05
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to echo"
                        }
                    },
                    "required": ["text"]
                },
                "outputSchema": {  # Using outputSchema for 2024-11-05
                    "type": "object",
                    "properties": {
                        "echo": {
                            "type": "string"
                        }
                    }
                }
            },
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
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
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {
                        "sum": {
                            "type": "number"
                        }
                    }
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": tools
            }
        }
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the mcp/tools/call method."""
        if "name" not in params:
            raise Exception("Missing required parameter: name")
        if "arguments" not in params:  # Using arguments for 2024-11-05
            raise Exception("Missing required parameter: arguments")
            
        tool_name = params["name"]
        arguments = params["arguments"]  # Using arguments instead of parameters
        
        result = None
        if tool_name == "echo":
            if "text" not in arguments:
                raise Exception("Missing required argument: text")
            result = {"echo": arguments["text"]}
        elif tool_name == "add":
            if "a" not in arguments or "b" not in arguments:
                raise Exception("Missing required arguments: a, b")
            try:
                a = float(arguments["a"])
                b = float(arguments["b"])
                result = {"sum": a + b}
            except (TypeError, ValueError):
                raise Exception("Invalid number format")
        else:
            raise Exception(f"Unknown tool: {tool_name}")
            
        return {
            "jsonrpc": "2.0",
            "result": result
        }

def run_server(host: str = "localhost", port: int = 9000, auto_port: bool = False):
    """Run the HTTP server."""
    
    # Try to bind to the port
    while True:
        try:
            server = HTTPServer((host, port), MCPRequestHandler)
            break
        except OSError:
            if not auto_port:
                raise
            port += 1
            
    logger.info(f"MCP 2024-11-05 HTTP Server listening on {host}:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.server_close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MCP 2024-11-05 HTTP Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--auto-port", action="store_true", help="Automatically find an available port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        
    run_server(args.host, args.port, args.auto_port) 