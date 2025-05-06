#!/usr/bin/env python3
"""
Standalone HTTP Server with Session ID Middleware

This script runs an MCP HTTP server with SSE transport, using a middleware
that automatically adds session IDs to requests.
"""

import asyncio
import logging
import uuid
import uvicorn
from typing import Dict, Any, Callable

from starlette.types import ASGIApp, Receive, Scope, Send
from mcp.server.fastmcp import FastMCP

class SessionMiddleware:
    """Middleware that ensures all requests have a session ID."""
    
    def __init__(self, app: ASGIApp, debug: bool = False):
        """Initialize the middleware."""
        self.app = app
        self.debug = debug
        self.logger = logging.getLogger("SessionMiddleware")
        if debug:
            self.logger.setLevel(logging.DEBUG)
    
    async def __call__(self, scope: Dict[str, Any], receive: Receive, send: Send) -> None:
        """Process the request, adding a session ID if missing."""
        if scope["type"] != "http":
            # Pass through non-HTTP requests (like lifespan)
            await self.app(scope, receive, send)
            return
            
        # Extract headers from the scope
        headers = scope.get("headers", [])
        
        # Check if we already have a session ID
        has_session_id = False
        for k, v in headers:
            if k.decode('latin1').lower() == 'mcp-session-id':
                has_session_id = True
                if self.debug:
                    self.logger.debug(f"Request already has session ID: {v.decode('latin1')}")
                break
        
        # If no session ID, add one
        if not has_session_id:
            session_id = str(uuid.uuid4())
            if self.debug:
                self.logger.debug(f"Adding session ID to request: {session_id}")
            
            # Add session ID to headers
            new_headers = list(headers)
            new_headers.append((b'mcp-session-id', session_id.encode()))
            scope["headers"] = new_headers
        
        # Continue with the request
        await self.app(scope, receive, send)

async def main():
    """Run the MCP HTTP server."""
    # Configure logging
    debug = True
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("mcp").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    # Create FastMCP instance with SSE capabilities
    fastmcp = FastMCP(
        name="MCP HTTP Reference Server",
        description="Reference implementation of an MCP server using HTTP with SSE transport",
        protocol_versions=["2024-11-05", "2025-03-26"],
        # FastMCP's internal SSE transport uses these paths by default:
        # POST to / for JSON-RPC requests
        # GET from /notifications for SSE
        message_path="/",
        sse_path="/notifications",
        host="localhost",
        port=8085,
        debug=debug,
    )
    
    # Register built-in tools for testing
    @fastmcp.tool()
    def echo(message: str) -> str:
        """Echo a message back to the client."""
        return message
    
    @fastmcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers and return the result."""
        return a + b
    
    @fastmcp.tool()
    async def sleep(seconds: float) -> str:
        """Sleep for the specified number of seconds (async)."""
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"
    
    # Get the ASGI application from FastMCP
    app = fastmcp.sse_app()
    
    # Wrap the app with our session middleware
    app_with_session = SessionMiddleware(app, debug=debug)
    
    print(f"Starting MCP HTTP server at http://localhost:8085")
    print(f"Supported protocol versions: 2024-11-05, 2025-03-26")
    print("Press Ctrl+C to stop the server")
    
    # Configure and start Uvicorn
    config = uvicorn.Config(
        app=app_with_session,
        host="0.0.0.0",  # Listen on all interfaces
        port=8085,
        log_level="debug" if debug else "info",
    )
    
    # Start the server
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main()) 