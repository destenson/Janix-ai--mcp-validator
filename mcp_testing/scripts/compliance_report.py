#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate a compliance report for an MCP server.

This script runs tests against any MCP server and generates a detailed compliance report.
It adapts to the server's capabilities rather than having fixed expectations.

Environment Variables:
    MCP_SKIP_SHUTDOWN:     Set to 'true' to skip calling the shutdown method
    MCP_PROTOCOL_VERSION:  Set the protocol version to test against
    MCP_REQUIRED_TOOLS:    Comma-separated list of required tools
    
    Server-specific environment variables can be set in two ways:
    1. Set the variable directly, e.g., BRAVE_API_KEY=your_key
    2. Use MCP_DEFAULT_* prefix for default values, e.g., MCP_DEFAULT_BRAVE_API_KEY=default_key
    
    The script will warn about missing required environment variables for specific servers.

Server Configurations:
    The system uses configuration files in the 'server_configs' directory to determine:
    - Required environment variables for each server
    - Tests that should be skipped
    - Required tools for the server
    - Recommended protocol version
    
    To support a new server, add a JSON configuration file to the 'server_configs' directory.
    See the README.md file in that directory for details on the configuration format.
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
from mcp_testing.tests.features.dynamic_tool_tester import TEST_CASES as DYNAMIC_TOOL_TEST_CASES
from mcp_testing.tests.features.dynamic_async_tools import TEST_CASES as DYNAMIC_ASYNC_TEST_CASES
from mcp_testing.tests.specification_coverage import TEST_CASES as SPEC_COVERAGE_TEST_CASES

# Import server compatibility utilities
try:
    from mcp_testing.utils.server_compatibility import (
        is_shutdown_skipped,
        prepare_environment_for_server,
        get_server_specific_test_config,
        get_recommended_protocol_version
    )
except ImportError:
    # Fallback implementations if module doesn't exist yet
    def is_shutdown_skipped() -> bool:
        """Check if shutdown should be skipped based on environment variable."""
        skip_shutdown = os.environ.get("MCP_SKIP_SHUTDOWN", "").lower()
        return skip_shutdown in ("true", "1", "yes")
    
    def prepare_environment_for_server(server_command: str) -> dict:
        """Prepare environment variables for a specific server."""
        env_vars = os.environ.copy()
        if "server-brave-search" in server_command:
            env_vars["MCP_SKIP_SHUTDOWN"] = "true"
        return env_vars
    
    def get_server_specific_test_config(server_command: str) -> dict:
        """Get server-specific test configuration."""
        config = {}
        if "server-brave-search" in server_command:
            config["skip_tests"] = ["test_shutdown", "test_exit_after_shutdown"]
            config["required_tools"] = ["brave_web_search", "brave_local_search"]
        return config
    
    def get_recommended_protocol_version(server_command: str) -> str:
        """Get the recommended protocol version for a specific server."""
        if "server-brave-search" in server_command:
            return "2024-11-05"
        return None

async def main():
    """Run the compliance tests and generate a report."""
    parser = argparse.ArgumentParser(description="Generate an MCP server compliance report")
    
    # Server configuration
    parser.add_argument("--server-command", required=True, help="Command to start the server")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                        default="2025-03-26", help="Protocol version to use")
    parser.add_argument("--server-config", help="JSON file with server-specific test configuration")
    parser.add_argument("--args", help="Additional arguments to pass to the server command")
    
    # Output options
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    parser.add_argument("--report-prefix", default="compliance_report", help="Prefix for report filenames")
    parser.add_argument("--json", action="store_true", help="Generate a JSON report")
    
    # Testing options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--skip-async", action="store_true", help="Skip async tool tests (for 2025-03-26)")
    parser.add_argument("--skip-shutdown", action="store_true", help="Skip shutdown method (some servers may not implement this)")
    parser.add_argument("--required-tools", help="Comma-separated list of tools that must be available")
    parser.add_argument("--skip-tests", help="Comma-separated list of test names to skip")
    parser.add_argument("--dynamic-only", action="store_true", help="Only run dynamic tests that adapt to the server's capabilities")
    parser.add_argument("--test-mode", choices=["all", "core", "tools", "async", "spec"], default="all", 
                        help="Testing mode: 'all' runs all tests, 'core' runs only initialization tests, 'tools' runs core and tools tests, 'async' runs async tests, 'spec' runs specification coverage tests")
    parser.add_argument("--spec-coverage-only", action="store_true", help="Only run specification coverage tests")
    parser.add_argument("--auto-detect", action="store_true", help="Auto-detect server settings based on server command")
    
    args = parser.parse_args()
    
    # Combine server command with any additional arguments
    full_server_command = args.server_command
    if args.args:
        full_server_command = f"{args.server_command} {args.args}"
    
    # Auto-detect protocol version if requested
    if args.auto_detect:
        recommended_version = get_recommended_protocol_version(full_server_command)
        if recommended_version:
            if args.debug:
                print(f"Auto-detected protocol version {recommended_version} for {args.server_command}")
            args.protocol_version = recommended_version
    
    # Set environment variables for the server
    if args.debug:
        print(f"Preparing environment for server: {full_server_command}")
    
    # Get environment variables with server-specific settings
    env_vars = prepare_environment_for_server(full_server_command)
    
    # Set protocol version in environment
    env_vars["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    # Set skip_shutdown flag in environment if specified via command line
    if args.skip_shutdown:
        env_vars["MCP_SKIP_SHUTDOWN"] = "true"
        if args.debug:
            print("Shutdown will be skipped (--skip-shutdown flag)")
    elif is_shutdown_skipped():
        # Environment variable is already set
        if args.debug:
            print("Shutdown will be skipped (MCP_SKIP_SHUTDOWN env var)")
    
    # Parse server configuration if provided
    server_config = {}
    if args.server_config:
        try:
            with open(args.server_config, 'r') as f:
                server_config = json.load(f)
                print(f"Loaded server configuration from {args.server_config}")
        except Exception as e:
            print(f"Error loading server configuration: {str(e)}")
    
    # If auto-detect is enabled, get server-specific config
    if args.auto_detect:
        server_specific_config = get_server_specific_test_config(full_server_command)
        server_config.update(server_specific_config)
        if args.debug and server_specific_config:
            print(f"Auto-detected configuration for {args.server_command}")
            for key, value in server_specific_config.items():
                print(f"  {key}: {value}")
    
    # Parse required tools
    required_tools = []
    if args.required_tools:
        required_tools = [t.strip() for t in args.required_tools.split(',')]
    elif server_config.get("required_tools"):
        required_tools = server_config.get("required_tools")
    
    # Set required tools in environment
    if required_tools:
        env_vars["MCP_REQUIRED_TOOLS"] = ",".join(required_tools)
        print(f"Required tools: {', '.join(required_tools)}")
    
    # Parse tests to skip
    skip_tests = []
    if args.skip_tests:
        skip_tests = [t.strip() for t in args.skip_tests.split(',')]
    elif server_config.get("skip_tests"):
        skip_tests = server_config.get("skip_tests")
    
    if skip_tests:
        print(f"Skipping tests: {', '.join(skip_tests)}")
    
    # Ensure output directory exists
    output_dir = os.path.join(parent_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for report filenames
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Collect test cases based on test mode and flags
    all_tests = []
    
    # If spec-coverage-only is set, only run specification coverage tests
    if args.spec_coverage_only:
        print("Running only specification coverage tests")
        spec_tests = [(func, name) for func, name in SPEC_COVERAGE_TEST_CASES if name not in skip_tests]
        all_tests.extend(spec_tests)
    else:
        # Always add initialization tests regardless of mode
        init_tests = [(func, name) for func, name in INIT_TEST_CASES if name not in skip_tests]
        all_tests.extend(init_tests)
    
        # Add specification coverage tests if mode is all or spec
        if args.test_mode in ["all", "spec"]:
            spec_tests = [(func, name) for func, name in SPEC_COVERAGE_TEST_CASES if name not in skip_tests]
            all_tests.extend(spec_tests)
        
        if args.dynamic_only:
            # Only use dynamic tests when in dynamic-only mode
            print("Running in dynamic-only mode - tests will adapt to the server's capabilities")
            
            # Add dynamic tool tests
            if args.test_mode in ["all", "tools"]:
                all_tests.extend([(func, name) for func, name in DYNAMIC_TOOL_TEST_CASES if name not in skip_tests])
            
            # Include dynamic async tests for 2025-03-26 if not skipped
            if args.protocol_version == "2025-03-26" and not args.skip_async and args.test_mode in ["all", "async"]:
                all_tests.extend([(func, name) for func, name in DYNAMIC_ASYNC_TEST_CASES if name not in skip_tests])
        else:
            # Use a mix of traditional and dynamic tests
            if args.test_mode in ["all", "tools"]:
                # Add tools tests (filtering out skipped ones)
                all_tests.extend([(func, name) for func, name in TOOLS_TEST_CASES if name not in skip_tests])
                
                # Add dynamic tool tests
                all_tests.extend([(func, name) for func, name in DYNAMIC_TOOL_TEST_CASES if name not in skip_tests])
            
            # Include async tool tests for 2025-03-26 if not skipped
            if args.protocol_version == "2025-03-26" and not args.skip_async and args.test_mode in ["all", "async"]:
                all_tests.extend([(func, name) for func, name in ASYNC_TOOLS_TEST_CASES if name not in skip_tests])
                all_tests.extend([(func, name) for func, name in DYNAMIC_ASYNC_TEST_CASES if name not in skip_tests])
    
    print(f"Running compliance tests for protocol {args.protocol_version}...")
    print(f"Server command: {full_server_command}")
    print(f"Test mode: {args.test_mode}")
    print(f"Total tests to run: {len(all_tests)}")
    
    # Run the tests
    results = await run_tests(
        tests=all_tests,
        protocol=args.protocol_version,
        transport="stdio",
        server_command=full_server_command,
        env_vars=env_vars,
        debug=args.debug
    )
    
    # Print results summary
    print(f"\nCompliance Test Results:")
    print(f"Total tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    if results.get("skipped", 0) > 0:
        print(f"Skipped: {results['skipped']}")
    
    # Generate compliance score
    compliance_pct = round(results['passed'] / results['total'] * 100, 1)
    
    if compliance_pct == 100:
        print(f"Compliance Status: ✅ Fully Compliant (100%)")
    elif compliance_pct >= 80:
        print(f"Compliance Status: ⚠️ Mostly Compliant ({compliance_pct}%)")
    else:
        print(f"Compliance Status: ❌ Non-Compliant ({compliance_pct}%)")
    
    # Generate the Markdown report
    markdown_filename = f"{args.report_prefix}_{args.protocol_version}_{timestamp}.md"
    markdown_path = os.path.join(output_dir, markdown_filename)
    
    report_path = results_to_markdown(
        results=results,
        server_command=full_server_command,
        protocol_version=args.protocol_version,
        output_file=markdown_filename,
        server_config=server_config
    )
    print(f"\nMarkdown compliance report generated: {report_path}")
    
    # Generate JSON report if requested
    if args.json:
        json_filename = f"{args.report_prefix}_{args.protocol_version}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Add additional metadata to the results
        results["metadata"] = {
            "server_command": full_server_command,
            "protocol_version": args.protocol_version,
            "timestamp": timestamp,
            "compliance_score": compliance_pct,
            "server_config": server_config,
            "dynamic_only": args.dynamic_only,
            "test_mode": args.test_mode,
            "skip_shutdown": is_shutdown_skipped()
        }
        
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"JSON report generated: {json_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 