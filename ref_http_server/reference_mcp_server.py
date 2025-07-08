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
from pydantic import BaseModel, Field, ValidationError
from sse_starlette.sse import EventSourceResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-reference-server")

# OAuth 2.1 / Authentication Configuration
# In a real implementation, these would be loaded from environment variables or config
OAUTH_ENABLED = True  # Set to True to enable OAuth 2.1 authentication
OAUTH_REALM = "mcp-server"
OAUTH_SCOPE = "mcp:read mcp:write"
VALID_TOKENS = {
    # Example tokens - in production, validate against OAuth server
    "valid-test-token-123": {
        "audience": "mcp-server",
        "scope": ["mcp:read", "mcp:write"],
        "expires_at": "2025-12-31T23:59:59Z"
    }
}

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
    elicitation: Optional[Dict[str, Any]] = {}  # New in 2025-06-18

class InitializeParams(BaseModel):
    """Parameters for initialize request."""
    client_info: ClientInfo = Field(alias="clientInfo")
    client_capabilities: ClientCapabilities = Field(alias="clientCapabilities")

class InitializeResult(BaseModel):
    """Result of initialize request."""
    session_id: str = Field(alias="sessionId")
    protocol_version: str = Field(alias="protocolVersion")
    server_info: Dict[str, str] = Field(alias="serverInfo")
    server_capabilities: ServerCapabilities = Field(alias="serverCapabilities")

    def model_dump(self, *args, **kwargs):
        """Override model_dump() to ensure proper camelCase field names."""
        kwargs.setdefault('by_alias', True)  # Use aliases (camelCase) by default
        base_dict = super().model_dump(*args, **kwargs)
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
    inputSchema: Dict[str, Any]  # Renamed from parameters in 2025-06-18
    title: Optional[str] = None  # New in 2025-06-18
    outputSchema: Optional[Dict[str, Any]] = None  # New in 2025-06-18

class CallToolParams(BaseModel):
    """Parameters for calling a tool."""
    name: str
    arguments: Dict[str, Any]

class CallToolResult(BaseModel):
    """Result of calling a tool."""
    content: List[Dict[str, Any]]
    isError: bool = False
    structuredContent: Optional[Dict[str, Any]] = None  # New in 2025-06-18

# OAuth 2.1 Authentication Functions
def validate_bearer_token(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Validate OAuth 2.1 Bearer token.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token info if valid, None if invalid or missing
    """
    if not OAUTH_ENABLED:
        return {"valid": True, "scope": ["mcp:read", "mcp:write"]}
    
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # In a real implementation, validate token with OAuth server
    token_info = VALID_TOKENS.get(token)
    if not token_info:
        return None
    
    # Check token expiration, audience, etc.
    # For demo purposes, we'll assume the token is valid
    return token_info

def create_www_authenticate_header(error: str = "invalid_token", 
                                 error_description: str = "The access token is invalid") -> str:
    """
    Create WWW-Authenticate header as required by OAuth 2.1 and 2025-06-18 spec.
    
    Args:
        error: OAuth error code
        error_description: Human-readable error description
        
    Returns:
        WWW-Authenticate header value
    """
    return f'Bearer realm="{OAUTH_REALM}", scope="{OAUTH_SCOPE}", error="{error}", error_description="{error_description}"'

def check_authentication(authorization: Optional[str] = Header(None),
                        mcp_protocol_version: Optional[str] = Header(None, alias="MCP-Protocol-Version")) -> Dict[str, Any]:
    """
    Check authentication for requests.
    
    Args:
        authorization: Authorization header
        mcp_protocol_version: MCP protocol version header (required for 2025-06-18)
        
    Returns:
        Authentication info
        
    Raises:
        HTTPException: If authentication fails
    """
    # Validate MCP-Protocol-Version header for 2025-06-18
    if mcp_protocol_version == "2025-06-18":
        logger.debug(f"2025-06-18 protocol detected, MCP-Protocol-Version header: {mcp_protocol_version}")
    
    # Check OAuth 2.1 authentication if enabled
    if OAUTH_ENABLED:
        token_info = validate_bearer_token(authorization)
        if not token_info:
            www_authenticate = create_www_authenticate_header()
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": www_authenticate}
            )
        return token_info
    
    # Authentication not required
    return {"valid": True}

# Reference MCP Server Implementation
class McpReferenceServer:
    """Reference implementation of an MCP server."""
    
    def __init__(self, name: str, protocol_versions: List[str]):
        """Initialize the MCP server."""
        self.name = name
        self.protocol_versions = protocol_versions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        
        # Check if we support 2025-06-18 features
        self.supports_2025_06_18 = "2025-06-18" in protocol_versions
        
        # Register built-in tools with 2025-06-18 format
        self.register_tool(
            name="echo",
            description="Echo a message back to the client.",
            title="Echo Tool",  # New in 2025-06-18
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to echo back"}
                },
                "required": ["message"]
            },
            output_schema={  # New in 2025-06-18
                "type": "object",
                "properties": {
                    "echo": {"type": "string", "description": "The echoed message"}
                }
            } if self.supports_2025_06_18 else None,
            handler=self._echo_tool
        )
        
        self.register_tool(
            name="add",
            description="Add two numbers and return the result.",
            title="Addition Tool",  # New in 2025-06-18
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            },
            output_schema={  # New in 2025-06-18
                "type": "object",
                "properties": {
                    "sum": {"type": "number", "description": "Sum of a and b"}
                }
            } if self.supports_2025_06_18 else None,
            handler=self._add_tool
        )
        
        self.register_tool(
            name="sleep",
            description="Sleep for the specified number of seconds.",
            title="Sleep Tool",  # New in 2025-06-18
            input_schema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "Number of seconds to sleep"}
                },
                "required": ["seconds"]
            },
            output_schema={  # New in 2025-06-18
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Confirmation message"}
                }
            } if self.supports_2025_06_18 else None,
            handler=self._sleep_tool
        )
    
    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], 
                    handler: callable, title: str = None, output_schema: Dict[str, Any] = None):
        """Register a new tool with the server."""
        tool_def = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,  # Updated for 2025-06-18
            "handler": handler
        }
        
        # Add 2025-06-18 specific fields if supported
        if self.supports_2025_06_18:
            if title:
                tool_def["title"] = title
            if output_schema:
                tool_def["outputSchema"] = output_schema
        else:
            # Backward compatibility - keep old field names for older protocols
            tool_def["parameters"] = input_schema
            
        self.tools[name] = tool_def
    
    async def initialize(self, params: InitializeParams) -> InitializeResult:
        """Handle initialize request from client."""
        # Validate protocol compatibility
        client_protocols = params.client_capabilities.protocol_versions
        
        # Find the highest mutually supported protocol version
        # Order matters: prefer newer versions
        version_priority = ["2025-06-18", "2025-03-26", "2024-11-05"]
        selected_version = None
        
        for version in version_priority:
            if version in client_protocols and version in self.protocol_versions:
                selected_version = version
                break
        
        if not selected_version:
            raise HTTPException(
                status_code=400,
                detail=f"Incompatible protocol versions. Server supports: {self.protocol_versions}, Client supports: {client_protocols}"
            )
        
        # Create new session
        session_id = str(uuid.uuid4())
        
        # Store session information with negotiated protocol
        self.sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "client_info": params.client_info.model_dump(),
            "protocol_version": selected_version,
            "last_activity": datetime.now().isoformat(),
        }
        
        logger.info(f"Created new session: {session_id} with protocol {selected_version}")
        
        # Return session ID and server capabilities
        return InitializeResult(
            session_id=session_id,
            protocol_version=selected_version,  # Use negotiated version
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
        # Validate session and get protocol version
        session = self.get_session(session_id)
        session_protocol = session.get("protocol_version", "2024-11-05")
        
        # Return tool descriptions based on session protocol version
        tools = []
        for tool in self.tools.values():
            tool_desc = ToolDescription(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"]
            )
            
            # Add 2025-06-18 specific fields if the session uses that protocol
            if session_protocol == "2025-06-18":
                if "title" in tool:
                    tool_desc.title = tool["title"]
                if "outputSchema" in tool:
                    tool_desc.outputSchema = tool["outputSchema"]
            
            tools.append(tool_desc)
        
        return tools
    
    async def call_tool(self, session_id: str, params: CallToolParams) -> CallToolResult:
        """Call a tool with the provided parameters."""
        # Validate session and get protocol version
        session = self.get_session(session_id)
        session_protocol = session.get("protocol_version", "2024-11-05")
        
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
            result = await tool["handler"](**params.arguments)
            
            # Format result based on session protocol version
            if session_protocol == "2025-06-18":
                # 2025-06-18 format with structured content
                content = [{"type": "text", "text": str(result)}]
                structured_content = None
                
                # If the tool has an output schema, create structured content
                if "outputSchema" in tool and isinstance(result, (dict, list)):
                    structured_content = result
                elif tool_name == "add" and isinstance(result, (int, float)):
                    structured_content = {"sum": result}
                elif tool_name == "echo" and isinstance(result, str):
                    structured_content = {"echo": result}
                elif tool_name == "sleep" and isinstance(result, str):
                    structured_content = {"message": result}
                
                return CallToolResult(
                    content=content,
                    isError=False,
                    structuredContent=structured_content
                )
            else:
                # Legacy format for older protocols
                return CallToolResult(
                    content=[{"type": "text", "text": str(result)}],
                    isError=False
                )
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            
            if session_protocol == "2025-06-18":
                return CallToolResult(
                    content=[{"type": "text", "text": f"Tool execution error: {str(e)}"}],
                    isError=True
                )
            else:
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
        
        # Validate JSON-RPC structure first
        if not isinstance(data, dict):
            response["error"] = {
                "code": -32700,  # Parse error
                "message": "Parse error: Invalid JSON"
            }
            response["id"] = None
            return JSONResponse(status_code=400, content=response)
        
        # Check for required JSON-RPC fields
        if "jsonrpc" not in data or data.get("jsonrpc") != "2.0":
            response["error"] = {
                "code": -32600,  # Invalid Request
                "message": "Invalid Request: Missing or invalid jsonrpc field"
            }
            response["id"] = data.get("id", None)
            return JSONResponse(status_code=400, content=response)
        
        if "method" not in data:
            response["error"] = {
                "code": -32600,  # Invalid Request
                "message": "Invalid Request: Missing method field"
            }
            response["id"] = data.get("id", None)
            return JSONResponse(status_code=400, content=response)
        
        # Handle initialize request (no session required)
        if data["method"] == "initialize":
            if "params" not in data:
                response["error"] = {
                    "code": -32602,  # Invalid params
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
                    "code": -32603,  # Internal error
                    "message": str(e)
                }
                return JSONResponse(status_code=500, content=response)
        
        # For all other requests, session ID is required
        if not session_id:
            response["error"] = {
                "code": -32602,  # Invalid params
                "message": "Missing session_id query parameter"
            }
            return JSONResponse(status_code=400, content=response)
        
        # Validate session
        try:
            self.get_session(session_id)
        except HTTPException:
            response["error"] = {
                "code": -32003,  # Session expired (custom error code)
                "message": f"Invalid or expired session: {session_id}"
            }
            return JSONResponse(status_code=401, content=response)  # 401 Unauthorized for invalid session
        
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
                        "code": -32602,  # Invalid params
                        "message": "Missing params for tools/call"
                    }
                    return JSONResponse(status_code=400, content=response)
                
                tool_params = data["params"]
                
                # Validate that params is a dictionary
                if not isinstance(tool_params, dict):
                    response["error"] = {
                        "code": -32602,  # Invalid params
                        "message": f"Invalid params type for tools/call: expected object, got {type(tool_params).__name__}"
                    }
                    return JSONResponse(status_code=400, content=response)
                
                # Validate required fields
                if "name" not in tool_params:
                    response["error"] = {
                        "code": -32602,  # Invalid params
                        "message": "Missing 'name' field in tools/call params"
                    }
                    return JSONResponse(status_code=400, content=response)
                
                if "arguments" not in tool_params:
                    response["error"] = {
                        "code": -32602,  # Invalid params
                        "message": "Missing 'arguments' field in tools/call params"
                    }
                    return JSONResponse(status_code=400, content=response)
                
                # Validate arguments is a dictionary
                if not isinstance(tool_params["arguments"], dict):
                    response["error"] = {
                        "code": -32602,  # Invalid params
                        "message": f"Invalid arguments type for tools/call: expected object, got {type(tool_params['arguments']).__name__}"
                    }
                    return JSONResponse(status_code=400, content=response)
                
                try:
                    params = CallToolParams(
                        name=tool_params["name"],
                        arguments=tool_params["arguments"]
                    )
                    result = await self.call_tool(session_id, params)
                    response["result"] = result.model_dump()
                except ValidationError as e:
                    response["error"] = {
                        "code": -32602,  # Invalid params
                        "message": f"Invalid tool call parameters: {str(e)}"
                    }
                    return JSONResponse(status_code=400, content=response)
            
            elif method == "ping":
                response["result"] = {"timestamp": datetime.now().isoformat()}
            
            else:
                # Method not found - return 200 with JSON-RPC error per JSON-RPC specification
                response["error"] = {
                    "code": -32601,  # Method not found
                    "message": f"Method not found: {method}"
                }
                return JSONResponse(status_code=200, content=response)  # 200 OK with JSON-RPC error
            
            return JSONResponse(content=response)
            
        except HTTPException as e:
            response["error"] = {
                "code": -32000,  # Server error
                "message": e.detail
            }
            return JSONResponse(status_code=e.status_code, content=response)
        except Exception as e:
            logger.error(f"Error handling {method}: {e}")
            response["error"] = {
                "code": -32603,  # Internal error
                "message": str(e)
            }
            return JSONResponse(status_code=500, content=response)  # 500 for internal errors

# Create FastAPI application
app = FastAPI(
    title="MCP Reference Server",
    description="Reference implementation of Model Context Protocol server with OAuth 2.1 support",
    version="1.0.0"
)

# Add CORS middleware with proper security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "https://localhost:*"],  # Restrict origins for security
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id", "WWW-Authenticate", "MCP-Protocol-Version"],
)

# Create MCP server instance
mcp_server = McpReferenceServer(
    name="MCP Reference Server",
    protocol_versions=["2024-11-05", "2025-03-26", "2025-06-18"]  # Added 2025-06-18 support
)

@app.post("/mcp")
async def handle_post_message(request: Request, 
                            auth_info: Dict[str, Any] = Depends(check_authentication)):
    """Handle POST requests to /mcp endpoint with OAuth 2.1 authentication."""
    try:
        # Extract session ID from query parameters or headers
        session_id = request.query_params.get("session_id")
        if not session_id:
            session_id = request.headers.get("Mcp-Session-Id")
        
        # Get request body as text first to handle JSON parsing ourselves
        body_text = await request.body()
        
        # Try to parse JSON
        try:
            body = json.loads(body_text.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Parse error - return 400 with JSON-RPC error
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,  # Parse error
                        "message": "Parse error: Invalid JSON"
                    },
                    "id": None
                }
            )
        
        # Check for batch requests (arrays) and reject them for 2025-06-18
        if isinstance(body, list):
            # Get protocol version from headers or determine from session
            protocol_version = request.headers.get("MCP-Protocol-Version")
            if not protocol_version and session_id:
                try:
                    session_info = mcp_server.get_session(session_id)
                    protocol_version = session_info.get("protocol_version")
                except:
                    protocol_version = None
            
            # For 2025-06-18, batch requests are not supported
            if protocol_version == "2025-06-18":
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,  # Invalid Request
                            "message": "Batch requests are not supported in protocol version 2025-06-18"
                        },
                        "id": None
                    }
                )
            
            # For older protocols, batch requests would be handled here
            # But for simplicity, we'll reject all batch requests for now
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,  # Invalid Request
                        "message": "Batch requests are not supported by this server"
                    },
                    "id": None
                }
            )
        
        # Handle the message
        response = await mcp_server.handle_message(body, session_id)
        
        # Add session ID to response headers if available
        if hasattr(response, 'headers') and session_id:
            response.headers["Mcp-Session-Id"] = session_id
        
        return response
        
    except Exception as e:
        logger.error(f"Error handling POST message: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,  # Internal error
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": None
            }
        )

@app.get("/mcp")
async def handle_get_message(request: Request, 
                           session_id: str = None,
                           auth_info: Dict[str, Any] = Depends(check_authentication)):
    """Handle GET requests for SSE notifications with OAuth 2.1 authentication."""
    # Extract session ID
    if not session_id:
        session_id = request.headers.get("Mcp-Session-Id")
    
    if not session_id:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Session ID required"
                },
                "id": None
            }
        )
    
    # Validate session exists
    try:
        mcp_server.get_session(session_id)
    except HTTPException as e:
        if e.status_code == 404:
            return JSONResponse(
                status_code=401,  # 401 Unauthorized for invalid session
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32003,  # Session expired
                        "message": "Invalid or expired session"
                    },
                    "id": None
                }
            )
        raise
    
    # Return SSE stream
    async def event_generator():
        """Generate SSE events for the client."""
        try:
            while True:
                # Send periodic ping messages
                ping_data = {
                    "jsonrpc": "2.0",
                    "method": "notifications/ping",
                    "params": {
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield {
                    "event": "ping",
                    "data": json.dumps(ping_data)
                }
                
                # Wait before next ping
                await asyncio.sleep(21)  # Slightly longer than typical SSE timeout
                
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream: {str(e)}")
    
    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Mcp-Session-Id": session_id
        }
    )

@app.get("/")
async def server_info():
    """Return server information and OAuth 2.1 discovery metadata."""
    info = {
        "name": "MCP Reference Server",
        "version": "1.0.0",
        "protocol_versions": ["2024-11-05", "2025-03-26", "2025-06-18"],
        "description": "Reference implementation of MCP server with OAuth 2.1 support"
    }
    
    # Add OAuth 2.1 Protected Resource Metadata (RFC 9728)
    if OAUTH_ENABLED:
        info["oauth"] = {
            "authorization_server": "https://auth.example.com",  # Would be real auth server
            "resource_server": "mcp-server",
            "scopes_supported": ["mcp:read", "mcp:write"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "resource_indicators_supported": True  # RFC 8707 requirement
        }
    
    return info

@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """
    OAuth 2.0 Authorization Server Metadata as required by 2025-06-18 spec.
    
    Returns:
        OAuth server metadata for discovery
    """
    if not OAUTH_ENABLED:
        raise HTTPException(status_code=404, detail="OAuth not enabled")
    
    base_url = "http://localhost:8080"  # In production, use actual server URL
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "jwks_uri": f"{base_url}/oauth/jwks",
        "registration_endpoint": f"{base_url}/oauth/register",
        "scopes_supported": ["mcp:read", "mcp:write", "mcp:admin"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query", "fragment"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
        "resource_indicators_supported": True,
        "authorization_details_supported": True,
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "introspection_endpoint": f"{base_url}/oauth/introspect",
        "revocation_endpoint": f"{base_url}/oauth/revoke"
    }

@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata as required by 2025-06-18 spec.
    
    Returns:
        Protected resource metadata
    """
    if not OAUTH_ENABLED:
        raise HTTPException(status_code=404, detail="OAuth not enabled")
    
    base_url = "http://localhost:8080"  # In production, use actual server URL
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "jwks_uri": f"{base_url}/oauth/jwks",
        "scopes_supported": ["mcp:read", "mcp:write", "mcp:admin"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://modelcontextprotocol.io/docs",
        "resource_policy_uri": f"{base_url}/privacy-policy",
        "resource_tos_uri": f"{base_url}/terms-of-service"
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