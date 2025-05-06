#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP Server Launcher

This script launches either the 2024-11-05 or 2025-03-26 version of the MCP server.
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
logger = logging.getLogger("mcp-launcher")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Launch MCP Server")
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="Protocol version to use"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    if args.debug:
        os.environ["MCP_DEBUG"] = "1"
    os.environ["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    logger.info(f"Starting MCP server with protocol version {args.protocol_version}")
    
    try:
        if args.protocol_version == "2024-11-05":
            from stdio_server_2024_11_05 import main as server_main
        else:
            from stdio_server_2025_03_26 import main as server_main
            
        server_main()
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