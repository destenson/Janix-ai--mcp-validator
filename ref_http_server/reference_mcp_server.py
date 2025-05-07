#!/usr/bin/env python3
"""
MCP Reference Server Implementation

This is a clean-room implementation of an MCP server that follows the specification
correctly, focusing on proper session management and protocol compliance.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response, WebSocket, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-reference-server")

# Define MCP protocol models
class ClientInfo(BaseModel):
    """Client information provided during initialization."""
    name: str
    version: str

class ClientCapabilities(BaseModel):
    """Client capabilities provided during initialization."""
    protocol_versions: List[str]
    roots: Optional[Dict[str, bool]] = None
    sampling: Optional[Dict[str, Any]] = None

class ServerCapabilities(BaseModel):
    """Server capabilities returned during initialization."""
    protocol_versions: List[str]
    logging: Dict[str, Any] = {}
    prompts: Dict[str, bool] = {"listChanged": True}
    resources: Dict[str, bool] = {"subscribe": True, "listChanged": True}
    tools: Dict[str, bool] = {"listChanged": True}

class InitializeParams(BaseModel):
    """Parameters for initialize request."""
    client_info: ClientInfo
    client_capabilities: ClientCapabilities

class InitializeResult(BaseModel):
    """Result of initialize request."""
    session_id: str
    protocol_version: str
    server_info: Dict[str, str]
    server_capabilities: ServerCapabilities

    def model_dump(self, *args, **kwargs):
        """Override model_dump() to ensure all fields are included."""
        base_dict = super().model_dump(*args, **kwargs)
        base_dict["server_capabilities"] = self.server_capabilities.model_dump()
        base_dict["server_info"] = self.server_info
        base_dict["protocol_version"] = self.protocol_version
        base_dict["session_id"] = self.session_id
        return base_dict

class JsonRpcRequest(BaseModel):
    """JSON-RPC request format."""
    jsonrpc: str = "2.0"
    id: Union[int, str]
    method: str
    params: Optional[Dict[str, Any]] = None

class JsonRpcResponse(BaseModel):
    """JSON-RPC response format."""
    jsonrpc: str = "2.0"
    id: Union[int, str]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class ToolDescription(BaseModel):
    """Description of a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]

class CallToolParams(BaseModel):
    """Parameters for calling a tool."""
    name: str
    parameters: Dict[str, Any]

class CallToolResult(BaseModel):
    """Result of calling a tool."""
    output: Any

# Reference MCP Server Implementation
class McpReferenceServer:
    """Reference implementation of an MCP server."""
    
    def __init__(self, name: str, protocol_versions: List[str]):
        """Initialize the MCP server."""
        self.name = name
        self.protocol_versions = protocol_versions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in tools
        self.register_tool(
            name="echo",
            description="Echo a message back to the client.",
            parameters={"message": {"type": "string", "description": "Message to echo back"}},
            returns={"type": "string", "description": "The echoed message"},
            handler=self._echo_tool
        )
        
        self.register_tool(
            name="add",
            description="Add two numbers and return the result.",
            parameters={
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            returns={"type": "number", "description": "Sum of a and b"},
            handler=self._add_tool
        )
        
        self.register_tool(
            name="sleep",
            description="Sleep for the specified number of seconds.",
            parameters={
                "seconds": {"type": "number", "description": "Number of seconds to sleep"}
            },
            returns={"type": "string", "description": "Confirmation message"},
            handler=self._sleep_tool
        )
    
    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], 
                    returns: Dict[str, Any], handler: callable):
        """Register a new tool with the server."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "returns": returns,
            "handler": handler
        }
    
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Handle initialize request from client."""
        # Validate protocol compatibility
        client_protocols = params.client_capabilities.protocol_versions
        compatible = any(proto in self.protocol_versions for proto in client_protocols)
        
        if not compatible:
            raise HTTPException(
                status_code=400,
                detail=f"Incompatible protocol versions. Server supports: {self.protocol_versions}"
            )
        
        # Create new session
        session_id = str(uuid.uuid4())
        
        # Store session information
        self.sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "client_info": params.client_info.model_dump(),
            "last_activity": datetime.now().isoformat(),
        }
        
        logger.info(f"Created new session: {session_id}")
        
        # Return session ID and server capabilities
        return InitializeResult(
            session_id=session_id,
            protocol_version=self.protocol_versions[0],  # Use first supported version
            server_info={
                "name": self.name,
                "version": "1.0.0"
            },
            server_capabilities=ServerCapabilities(
                protocol_versions=self.protocol_versions
            )
        )
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session by ID, raising exception if not found."""
        if session_id not in self.sessions:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        # Update last activity timestamp
        self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
        return self.sessions[session_id]
    
    async def list_tools(self, session_id: str) -> List[ToolDescription]:
        """List available tools."""
        # Validate session
        self.get_session(session_id)
        
        # Return tool descriptions
        return [
            ToolDescription(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                returns=tool["returns"]
            )
            for tool in self.tools.values()
        ]
    
    async def call_tool(self, session_id: str, params: CallToolParams) -> CallToolResult:
        """Call a tool with the provided parameters."""
        # Validate session
        self.get_session(session_id)
        
        # Check if tool exists
        tool_name = params.name
        if tool_name not in self.tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool not found: {tool_name}"
            )
        
        # Get tool
        tool = self.tools[tool_name]
        
        try:
            # Call tool handler
            result = await tool["handler"](**params.parameters)
            return CallToolResult(output=result)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Tool execution error: {str(e)}"
            )
    
    # Tool implementations
    async def _echo_tool(self, message: str) -> str:
        """Echo a message back to the client."""
        logger.debug(f"Echo tool called with message: {message}")
        return message
    
    async def _add_tool(self, a: float, b: float) -> float:
        """Add two numbers and return the result."""
        logger.debug(f"Add tool called with a={a}, b={b}")
        return a + b
    
    async def _sleep_tool(self, seconds: float) -> str:
        """Sleep for the specified number of seconds."""
        logger.debug(f"Sleep tool called with seconds={seconds}")
        await asyncio.sleep(seconds)
        return f"Slept for {seconds} seconds"

    async def handle_message(self, data: Dict[str, Any], session_id: Optional[str] = None) -> JSONResponse:
        """Handle an MCP message."""
        # Create JSON-RPC response template
        response = {
            "jsonrpc": "2.0"
        }
        
        # Add ID if present (not a notification)
        if "id" in data:
            response["id"] = data["id"]
        
        # Handle initialize request (no session required)
        if data["method"] == "initialize":
            if "params" not in data:
                response["error"] = {
                    "code": -32602,
                    "message": "Missing params for initialize"
                }
                return JSONResponse(status_code=400, content=response)
            
            try:
                params = InitializeParams(**data["params"])
                result = await self.initialize(params)
                response["result"] = result.model_dump()
                # Set session ID header
                response_obj = JSONResponse(content=response)
                response_obj.headers["Mcp-Session-Id"] = result.session_id
                return response_obj
            except Exception as e:
                logger.error(f"Error handling initialize: {e}")
                response["error"] = {
                    "code": -32603,
                    "message": str(e)
                }
                return JSONResponse(content=response)
        
        # For all other requests, session ID is required
        if not session_id:
            response["error"] = {
                "code": -32602,
                "message": "Missing session_id query parameter"
            }
            return JSONResponse(status_code=400, content=response)
        
        # Validate session
        try:
            self.get_session(session_id)
        except HTTPException:
            response["error"] = {
                "code": -32000,
                "message": f"Session not found: {session_id}"
            }
            return JSONResponse(status_code=404, content=response)
        
        # Handle notifications (no ID)
        if "id" not in data:
            if data["method"] == "notifications/initialized":
                # Always return 202 for notifications with empty content
                return JSONResponse(
                    status_code=202,
                    content={}
                )
            return JSONResponse(
                status_code=202,
                content={}
            )
        
        # Handle regular methods (with ID)
        try:
            method = data["method"]
            
            if method == "tools/list":
                tools = await self.list_tools(session_id)
                response["result"] = {"tools": [tool.model_dump() for tool in tools]}
            
            elif method == "tools/call":
                if "params" not in data:
                    response["error"] = {
                        "code": -32602,
                        "message": "Missing params for tools/call"
                    }
                    return JSONResponse(status_code=400, content=response)
                tool_params = data["params"]
                params = CallToolParams(
                    name=tool_params["name"],
                    parameters=tool_params["arguments"]
                )
                result = await self.call_tool(session_id, params)
                response["result"] = result.model_dump()
            
            elif method == "ping":
                response["result"] = {"timestamp": datetime.now().isoformat()}
            
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
                return JSONResponse(status_code=400, content=response)
            
            return JSONResponse(content=response)
            
        except HTTPException as e:
            response["error"] = {
                "code": -32000,
                "message": e.detail
            }
            return JSONResponse(status_code=e.status_code, content=response)
        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            response["error"] = {
                "code": -32603,
                "message": str(e)
            }
            return JSONResponse(content=response)

# Create FastAPI application
app = FastAPI(
    title="MCP Reference Server",
    # Disable automatic response model to allow SSE streaming
    response_model=None,
    # Configure CORS
    default_response_class=JSONResponse
)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"]
)

# Create MCP server instance
mcp_server = McpReferenceServer(
    name="MCP Reference Server",
    protocol_versions=["2025-03-26"]
)

# Handle HTTP methods
@app.post("/messages")
async def handle_post_message(request: Request):
    """Handle POST requests to /messages endpoint."""
    try:
        data = await request.json()
        logger.debug(f"Received message: {data}")
        
        # Handle batch requests
        if isinstance(data, list):
            try:
                responses = []
                for request_item in data:
                    # Process each request
                    response = await mcp_server.handle_message(
                        request_item,
                        request.query_params.get("session_id")
                    )
                    if response.status_code == 200:
                        responses.append(json.loads(response.body))
                    else:
                        # Return error response directly
                        return response
                
                # Return combined responses
                return JSONResponse(content=responses)
            except Exception as e:
                logger.error(f"Error handling batch request: {e}")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid batch request format"}
                )
        
        # Handle single request
        return await mcp_server.handle_message(
            data,
            request.query_params.get("session_id")
        )
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"}
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/messages")
async def handle_get_message(request: Request, session_id: str = None):
    """Handle GET requests to /messages endpoint."""
    # Check if client accepts SSE
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" not in accept_header:
        return JSONResponse(
            status_code=400,
            content={"error": "Client must accept text/event-stream"}
        )
        
    if not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing session_id query parameter"}
        )
    
    # Validate session
    try:
        mcp_server.get_session(session_id)
    except HTTPException:
        return JSONResponse(
            status_code=404,
            content={"error": f"Session not found: {session_id}"}
        )
    
    # Define SSE event generator
    async def event_generator():
        """Generate SSE events for the client."""
        try:
            # Send initial connection established event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/connected",
                    "params": {
                        "timestamp": datetime.now().isoformat()
                    }
                })
            }
            
            # Keep connection alive with periodic pings
            while True:
                await asyncio.sleep(30)
                # Check if session still exists
                try:
                    mcp_server.get_session(session_id)
                    yield {
                        "event": "ping",
                        "data": json.dumps({
                            "jsonrpc": "2.0",
                            "method": "notifications/ping",
                            "params": {
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                    }
                except HTTPException:
                    # Session expired, close connection
                    logger.info(f"Session {session_id} expired, closing SSE connection")
                    break
        except Exception as e:
            logger.error(f"Error in SSE event generator: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/error",
                    "params": {
                        "message": str(e)
                    }
                })
            }
    
    # Return SSE response with proper headers
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )

# Server info endpoint
@app.get("/")
async def server_info():
    """Return information about the server."""
    return {
        "name": mcp_server.name,
        "protocol_versions": mcp_server.protocol_versions,
        "tools_count": len(mcp_server.tools),
        "active_sessions": len(mcp_server.sessions)
    }

def main():
    """Run the server."""
    parser = argparse.ArgumentParser(description="Run MCP Reference Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8088, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Start server
    logger.info(f"Starting MCP Reference Server at http://{args.host}:{args.port}")
    logger.info(f"Protocol versions: {mcp_server.protocol_versions}")
    logger.info(f"Available tools: {', '.join(mcp_server.tools.keys())}")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

if __name__ == "__main__":
    main() 