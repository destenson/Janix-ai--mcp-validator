"""MCP HTTP server implementation for version 2025-03-26."""

import json
from typing import Optional, Dict, Any

from aiohttp import web

from ..common import MCPError, ErrorCodes, validate_request, format_response
from .session import Session


class MCPServer2025_03_26:
    """MCP HTTP server implementation for version 2025-03-26."""
    
    def __init__(self):
        """Initialize the server."""
        self.app = web.Application()
        self.app.router.add_post('/', self.handle_request)
        self.session: Optional[Session] = None
        
    async def handle_request(self, request: web.Request) -> web.Response:
        """Handle an incoming JSON-RPC request."""
        try:
            body = await request.text()
            jsonrpc_request = validate_request(body)
            
            method = jsonrpc_request['method']
            params = jsonrpc_request.get('params', {})
            request_id = jsonrpc_request.get('id')
            
            if method == 'initialize':
                if self.session is not None:
                    raise MCPError("Server already initialized", 
                                 code=ErrorCodes.INVALID_REQUEST)
                self.session = Session()
                result = await self.session.initialize(params)
            else:
                if self.session is None:
                    raise MCPError("Server not initialized",
                                 code=ErrorCodes.UNINITIALIZED)
                result = await self.session.handle_method(method, params)
                
            # If this is a notification (no id), don't send a response
            if request_id is None:
                return web.Response(status=204)
                
            response = format_response(result=result, request_id=request_id)
            
        except MCPError as e:
            # Only send error response if request had an id
            if 'request_id' not in locals() or request_id is None:
                return web.Response(status=204)
            response = format_response(error=e, request_id=request_id)
        except Exception as e:
            # Only send error response if request had an id
            if 'request_id' not in locals() or request_id is None:
                return web.Response(status=204)
            error = MCPError(str(e), code=ErrorCodes.INTERNAL_ERROR)
            response = format_response(error=error, request_id=request_id)
            
        return web.json_response(response)
        
    async def start(self, host: str = 'localhost', port: int = 8080):
        """Start the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"Server running at http://{host}:{port}")
        
    async def stop(self):
        """Stop the server."""
        if self.session:
            await self.session.shutdown()
        await self.app.shutdown()
        await self.app.cleanup() 