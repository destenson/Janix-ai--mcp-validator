"""Method handlers for MCP 2024-11-05"""

from typing import Dict, Any, Callable, Optional
from ..common import (
    InvalidParams, MethodNotFound, create_response,
    get_request_id, format_error_response
)
from .session import Session

class MethodHandlers:
    """Handles MCP method calls for protocol version 2024-11-05"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {
            "initialize": self.handle_initialize,
            "shutdown": self.handle_shutdown,
            "filesystem/listDirectory": self.handle_list_directory,
            "filesystem/readFile": self.handle_read_file,
            "filesystem/writeFile": self.handle_write_file
        }
    
    def get_handler(self, method: str) -> Optional[Callable]:
        """Get handler for method if it exists"""
        return self._handlers.get(method)
    
    def handle_initialize(self, params: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Handle initialize method"""
        if not isinstance(params, dict):
            raise InvalidParams("Parameters must be an object")
            
        required_fields = ["protocolVersion", "capabilities", "clientInfo"]
        for field in required_fields:
            if field not in params:
                raise InvalidParams(f"Missing required field: {field}")
        
        protocol_version = params["protocolVersion"]
        capabilities = params["capabilities"]
        client_info = params["clientInfo"]
        
        if not isinstance(capabilities, dict):
            raise InvalidParams("capabilities must be an object")
        if not isinstance(client_info, dict):
            raise InvalidParams("clientInfo must be an object")
        if "name" not in client_info:
            raise InvalidParams("clientInfo.name is required")
            
        session.initialize(protocol_version, capabilities, client_info)
        
        return {
            "protocolVersion": protocol_version,
            "capabilities": {},  # Server capabilities
            "serverInfo": {
                "name": "MCP Reference HTTP Server 2024-11-05",
                "version": "1.0.0"
            }
        }
    
    def handle_shutdown(self, params: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Handle shutdown method"""
        session.validate_initialized()
        session.initialized = False
        return {}
    
    def handle_list_directory(self, params: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Handle filesystem/listDirectory method"""
        session.validate_initialized()
        raise NotImplementedError("filesystem/listDirectory not implemented")
    
    def handle_read_file(self, params: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Handle filesystem/readFile method"""
        session.validate_initialized()
        raise NotImplementedError("filesystem/readFile not implemented")
    
    def handle_write_file(self, params: Dict[str, Any], session: Session) -> Dict[str, Any]:
        """Handle filesystem/writeFile method"""
        session.validate_initialized()
        raise NotImplementedError("filesystem/writeFile not implemented") 