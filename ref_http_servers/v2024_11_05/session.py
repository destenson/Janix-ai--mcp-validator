"""Session management for MCP HTTP server version 2024-11-05."""

import os
from typing import Dict, Any, Optional

from ..common import MCPError, ErrorCodes


class Session:
    """Manages a client session for the MCP server."""
    
    def __init__(self):
        """Initialize a new session."""
        self.initialized = False
        self.protocol_version: Optional[str] = None
        self.client_capabilities: Optional[Dict[str, Any]] = None
        self.client_info: Optional[Dict[str, str]] = None
        
    async def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the session with client information.
        
        Args:
            params: Initialization parameters from client
            
        Returns:
            Dict containing server information and capabilities
            
        Raises:
            MCPError: If initialization fails
        """
        if self.initialized:
            raise MCPError("Session already initialized", 
                         code=ErrorCodes.INVALID_REQUEST)
            
        # Validate required fields
        if not isinstance(params.get('protocolVersion'), str):
            raise MCPError("Missing or invalid protocolVersion",
                         code=ErrorCodes.INVALID_PARAMS)
            
        if not isinstance(params.get('capabilities'), dict):
            raise MCPError("Missing or invalid capabilities",
                         code=ErrorCodes.INVALID_PARAMS)
            
        if not isinstance(params.get('clientInfo'), dict):
            raise MCPError("Missing or invalid clientInfo",
                         code=ErrorCodes.INVALID_PARAMS)
            
        client_info = params['clientInfo']
        if not isinstance(client_info.get('name'), str):
            raise MCPError("Missing or invalid clientInfo.name",
                         code=ErrorCodes.INVALID_PARAMS)
            
        # Store session info
        self.protocol_version = params['protocolVersion']
        self.client_capabilities = params['capabilities']
        self.client_info = client_info
        self.initialized = True
        
        # Return server info
        return {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'filesystem': True
            },
            'serverInfo': {
                'name': 'mcp-reference-server',
                'version': '0.1.0'
            }
        }
        
    async def handle_method(self, method: str, params: Dict[str, Any]) -> Any:
        """Handle a method call.
        
        Args:
            method: The method name
            params: Method parameters
            
        Returns:
            Method result
            
        Raises:
            MCPError: If method handling fails
        """
        if method == 'shutdown':
            return await self.shutdown()
            
        if method.startswith('filesystem/'):
            return await self.handle_filesystem_method(method, params)
            
        raise MCPError(f"Method not found: {method}",
                      code=ErrorCodes.METHOD_NOT_FOUND)
                      
    async def handle_filesystem_method(self, method: str, 
                                     params: Dict[str, Any]) -> Any:
        """Handle filesystem-related methods.
        
        Args:
            method: The method name
            params: Method parameters
            
        Returns:
            Method result
            
        Raises:
            MCPError: If method handling fails
        """
        if not self.client_capabilities.get('supports', {}).get('filesystem'):
            raise MCPError("Filesystem operations not supported by client",
                         code=ErrorCodes.INVALID_REQUEST)
                         
        if method == 'filesystem/listDirectory':
            return await self.list_directory(params)
        elif method == 'filesystem/readFile':
            return await self.read_file(params)
        elif method == 'filesystem/writeFile':
            return await self.write_file(params)
            
        raise MCPError(f"Method not found: {method}",
                      code=ErrorCodes.METHOD_NOT_FOUND)
                      
    async def list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            params: Method parameters
            
        Returns:
            Dict containing directory entries
            
        Raises:
            MCPError: If operation fails
        """
        if not isinstance(params.get('path'), str):
            raise MCPError("Missing or invalid path",
                         code=ErrorCodes.INVALID_PARAMS)
                         
        try:
            entries = []
            with os.scandir(params['path']) as it:
                for entry in it:
                    entry_info = {
                        'name': entry.name,
                        'type': 'directory' if entry.is_dir() else 'file'
                    }
                    if entry.is_file():
                        entry_info['size'] = entry.stat().st_size
                    entries.append(entry_info)
            return {'entries': entries}
        except Exception as e:
            raise MCPError(str(e), code=ErrorCodes.INTERNAL_ERROR)
            
    async def read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read contents of a file.
        
        Args:
            params: Method parameters
            
        Returns:
            Dict containing file contents
            
        Raises:
            MCPError: If operation fails
        """
        if not isinstance(params.get('path'), str):
            raise MCPError("Missing or invalid path",
                         code=ErrorCodes.INVALID_PARAMS)
                         
        try:
            with open(params['path'], 'r') as f:
                content = f.read()
            return {'content': [{'type': 'text', 'text': content}]}
        except Exception as e:
            raise MCPError(str(e), code=ErrorCodes.INTERNAL_ERROR)
            
    async def write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write contents to a file.
        
        Args:
            params: Method parameters
            
        Returns:
            Dict containing bytes written
            
        Raises:
            MCPError: If operation fails
        """
        if not isinstance(params.get('path'), str):
            raise MCPError("Missing or invalid path",
                         code=ErrorCodes.INVALID_PARAMS)
                         
        if not isinstance(params.get('content'), str):
            raise MCPError("Missing or invalid content",
                         code=ErrorCodes.INVALID_PARAMS)
                         
        try:
            with open(params['path'], 'w') as f:
                bytes_written = f.write(params['content'])
            return {'bytesWritten': bytes_written}
        except Exception as e:
            raise MCPError(str(e), code=ErrorCodes.INTERNAL_ERROR)
            
    async def shutdown(self) -> None:
        """Shutdown the session."""
        self.initialized = False
        return None 