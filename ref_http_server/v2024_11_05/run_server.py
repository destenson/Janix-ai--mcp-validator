"""Entry point for running the MCP HTTP server version 2024-11-05."""

import argparse
import asyncio
import logging

from .server import MCPServer2024_11_05


async def main():
    """Run the server."""
    parser = argparse.ArgumentParser(description='Run MCP HTTP server v2024-11-05')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port to listen on')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    server = MCPServer2024_11_05()
    
    try:
        await server.start(args.host, args.port)
        await asyncio.Event().wait()  # Run forever
    except KeyboardInterrupt:
        await server.stop()
        
if __name__ == '__main__':
    asyncio.run(main()) 