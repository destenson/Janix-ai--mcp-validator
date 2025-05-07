#!/usr/bin/env python3
"""
Standard MCP HTTP Server Implementation

This server implements the standard HTTP transport pattern expected by the MCP HTTP tester.
It uses header-based session management and returns immediate responses.
"""

import argparse
import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logger = logging.getLogger("mcp_http_server")

# Create FastAPI app
app = FastAPI(title="MCP HTTP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# Global state
sessions: Dict[str, Dict[str, Any]] = {}
supported_protocol_versions = ["2024-11-05", "2025-03-26"]

# Tools registry
tools = {}

# Register built-in tools
def register_tool(name, description, parameters, handler):
    """Register a tool with the server."""
    tools[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "handler": handler
    }

# Simple echo tool
def echo_handler(params):
    """Echo a message back to the client."""
    return params.get("message", "")

register_tool(
    "echo",
    "Echo a message back to the client.",
    {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to echo."
            }
        },
        "required": ["message"]
    },
    echo_handler
)

# Add tool
def add_handler(params):
    """Add two numbers and return the result."""
    a = params.get("a", 0)
    b = params.get("b", 0)
    return a + b

register_tool(
    "add",
    "Add two numbers and return the result.",
    {
        "type": "object",
        "properties": {
            "a": {
                "type": "number",
                "description": "First number."
            },
            "b": {
                "type": "number",
                "description": "Second number."
            }
        },
        "required": ["a", "b"]
    },
    add_handler
)

# Sleep tool (async)
async def sleep_handler(params):
    """Sleep for the specified number of seconds."""
    seconds = params.get("seconds", 1)
    await asyncio.sleep(seconds)
    return f"Slept for {seconds} seconds"

register_tool(
    "sleep",
    "Sleep for the specified number of seconds (async).",
    {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": "Number of seconds to sleep."
            }
        },
        "required": ["seconds"]
    },
    sleep_handler
)

@app.options("/mcp")
async def options_handler():
    """Handle OPTIONS requests for CORS."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id",
            "Access-Control-Expose-Headers": "Mcp-Session-Id"
        }
    )

@app.post("/mcp")
async def mcp_handler(request: Request, 
                      response: Response,
                      mcp_session_id: Optional[str] = Header(None)):
    """Handle MCP requests."""
    # Get or create session
    session_id = mcp_session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {
            "initialized": False,
            "protocol_version": None
        }
    
    # Parse JSON-RPC request
    try:
        data = await request.json()
        logger.debug(f"Received request: {data}")
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            },
            status_code=400
        )
    
    # Validate JSON-RPC request
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request"
                },
                "id": data.get("id")
            },
            status_code=400
        )
    
    # Get method, id, and params
    method = data.get("method")
    request_id = data.get("id")
    params = data.get("params", {})
    
    # Always include session ID in response headers
    response.headers["Mcp-Session-Id"] = session_id
    
    # Process method
    session = sessions[session_id]
    result = None
    error = None
    
    if method == "initialize":
        # Handle initialize method
        protocol_version = params.get("protocol_version")
        if not protocol_version:
            error = {
                "code": -32602,
                "message": "Missing protocol_version parameter"
            }
        elif protocol_version not in supported_protocol_versions:
            error = {
                "code": -32602,
                "message": f"Unsupported protocol version: {protocol_version}"
            }
        elif session.get("initialized"):
            error = {
                "code": -32002,
                "message": "Server already initialized"
            }
        else:
            session["initialized"] = True
            session["protocol_version"] = protocol_version
            result = {
                "capabilities": {
                    "tools": True,
                    "async": True
                },
                "server_info": {
                    "name": "MCP HTTP Server",
                    "version": "1.0.0"
                }
            }
    
    elif not session.get("initialized"):
        # All other methods require initialization
        error = {
            "code": -32001,
            "message": "Server not initialized"
        }
    
    elif method == "shutdown":
        # Handle shutdown method
        session["initialized"] = False
        result = True
    
    elif method == "exit":
        # Handle exit method
        if session_id in sessions:
            del sessions[session_id]
        result = True
    
    elif method == "reset":
        # Handle reset method (non-standard but useful for testing)
        session["initialized"] = False
        result = True
    
    elif method == "list_tools":
        # Handle list_tools method
        tool_list = []
        for name, tool in tools.items():
            tool_list.append({
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            })
        result = {"tools": tool_list}
    
    else:
        # Check if this is a tool call
        tool_name = method
        if tool_name in tools:
            try:
                # Call the tool handler
                tool = tools[tool_name]
                handler = tool["handler"]
                
                # Handle async tools
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(params)
                else:
                    result = handler(params)
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                error = {
                    "code": -32603,
                    "message": f"Error calling tool {tool_name}: {str(e)}"
                }
        else:
            error = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
    
    # Build response
    response_data = {"jsonrpc": "2.0", "id": request_id}
    
    if error:
        response_data["error"] = error
        status_code = 400 if error["code"] in [-32700, -32600, -32602] else 500
        if error["code"] == -32601:  # Method not found
            status_code = 404
        elif error["code"] == -32001:  # Not initialized
            status_code = 401
        elif error["code"] == -32002:  # Already initialized
            status_code = 409
    else:
        response_data["result"] = result
        status_code = 200
    
    logger.debug(f"Sending response: {response_data}")
    return JSONResponse(content=response_data, status_code=status_code)

def main():
    """Run the MCP HTTP server."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run a standard MCP HTTP server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8085, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Start the server
    print(f"Starting MCP HTTP server at http://{args.host}:{args.port}/mcp")
    print(f"Supported protocol versions: {', '.join(supported_protocol_versions)}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="debug" if args.debug else "info")

if __name__ == "__main__":
    main() 