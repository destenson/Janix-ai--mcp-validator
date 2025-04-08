#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Run tests against a stdio MCP server.

This script runs all tests against a stdio MCP server.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from mcp_testing.utils.runner import run_tests
from mcp_testing.utils.reporter import results_to_markdown
from mcp_testing.tests.base_protocol.test_initialization import TEST_CASES as INIT_TEST_CASES
from mcp_testing.tests.features.test_tools import TEST_CASES as TOOLS_TEST_CASES
from mcp_testing.tests.features.test_async_tools import TEST_CASES as ASYNC_TOOLS_TEST_CASES


async def main():
    """Run the tests."""
    parser = argparse.ArgumentParser(description="Run tests against a stdio MCP server")
    parser.add_argument("--server-command", required=True, help="Command to start the server")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                        default="2024-11-05", help="Protocol version to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--output-file", help="File to write results to (in JSON format)")
    parser.add_argument("--markdown", action="store_true", help="Generate a Markdown compliance report")
    parser.add_argument("--markdown-file", help="Filename for the Markdown report (default: auto-generated)")
    args = parser.parse_args()
    
    # Set environment variables for the server
    env_vars = os.environ.copy()
    env_vars["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    # Collect all test cases
    all_tests = []
    all_tests.extend(INIT_TEST_CASES)
    all_tests.extend(TOOLS_TEST_CASES)
    
    # Include async tool tests only for 2025-03-26
    if args.protocol_version == "2025-03-26":
        all_tests.extend(ASYNC_TOOLS_TEST_CASES)
    
    # Run the tests
    results = await run_tests(
        tests=all_tests,
        protocol=args.protocol_version,
        transport="stdio",
        server_command=args.server_command,
        env_vars=env_vars,
        debug=args.debug
    )
    
    # Print results
    print(f"\nTest Results:")
    print(f"Total tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    # Write results to file if requested
    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(results, f, indent=2)
            print(f"\nResults written to {args.output_file}")
    
    # Generate Markdown report if requested
    if args.markdown or args.markdown_file:
        report_path = results_to_markdown(
            results=results,
            server_command=args.server_command,
            protocol_version=args.protocol_version,
            output_file=args.markdown_file
        )
        print(f"\nMarkdown compliance report generated: {report_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 