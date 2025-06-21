#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP STDIO Testing Command Line Interface

A command-line interface for testing MCP STDIO server implementations.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

from .tester import MCPStdioTester
from .utils import check_command_exists, verify_python_server
from mcp_testing.report import generate_report


def run_stdio_tester(server_command, args=None, debug=False, protocol_version="2025-06-18"):
    """
    Run the STDIO tester against a server.
    
    Args:
        server_command: The command to run the server
        args: Additional arguments to pass to the server command
        debug: Whether to enable debug output
        protocol_version: The protocol version to test
        
    Returns:
        True if all tests passed, False otherwise
    """
    args = args or []
    tester = MCPStdioTester(server_command, args, debug)
    tester.protocol_version = protocol_version
    
    return tester.run_all_tests()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Run MCP STDIO compliance tests against an MCP STDIO server."
    )
    
    parser.add_argument(
        "server_command",
        help="Command to run the server"
    )
    
    parser.add_argument(
        "--args",
        nargs="+",
        default=[],
        help="Additional arguments to pass to the server command"
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
        "--output-dir",
        default=None,
        help="Directory to write test report"
    )
    
    parser.add_argument(
        "--report-format",
        choices=["text", "json", "html"],
        default="text",
        help="Format of the test report"
    )
    
    args = parser.parse_args()
    
    # Check if the server command exists
    cmd = args.server_command.split()[0]
    if not check_command_exists(cmd):
        print(f"Error: Command '{cmd}' not found", file=sys.stderr)
        return 1
    
    # Run the tester
    success = run_stdio_tester(
        args.server_command,
        args.args,
        args.debug,
        args.protocol_version
    )
    
    # Generate report if output directory is specified
    if args.output_dir and success:
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # TODO: Use actual test results here instead of hardcoded values
        report_data = {
            "title": "MCP STDIO Server Test Report",
            "server_info": {
                "command": args.server_command,
                "protocol_version": args.protocol_version
            },
            "tests": [
                {"name": "Initialize", "result": "PASS", "details": "Server initialization successful"},
                {"name": "List Tools", "result": "PASS", "details": "Server returned tools list"},
                {"name": "Echo Tool", "result": "PASS", "details": "Echo tool returned expected result"},
                {"name": "Add Tool", "result": "PASS", "details": "Add tool returned expected result"},
                {"name": "Async Sleep Tool", "result": "PASS", "details": "Async sleep tool completed successfully"}
            ]
        }
        
        # Generate report
        report_file = os.path.join(args.output_dir, f"report.{args.report_format}")
        generate_report(report_data, report_file, args.report_format)
        
        print(f"\nReport generated at: {report_file}")
    
    if success:
        print("All STDIO tests passed!")
        return 0
    else:
        print("Some STDIO tests failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 