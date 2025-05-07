#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Session Testing Script

A script for validating session handling in MCP HTTP servers.
"""

import argparse
import os
import sys
import subprocess
import time

# Add the parent directory to the path to allow importing from mcp_testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp_testing.http.session_validator import MCPSessionValidator
from mcp_testing.http.utils import wait_for_server, check_server

def main():
    parser = argparse.ArgumentParser(
        description="Validate session handling in an MCP HTTP server"
    )
    parser.add_argument(
        "--server-url", 
        default="http://localhost:8888/mcp",
        help="URL of the MCP HTTP server to test"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="MCP protocol version to test"
    )
    parser.add_argument(
        "--restart-server",
        action="store_true",
        help="Restart the server before running tests"
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=8888,
        help="Port to use when starting a new server"
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
    
    # Restart the server if requested
    if args.restart_server:
        print("Restarting the MCP HTTP server...")
        try:
            # Kill any existing server processes
            subprocess.run(["pkill", "-9", "-f", "minimal_http_server"], 
                          check=False, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            # Wait a moment for ports to be freed
            time.sleep(2)
            
            # Start a new server
            server_cmd = [
                "python",
                "minimal_http_server/minimal_http_server.py",
                "--port", str(args.server_port),
                "--debug"
            ]
            
            print(f"Starting server with: {' '.join(server_cmd)}")
            server_process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if the server started successfully
            if server_process.poll() is not None:
                print("ERROR: Failed to start the server")
                stdout, stderr = server_process.communicate()
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return 1
            
            print("Server started successfully")
            
        except Exception as e:
            print(f"ERROR: Failed to restart the server: {str(e)}")
            return 1
    
    # Check server connection
    if not wait_for_server(
        args.server_url, 
        max_retries=args.max_retries, 
        retry_interval=args.retry_interval
    ):
        print(f"ERROR: Could not connect to server at {args.server_url}")
        return 1
    
    # Run the validator
    validator = MCPSessionValidator(args.server_url, args.debug)
    validator.protocol_version = args.protocol_version
    success = validator.run_all_tests()
    
    # Generate summary
    print("\n=== Session Validation Results ===")
    if success:
        print("✅ SERVER PASSED Session Validation Test")
        print(f"Server: {args.server_url}")
        print(f"Protocol version: {args.protocol_version}")
        print("\nThis server correctly implements session management with the Mcp-Session-Id header.")
        print("It is safe to use this server for MCP protocol compliance testing.")
    else:
        print("❌ SERVER FAILED Session Validation Test")
        print(f"Server: {args.server_url}")
        print(f"Protocol version: {args.protocol_version}")
        print("\nThis server has issues with session management.")
        print("Please check the server implementation and ensure it correctly handles the Mcp-Session-Id header.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 