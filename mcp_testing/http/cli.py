#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP HTTP Testing Command Line Interface

A command-line interface for testing MCP HTTP server implementations.
"""

import argparse
import os.path
import subprocess
import sys

from .tester import MCPHttpTester
from .utils import wait_for_server

def run_http_tester(url, debug=False, protocol_version="2025-03-26"):
    """
    Run the HTTP tester against a server.
    
    Args:
        url: The server URL to test
        debug: Whether to enable debug output
        protocol_version: The protocol version to test
        
    Returns:
        True if all tests passed, False otherwise
    """
    tester = MCPHttpTester(url, debug)
    tester.protocol_version = protocol_version
    
    return tester.run_all_tests()

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Run MCP HTTP compliance tests against an MCP HTTP server."
    )
    parser.add_argument(
        "--server-url", 
        default="http://localhost:9000/mcp",
        help="URL of the MCP HTTP server to test"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26", "2025-06-18"],
        default="2025-06-18",
        help="MCP protocol version to test"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=3,
        help="Maximum number of connection retries"
    )
    parser.add_argument(
        "--retry-interval", 
        type=int, 
        default=2,
        help="Seconds to wait between connection retries"
    )
    
    args = parser.parse_args()
    
    # Check server connection first
    if not wait_for_server(
        args.server_url, 
        max_retries=args.max_retries, 
        retry_interval=args.retry_interval
    ):
        return 1
    
    # Run the tester
    success = run_http_tester(
        args.server_url, 
        args.debug,
        args.protocol_version
    )
    
    if success:
        print("All HTTP tests passed!")
        return 0
    else:
        print("Some HTTP tests failed", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 