"""Error handling for MCP reference HTTP servers."""

from enum import IntEnum
from typing import Any, Dict, Optional


class ErrorCodes(IntEnum):
    """JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000
    UNINITIALIZED = -32001
    INVALID_PROTOCOL_VERSION = -32002


class MCPError(Exception):
    """Base class for MCP protocol errors."""
    def __init__(self, message: str, code: int = ErrorCodes.INTERNAL_ERROR, data: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}

    def to_response(self, request_id: Any = None) -> Dict[str, Any]:
        """Convert error to JSON-RPC response format"""
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": self.code,
                "message": self.message
            },
            "id": request_id
        }
        if self.data is not None:
            response["error"]["data"] = self.data
        return response

class ParseError(MCPError):
    def __init__(self, message: str = "Parse error", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.PARSE_ERROR, data)

class InvalidRequest(MCPError):
    def __init__(self, message: str = "Invalid Request", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.INVALID_REQUEST, data)

class MethodNotFound(MCPError):
    def __init__(self, message: str = "Method not found", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.METHOD_NOT_FOUND, data)

class InvalidParams(MCPError):
    def __init__(self, message: str = "Invalid params", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.INVALID_PARAMS, data)

class InternalError(MCPError):
    def __init__(self, message: str = "Internal error", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.INTERNAL_ERROR, data)

class ProtocolError(MCPError):
    def __init__(self, message: str = "Protocol error", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.SERVER_ERROR_START, data)

class UninitializedError(MCPError):
    def __init__(self, message: str = "Server not initialized", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.UNINITIALIZED, data)

class InvalidProtocolVersion(MCPError):
    def __init__(self, message: str = "Invalid protocol version", data: Optional[Any] = None):
        super().__init__(message, ErrorCodes.INVALID_PROTOCOL_VERSION, data) 