#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Run script for the MCP HTTP Server V2.

This script directly imports and runs the V2 server without package issues.
"""

import sys
import os

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, parent_dir)

# Import the server components
from ref_http_server.server import run_server, DEFAULT_HOST, DEFAULT_PORT
import argparse

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MCP HTTP Server V2')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                        help=f'Host to listen on (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--auto-port', action='store_true',
                        help='Automatically find an available port if the specified port is in use')
    parser.add_argument('--log-file', type=str,
                        help='Log file to write to (in addition to stdout)')
    parser.add_argument('--no-shutdown', action='store_true',
                        help='Ignore shutdown requests (for testing with compliance tests)')
    
    args = parser.parse_args()
    
    # Run the server
    run_server(args.host, args.port, args.debug, args.auto_port, args.log_file, args.no_shutdown)


if __name__ == "__main__":
    main() 