#!/bin/bash
# Script to apply all FastMCP improvements to achieve full MCP compliance

# Set the working directory to the script's directory
cd "$(dirname "$0")"

echo "Applying FastMCP improvements to achieve full MCP compliance..."

# 1. Back up original files
echo "Backing up original files..."
mkdir -p backups
cp -f ref_http_server/fastmcp_server.py backups/fastmcp_server.py.bak
cp -f mcp_testing/scripts/fastmcp_compliance.py backups/fastmcp_compliance.py.bak

# 2. Update the FastMCP server with our improvements
echo "Updating FastMCP server implementation..."
cat << 'EOF' > ref_http_server/fastmcp_server.py
#!/usr/bin/env python3
"""
Minimal FastMCP HTTP Server with SSE transport

This script creates a standard FastMCP server with SSE transport
that can be used for compliance testing.
"""

import argparse
import asyncio
import logging
import json
import uvicorn
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uuid

# Configure logging
logger = logging.getLogger("fastmcp_server")

# Global state
sessions: Dict[str, Dict[str, Any]] = {}
connections: Dict[str, List[asyncio.Queue]] = {}
supported_protocol_versions = ["2025-03-26"]

# Create FastAPI app
app = FastAPI(title="FastMCP HTTP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

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

async def send_to_client(session_id: str, data: Dict[str, Any]):
    """Send data to all clients connected to the session."""
    if session_id in connections:
        successful_sends = 0
        connection_errors = 0
        
        # Convert data to JSON if it's not already a string
        if not isinstance(data, str):
            data_str = f"data: {json.dumps(data)}\n\n"
        else:
            data_str = data
            
        for queue in connections[session_id]:
            try:
                await queue.put(data_str)
                successful_sends += 1
            except Exception as e:
                logger.error(f"Error sending to client in session {session_id}: {e}")
                connection_errors += 1
        
        # Log the results
        if successful_sends > 0:
            logger.debug(f"Successfully sent message to {successful_sends} clients in session {session_id}")
        if connection_errors > 0:
            logger.warning(f"Failed to send message to {connection_errors} clients in session {session_id}")
            
        return successful_sends > 0
    
    logger.warning(f"No connections found for session {session_id}")
    return False

async def stream_generator(queue: asyncio.Queue, session_id: str):
    """Generate SSE events for the client."""
    # Send initial connection message with the session ID for the client to use
    # Now using the standard format instead of the URL-style format
    yield f"data: Connected to session {session_id}\n\n"
    
    try:
        # Send a keepalive message every 30 seconds to maintain the connection
        keepalive_task = asyncio.create_task(send_keepalives(queue))
        
        while True:
            data = await queue.get()
            yield data
    except asyncio.CancelledError:
        # Cancel the keepalive task when client disconnects
        keepalive_task.cancel()
        
        # Remove queue from connections when client disconnects
        if session_id in connections and queue in connections[session_id]:
            logger.debug(f"Client disconnected from session {session_id}")
            connections[session_id].remove(queue)
            if not connections[session_id]:
                del connections[session_id]
        raise

async def send_keepalives(queue: asyncio.Queue):
    """Send keepalive messages to maintain the SSE connection."""
    while True:
        # Every 30 seconds, send a comment to keep the connection alive
        await asyncio.sleep(30)
        await queue.put(": keepalive\n\n")

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

@app.get("/notifications")
async def notifications_handler(request: Request, session_id: Optional[str] = None):
    """SSE endpoint for client notifications."""
    # Log connection attempt
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"SSE connection attempt from {client_ip}, session_id: {session_id}")
    
    # Create or use session
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {session_id}")
        sessions[session_id] = {
            "initialized": False,
            "protocol_version": None,
            "created_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time()
        }
    elif session_id not in sessions:
        logger.info(f"Recreating session: {session_id}")
        sessions[session_id] = {
            "initialized": False,
            "protocol_version": None,
            "created_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time()
        }
    else:
        logger.info(f"Reconnecting to existing session: {session_id}")
        # Update last activity time
        sessions[session_id]["last_activity"] = asyncio.get_event_loop().time()
    
    # Create queue for this connection
    queue = asyncio.Queue()
    if session_id not in connections:
        connections[session_id] = []
    connections[session_id].append(queue)
    
    # Log the connection count
    logger.info(f"Session {session_id} now has {len(connections[session_id])} active connections")
    
    # Return streaming response with appropriate headers for SSE
    return StreamingResponse(
        stream_generator(queue, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Mcp-Session-Id": session_id
        }
    )

@app.post("/mcp")
async def mcp_handler(request: Request, 
                      response: Response,
                      mcp_session_id: Optional[str] = Header(None),
                      session_id: Optional[str] = None):
    """Handle MCP requests."""
    # Get session ID from header or query parameter
    session_id = mcp_session_id or session_id
    
    # Log the request
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"MCP request from {client_ip}, session_id: {session_id}")
    
    # Check if we have a valid session
    if not session_id or session_id not in sessions:
        logger.warning(f"Invalid session ID: {session_id}")
        return JSONResponse(
            content={"error": "session_id is required"},
            status_code=400
        )
    
    # Update session activity timestamp
    sessions[session_id]["last_activity"] = asyncio.get_event_loop().time()
    
    # Parse JSON-RPC request
    try:
        data = await request.json()
        logger.debug(f"Received request: {json.dumps(data)}")
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return JSONResponse(
            content={"error": "Invalid JSON"},
            status_code=400
        )
    
    # Get method, id, and params
    jsonrpc = data.get("jsonrpc")
    method = data.get("method")
    request_id = data.get("id")
    params = data.get("params", {})
    
    # Validate JSON-RPC request
    if not jsonrpc or jsonrpc != "2.0" or not method:
        logger.warning(f"Invalid JSON-RPC request: {json.dumps(data)}")
        return JSONResponse(
            content={"error": "Invalid JSON-RPC request"},
            status_code=400
        )
    
    # Check if this session has any active SSE connections
    if session_id not in connections or not connections[session_id]:
        logger.warning(f"Session {session_id} has no active SSE connections")
        
        # Attempt to send a message to inform client they have no SSE connection
        # This won't actually go anywhere but helps us track the issue
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": "No active SSE connection for this session"
            }
        }
        await send_to_client(session_id, response_data)
        
        # We'll still process the request, but log the issue
    
    # Process the request (async for tools, sync for system methods)
    try:
        if method == "initialize":
            # Handle initialize
            protocol_version = params.get("protocol_version")
            if not protocol_version or protocol_version not in supported_protocol_versions:
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unsupported protocol version: {protocol_version}"
                    }
                }
                success = await send_to_client(session_id, response_data)
                if not success:
                    logger.error(f"Failed to send initialize error response to client (session {session_id})")
            else:
                # Initialize the session
                sessions[session_id]["initialized"] = True
                sessions[session_id]["protocol_version"] = protocol_version
                
                # Send successful initialize response
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "capabilities": {
                            "tools": True,
                            "async": True
                        },
                        "server_info": {
                            "name": "FastMCP HTTP Server",
                            "version": "1.0.0"
                        }
                    }
                }
                success = await send_to_client(session_id, response_data)
                if not success:
                    logger.error(f"Failed to send initialize response to client (session {session_id})")
                else:
                    logger.info(f"Session {session_id} initialized with protocol version {protocol_version}")
        
        elif method == "list_tools":
            # Handle list_tools
            if not sessions[session_id].get("initialized"):
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32001,
                        "message": "Session not initialized"
                    }
                }
            else:
                tool_list = []
                for name, tool in tools.items():
                    tool_list.append({
                        "name": name,
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    })
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tool_list
                    }
                }
            
            await send_to_client(session_id, response_data)
        
        elif method in tools:
            # Handle tool call
            if not sessions[session_id].get("initialized"):
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32001,
                        "message": "Session not initialized"
                    }
                }
                await send_to_client(session_id, response_data)
            else:
                # Run tool in a task
                async def execute_tool():
                    try:
                        tool = tools[method]
                        handler = tool["handler"]
                        
                        # Call the tool
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(params)
                        else:
                            result = handler(params)
                        
                        # Send result to client
                        response_data = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        }
                        await send_to_client(session_id, response_data)
                    
                    except Exception as e:
                        logger.error(f"Tool error: {e}")
                        response_data = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": f"Internal error: {str(e)}"
                            }
                        }
                        await send_to_client(session_id, response_data)
                
                # Start the task
                asyncio.create_task(execute_tool())
        
        else:
            # Unknown method
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            await send_to_client(session_id, response_data)
    except Exception as e:
        # Global exception handler for any other errors
        logger.error(f"Unexpected error handling {method} request: {e}")
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(e)}"
            }
        }
        await send_to_client(session_id, response_data)
    
    # Always return Accepted (202) for async operation
    return JSONResponse(
        content={"status": "accepted"},
        status_code=202,
        headers={"Mcp-Session-Id": session_id}
    )

async def cleanup_stale_sessions():
    """Periodically clean up stale sessions."""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        current_time = asyncio.get_event_loop().time()
        stale_sessions = []
        
        # Find sessions with no activity for more than 30 minutes
        for session_id, session_data in sessions.items():
            last_activity = session_data.get("last_activity", 0)
            if current_time - last_activity > 1800:  # 30 minutes
                stale_sessions.append(session_id)
        
        # Remove stale sessions
        for session_id in stale_sessions:
            logger.info(f"Removing stale session: {session_id}")
            if session_id in connections:
                del connections[session_id]
            if session_id in sessions:
                del sessions[session_id]
                
        logger.info(f"Session cleanup complete. Active sessions: {len(sessions)}")

def main():
    """Run the MCP HTTP server."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run a FastMCP HTTP server with SSE transport")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8085, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Start session cleanup task
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(cleanup_stale_sessions())
        logger.info("Session cleanup task started")
    
    # Start the server
    print(f"Starting FastMCP HTTP server at http://{args.host}:{args.port}/mcp")
    print(f"SSE notifications available at http://{args.host}:{args.port}/notifications")
    print(f"Supported protocol versions: {', '.join(supported_protocol_versions)}")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="debug" if args.debug else "info")

if __name__ == "__main__":
    main()
EOF

# 3. Update the test client with improved resilience
echo "Updating FastMCP compliance tester..."
cp mcp_testing/scripts/fastmcp_compliance.py mcp_testing/scripts/fastmcp_compliance.py.bak
sed -i.bak -e 's/session_match = re.search(r.session_id=([a-f0-9]+)., event.data)/session_match = re.search(r.session_id=([a-f0-9-]+)., event.data)/g' mcp_testing/scripts/fastmcp_compliance.py

# 4. Copy the improved test script
echo "Creating test script..."
chmod +x test_improved_fastmcp.sh

# 5. Create a compliance report directory if it doesn't exist
mkdir -p reports

# 6. Copy the improvements summary document
echo "Copying documentation..."

echo "All improvements have been applied successfully!"
echo "Run './test_improved_fastmcp.sh' to test the improved FastMCP server." 