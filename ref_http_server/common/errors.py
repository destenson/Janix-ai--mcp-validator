"""Error handling for MCP HTTP server implementations."""
from enum import IntEnum
from typing import Any, Dict, Optional


class ErrorCodes(IntEnum):
    """JSON-RPC 2.0 error codes for MCP."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP specific error codes
    SESSION_NOT_FOUND = -32000
    INVALID_SESSION = -32001
    TOOL_NOT_FOUND = -32002
    TOOL_ERROR = -32003
    RESOURCE_EXHAUSTED = -32004


class MCPError(Exception):
    """Base exception class for MCP errors."""
    
    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize MCP error.
        
        Args:
            code: JSON-RPC error code
            message: Error message
            data: Optional additional error data
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to JSON-RPC error object.
        
        Returns:
            Dict containing error code, message and optional data
        """
        error = {
            "code": self.code,
            "message": self.message,
        }
        if self.data:
            error["data"] = self.data
        return error


class ParseError(MCPError):
    """Invalid JSON was received."""
    def __init__(self, message: str = "Parse error", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.PARSE_ERROR, message, data)


class InvalidRequest(MCPError):
    """The JSON sent is not a valid Request object."""
    def __init__(self, message: str = "Invalid Request", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.INVALID_REQUEST, message, data)


class MethodNotFound(MCPError):
    """The method does not exist / is not available."""
    def __init__(self, message: str = "Method not found", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.METHOD_NOT_FOUND, message, data)


class InvalidParams(MCPError):
    """Invalid method parameters."""
    def __init__(self, message: str = "Invalid params", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.INVALID_PARAMS, message, data)


class InternalError(MCPError):
    """Internal JSON-RPC error."""
    def __init__(self, message: str = "Internal error", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.INTERNAL_ERROR, message, data)


class SessionNotFound(MCPError):
    """Session ID not found."""
    def __init__(self, message: str = "Session not found", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.SESSION_NOT_FOUND, message, data)


class InvalidSession(MCPError):
    """Invalid session state."""
    def __init__(self, message: str = "Invalid session", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.INVALID_SESSION, message, data)


class ToolNotFound(MCPError):
    """Requested tool not found."""
    def __init__(self, message: str = "Tool not found", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.TOOL_NOT_FOUND, message, data)


class ToolError(MCPError):
    """Error executing tool."""
    def __init__(self, message: str = "Tool error", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.TOOL_ERROR, message, data)


class ResourceExhausted(MCPError):
    """Resource limits exceeded."""
    def __init__(self, message: str = "Resource exhausted", data: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.RESOURCE_EXHAUSTED, message, data) 