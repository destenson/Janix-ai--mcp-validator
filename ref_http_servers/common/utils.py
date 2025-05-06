"""Utilities for MCP reference HTTP servers."""

import json
from typing import Any, Dict, Optional, Union

from .errors import MCPError, ErrorCodes


def validate_request(request_data: Union[str, bytes, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and parse a JSON-RPC request.
    
    Args:
        request_data: The raw request data to validate
        
    Returns:
        Dict containing the parsed request
        
    Raises:
        MCPError: If the request is invalid
    """
    try:
        if isinstance(request_data, (str, bytes)):
            request = json.loads(request_data)
        else:
            request = request_data
    except json.JSONDecodeError:
        raise MCPError("Invalid JSON", code=ErrorCodes.PARSE_ERROR)
        
    if not isinstance(request, dict):
        raise MCPError("Request must be an object", code=ErrorCodes.INVALID_REQUEST)
        
    if request.get('jsonrpc') != '2.0':
        raise MCPError("Invalid jsonrpc version", code=ErrorCodes.INVALID_REQUEST)
        
    if 'method' not in request:
        raise MCPError("Missing method", code=ErrorCodes.INVALID_REQUEST)
        
    if not isinstance(request['method'], str):
        raise MCPError("Method must be string", code=ErrorCodes.INVALID_REQUEST)
        
    return request


def format_response(result: Any = None, error: Optional[MCPError] = None, 
                   request_id: Any = None) -> Dict[str, Any]:
    """Format a JSON-RPC response.
    
    Args:
        result: The result of the method call
        error: Optional error that occurred
        request_id: The ID from the request
        
    Returns:
        Dict containing the formatted response
    """
    response = {
        'jsonrpc': '2.0',
        'id': request_id
    }
    
    if error is not None:
        response['error'] = {
            'code': error.code,
            'message': error.message
        }
        if error.data:
            response['error']['data'] = error.data
    else:
        response['result'] = result
        
    return response 