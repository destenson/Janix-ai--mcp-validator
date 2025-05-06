#!/usr/bin/env python3
"""
Minimal FastMCP HTTP Server with SSE transport

This script creates a standard FastMCP server with SSE transport
that can be used for compliance testing.
"""

import argparse
import asyncio
import logging
import uvicorn
from typing import List

from mcp.server.fastmcp import FastMCP

async def main():
    """Run the MCP HTTP server."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run a FastMCP HTTP server with SSE transport")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8085, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("mcp").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    # Create FastMCP instance with SSE capabilities
    fastmcp = FastMCP(
        name="MCP HTTP Reference Server",
        description="Reference implementation of an MCP server using HTTP with SSE transport",
        protocol_versions=["2024-11-05", "2025-03-26"],
        message_path="/mcp",
        sse_path="/notifications",
        host=args.host,
        port=args.port,
        debug=args.debug,
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
    
    print(f"Starting FastMCP HTTP server at http://{args.host}:{args.port}")
    print(f"Supported protocol versions: 2024-11-05, 2025-03-26")
    print("Press Ctrl+C to stop the server")
    print()
    print("IMPORTANT NOTES:")
    print("1. FastMCP requires a session_id for all requests")
    print("2. To establish a session, connect to the /notifications endpoint first")
    print("3. Then include the same session_id in all subsequent requests")
    print()
    
    # Configure and start Uvicorn
    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        log_level="debug" if args.debug else "info",
    )
    
    # Start the server
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main()) 