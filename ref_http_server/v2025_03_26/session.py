"""Session management for MCP HTTP server version 2025-03-26."""

import asyncio
import os
import uuid
from typing import Dict, Any, Optional, List

from ..common import MCPError, ErrorCodes


class AsyncTask:
    """Represents an asynchronous task."""
    
    def __init__(self, task: asyncio.Task):
        """Initialize a new async task."""
        self.id = str(uuid.uuid4())
        self.task = task
        self.status = "running"
        self.result: Optional[Any] = None
        self.error: Optional[Dict[str, Any]] = None


class Session:
    """Manages a client session for the MCP server."""
    
    def __init__(self):
        """Initialize a new session."""
        self.initialized = False
        self.protocol_version: Optional[str] = None
        self.client_capabilities: Optional[Dict[str, Any]] = None
        self.client_info: Optional[Dict[str, str]] = None
        self.async_tasks: Dict[str, AsyncTask] = {}
        self.tools: List[Dict[str, Any]] = []
        self.supports_async = False
        self.supports_list_changed = False
        
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
        
        # Check client capabilities
        tools_caps = self.client_capabilities.get('tools', {})
        self.supports_async = tools_caps.get('async', False)
        self.supports_list_changed = tools_caps.get('listChanged', False)
        
        # Return server info
        return {
            'protocolVersion': '2025-03-26',
            'capabilities': {
                'tools': {
                    'async': True,
                    'listChanged': True
                },
                'resources': {
                    'memory': 1024,  # 1GB
                    'timeout': 300   # 5 minutes
                }
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
            
        if method.startswith('tools/'):
            return await self.handle_tools_method(method, params)
            
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
        if method == 'filesystem/listDirectory':
            return await self.list_directory(params)
        elif method == 'filesystem/readFile':
            return await self.read_file(params)
        elif method == 'filesystem/writeFile':
            return await self.write_file(params)
            
        raise MCPError(f"Method not found: {method}",
                      code=ErrorCodes.METHOD_NOT_FOUND)
                      
    async def handle_tools_method(self, method: str,
                                params: Dict[str, Any]) -> Any:
        """Handle tools-related methods.
        
        Args:
            method: The method name
            params: Method parameters
            
        Returns:
            Method result
            
        Raises:
            MCPError: If method handling fails
        """
        if method == 'tools/list':
            return {'tools': self.tools}
            
        if method == 'tools/call':
            if not isinstance(params.get('name'), str):
                raise MCPError("Missing or invalid tool name",
                             code=ErrorCodes.INVALID_PARAMS)
                             
            tool_name = params['name']
            tool = next((t for t in self.tools if t['name'] == tool_name), None)
            if not tool:
                raise MCPError(f"Tool not found: {tool_name}",
                             code=ErrorCodes.METHOD_NOT_FOUND)
                             
            arguments = params.get('arguments', {})
            is_async = params.get('async', False)
            
            if is_async and not self.supports_async:
                raise MCPError("Async execution not supported by client",
                             code=ErrorCodes.INVALID_REQUEST)
                             
            # Create and run the task
            task = asyncio.create_task(self.execute_tool(tool, arguments))
            
            if is_async:
                # Store and return task ID
                async_task = AsyncTask(task)
                self.async_tasks[async_task.id] = async_task
                return {'taskId': async_task.id}
            else:
                # Wait for completion and return result
                try:
                    return await task
                except Exception as e:
                    raise MCPError(str(e), code=ErrorCodes.INTERNAL_ERROR)
                    
        if method == 'tools/getTask':
            if not isinstance(params.get('taskId'), str):
                raise MCPError("Missing or invalid taskId",
                             code=ErrorCodes.INVALID_PARAMS)
                             
            task_id = params['taskId']
            if task_id not in self.async_tasks:
                raise MCPError(f"Task not found: {task_id}",
                             code=ErrorCodes.METHOD_NOT_FOUND)
                             
            async_task = self.async_tasks[task_id]
            
            if async_task.task.done():
                try:
                    result = async_task.task.result()
                    return {
                        'status': 'completed',
                        'result': result
                    }
                except Exception as e:
                    return {
                        'status': 'failed',
                        'error': {
                            'code': ErrorCodes.INTERNAL_ERROR,
                            'message': str(e)
                        }
                    }
            else:
                return {'status': 'running'}
                
        raise MCPError(f"Method not found: {method}",
                      code=ErrorCodes.METHOD_NOT_FOUND)
                      
    async def execute_tool(self, tool: Dict[str, Any],
                         arguments: Dict[str, Any]) -> Any:
        """Execute a tool.
        
        Args:
            tool: The tool definition
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPError: If tool execution fails
        """
        # This is where you would implement actual tool execution
        # For now, just return a dummy result
        return {'success': True}
                      
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
        # Cancel any pending async tasks
        for task in self.async_tasks.values():
            if not task.task.done():
                task.task.cancel()
                
        self.initialized = False
        return None 