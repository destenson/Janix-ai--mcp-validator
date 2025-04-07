#!/usr/bin/env python3
"""
Generate a compliance report for an MCP server.

This script runs tests against any MCP server and generates a detailed compliance report.
It adapts to the server's capabilities rather than having fixed expectations.
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
    parser.add_argument("--test-mode", choices=["all", "core", "tools", "async"], default="all", 
                        help="Testing mode: 'all' runs all tests, 'core' runs only initialization tests, 'tools' runs core and tools tests, 'async' runs async tests")
    
    args = parser.parse_args()
    
    # Combine server command with any additional arguments
    full_server_command = args.server_command
    if args.args:
        full_server_command = f"{args.server_command} {args.args}"
    
    # Set environment variables for the server
    env_vars = os.environ.copy()
    env_vars["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    # Add skip_shutdown flag to environment if specified
    if args.skip_shutdown:
        env_vars["MCP_SKIP_SHUTDOWN"] = "true"
    
    # Parse server configuration if provided
    server_config = {}
    if args.server_config:
        try:
            with open(args.server_config, 'r') as f:
                server_config = json.load(f)
                print(f"Loaded server configuration from {args.server_config}")
        except Exception as e:
            print(f"Error loading server configuration: {str(e)}")
    
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
    
    # Collect test cases based on test mode and dynamic flag
    all_tests = []
    
    # Always add initialization tests regardless of mode
    init_tests = [(func, name) for func, name in INIT_TEST_CASES if name not in skip_tests]
    all_tests.extend(init_tests)
    
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
            "test_mode": args.test_mode
        }
        
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"JSON report generated: {json_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 