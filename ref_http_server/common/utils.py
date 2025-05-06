"""Utility functions for MCP HTTP server implementations."""

import json
from typing import Any, Dict, Optional, Union

from .errors import InvalidRequest, ParseError


def validate_request(request_text: str) -> Dict[str, Any]:
    """Validate and parse JSON-RPC request.
    
    Args:
        request_text: Raw JSON-RPC request string
        
    Returns:
        Parsed request object
        
    Raises:
        ParseError: If request is not valid JSON
        InvalidRequest: If request is not valid JSON-RPC 2.0
    """
    try:
        request = json.loads(request_text)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON: {str(e)}")
        
    if not isinstance(request, dict):
        raise InvalidRequest("Request must be an object")
        
    if request.get("jsonrpc") != "2.0":
        raise InvalidRequest("Invalid jsonrpc version")
        
    if "method" not in request:
        raise InvalidRequest("Missing method")
        
    if not isinstance(request["method"], str):
        raise InvalidRequest("Method must be string")
        
    if "id" in request and not isinstance(request["id"], (int, str, type(None))):
        raise InvalidRequest("Invalid id type")
        
    return request


def format_response(
    result: Optional[Any] = None,
    error: Optional[Dict[str, Any]] = None,
    id: Optional[Union[int, str]] = None
) -> Dict[str, Any]:
    """Format JSON-RPC response.
    
    Args:
        result: Response result (mutually exclusive with error)
        error: Response error (mutually exclusive with result) 
        id: Request ID
        
    Returns:
        Formatted JSON-RPC response object
    """
    response = {"jsonrpc": "2.0"}
    
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
        
    if id is not None:
        response["id"] = id
        
    return response 