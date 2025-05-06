#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP HTTP Server Launcher

This script launches either the 2024-11-05 or 2025-03-26 version of the MCP HTTP server.
"""

import os
import sys
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp-http-launcher")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Launch MCP HTTP Server")
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="Protocol version to use"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port to listen on"
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Automatically find available port"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--no-shutdown",
        action="store_true",
        help="Don't shut down server on client disconnect"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    if args.debug:
        os.environ["MCP_DEBUG"] = "1"
    os.environ["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    logger.info(f"Starting MCP HTTP server with protocol version {args.protocol_version}")
    
    try:
        if args.protocol_version == "2024-11-05":
            from server_2024_11_05 import run_server
        else:
            from server_2025_03_26 import run_server
            
        run_server(
            host=args.host,
            port=args.port,
            auto_port=args.auto_port
        )
    except ImportError as e:
        logger.error(f"Failed to import server module: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 