#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Generic MCP Server Test Script

This script provides a high-level interface for testing any MCP server,
automatically detecting server-specific configuration needs.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = Path(__file__).resolve().parent
sys.path.append(str(parent_dir))

# Import utility modules
try:
    from mcp_testing.utils.server_compatibility import (
        prepare_environment_for_server,
        get_server_specific_test_config,
        get_recommended_protocol_version
    )
    from mcp_testing.utils.runner import run_tests
    from mcp_testing.utils.reporter import results_to_markdown
    from mcp_testing.tests.base_protocol.test_initialization import TEST_CASES as INIT_TEST_CASES
    from mcp_testing.tests.features.dynamic_tool_tester import TEST_CASES as DYNAMIC_TOOL_TEST_CASES
except ImportError:
    print("Error: Unable to import required modules from mcp_testing package")
    print("Make sure you're running this script from the mcp-protocol-validator directory")
    sys.exit(1)


async def main():
    """Run tests for the specified server command and generate a report."""
    parser = argparse.ArgumentParser(description="Test an MCP server with automatic configuration")
    
    # Server configuration
    parser.add_argument("--server-command", required=True, help="Command to start the server")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                        help="Protocol version to use (auto-detected if not specified)")
    parser.add_argument("--args", help="Additional arguments to pass to the server command")
    
    # Output options
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    
    # Testing options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--basic-only", action="store_true", help="Only run basic initialization and tool tests")
    
    args = parser.parse_args()
    
    # Combine server command with any additional arguments
    full_server_command = args.server_command
    if args.args:
        full_server_command = f"{args.server_command} {args.args}"
    
    # Get recommended protocol version if not specified
    protocol_version = args.protocol_version
    if not protocol_version:
        recommended_version = get_recommended_protocol_version(full_server_command)
        protocol_version = recommended_version or "2024-11-05"  # Default to 2024-11-05 if not detected
    
    # Prepare environment variables
    env_vars = prepare_environment_for_server(full_server_command)
    env_vars["MCP_PROTOCOL_VERSION"] = protocol_version
    
    # Get server-specific test configuration
    server_config = get_server_specific_test_config(full_server_command)
    
    # Extract skip tests from configuration
    skip_tests = server_config.get("skip_tests", [])
    
    # Ensure output directory exists
    output_dir = os.path.join(parent_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Collect test cases
    all_tests = []
    
    # Add initialization tests
    init_tests = [(func, name) for func, name in INIT_TEST_CASES if name not in skip_tests]
    all_tests.extend(init_tests)
    
    # Add dynamic tool tests
    if not args.basic_only:
        dynamic_tests = [(func, name) for func, name in DYNAMIC_TOOL_TEST_CASES if name not in skip_tests]
        all_tests.extend(dynamic_tests)
    
    print(f"Running tests for {full_server_command}")
    print(f"Protocol version: {protocol_version}")
    if "MCP_SKIP_SHUTDOWN" in env_vars:
        print(f"Note: Shutdown is skipped for this server")
    print(f"Total tests to run: {len(all_tests)}")
    
    # Run the tests
    results = await run_tests(
        tests=all_tests,
        protocol=protocol_version,
        transport="stdio",
        server_command=full_server_command,
        env_vars=env_vars,
        debug=args.debug
    )
    
    # Print results summary
    print(f"\nTest Results:")
    print(f"Total tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    # Generate the report
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report_name = f"server_test_{timestamp}.md"
    if "server-brave-search" in full_server_command:
        report_name = f"brave_search_test_{timestamp}.md"
    
    report_path = results_to_markdown(
        results=results,
        server_command=full_server_command,
        protocol_version=protocol_version,
        output_file=report_name,
        server_config=server_config
    )
    print(f"\nReport generated: {report_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 