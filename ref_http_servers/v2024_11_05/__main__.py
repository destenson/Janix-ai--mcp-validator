"""Run script for MCP HTTP Server 2024-11-05"""

import asyncio
import argparse
from .server import MCPServer

def parse_args():
    parser = argparse.ArgumentParser(description="Run MCP HTTP Server 2024-11-05")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    return parser.parse_args()

async def main():
    args = parse_args()
    server = MCPServer(host=args.host, port=args.port)
    runner = await server.start()
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 