#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Run tests against an HTTP MCP server.

This script provides a command-line interface for testing an MCP HTTP server.
"""

import argparse
import os
import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mcp_testing.http.tester import MCPHttpTester
from mcp_testing.http.utils import wait_for_server

def main():
    """Run compliance tests against an HTTP MCP server."""
    try:
        parser = argparse.ArgumentParser(description="Run tests against an HTTP MCP server")
        parser.add_argument(
            "--server-url", 
            default="http://localhost:9000/mcp",
            help="URL of the MCP HTTP server (default: http://localhost:9000/mcp)"
        )
        parser.add_argument(
            "--protocol-version", 
            choices=["2024-11-05", "2025-03-26"], 
            default="2025-03-26", 
            help="Protocol version to use (default: 2025-03-26)"
        )
        parser.add_argument(
            "--debug", 
            action="store_true", 
            help="Enable debug logging"
        )
        parser.add_argument(
            "--output-dir", 
            help="Directory to write test results"
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
        
        # Create output directory if needed
        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)
        
        # Check server connection first
        if not wait_for_server(
            args.server_url, 
            max_retries=args.max_retries, 
            retry_interval=args.retry_interval
        ):
            return 1
        
        # Run the HTTP tests
        tester = MCPHttpTester(args.server_url, args.debug)
        tester.protocol_version = args.protocol_version
        
        success = tester.run_all_tests()
        
        # Generate report if needed
        if args.output_dir:
            report_path = os.path.join(args.output_dir, f"http_test_report_{args.protocol_version}.md")
            
            with open(report_path, "w") as f:
                f.write(f"# MCP HTTP Compliance Test Report\n\n")
                f.write(f"- Server: {args.server_url}\n")
                f.write(f"- Protocol Version: {args.protocol_version}\n")
                f.write(f"- Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"## Test Results\n\n")
                f.write(f"All tests {'PASSED' if success else 'FAILED'}\n\n")
                
                f.write(f"## Notes\n\n")
                f.write(f"This report was generated using the MCP HTTP testing framework.\n")
                f.write(f"For more detailed test results, run with the --debug flag.\n")
            
            print(f"Test report written to {report_path}")
        
        return 0 if success else 1
    except Exception as e:
        print("Error during HTTP test:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 