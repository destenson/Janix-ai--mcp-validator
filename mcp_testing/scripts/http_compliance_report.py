#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
HTTP Compliance Report Generator

This script runs the full compliance test suite against an HTTP-based MCP server.
It uses the same comprehensive test cases as the STDIO compliance report but adapts
them to use HTTP transport.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from mcp_testing.utils.runner import run_tests
from mcp_testing.utils.reporter import results_to_markdown, extract_server_name, generate_markdown_report
from mcp_testing.tests.base_protocol.test_initialization import TEST_CASES as INIT_TEST_CASES
from mcp_testing.tests.features.test_tools import TEST_CASES as TOOLS_TEST_CASES
from mcp_testing.tests.features.test_async_tools import TEST_CASES as ASYNC_TOOLS_TEST_CASES
from mcp_testing.tests.features.dynamic_tool_tester import TEST_CASES as DYNAMIC_TOOL_TEST_CASES
from mcp_testing.tests.features.dynamic_async_tools import TEST_CASES as DYNAMIC_ASYNC_TEST_CASES
from mcp_testing.tests.specification_coverage import TEST_CASES as SPEC_COVERAGE_TEST_CASES
from mcp_testing.transports.http import HttpTransportAdapter

def log_with_timestamp(message):
    """Log a message with a timestamp prefix."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

async def main():
    """Run the compliance tests using HTTP transport and generate a report."""
    parser = argparse.ArgumentParser(description="Generate an MCP HTTP server compliance report")
    
    # Server configuration
    parser.add_argument("--server-url", required=True, help="URL of the HTTP server")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                      default="2025-03-26", help="Protocol version to use")
    
    # Output options
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    parser.add_argument("--report-prefix", default="cr", help="Prefix for report filenames (default: 'cr')")
    parser.add_argument("--json", action="store_true", help="Generate a JSON report")
    
    # Debug and control options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--skip-async", action="store_true", help="Skip async tests")
    parser.add_argument("--skip-tests", help="Comma-separated list of test names to skip")
    parser.add_argument("--dynamic-only", action="store_true", help="Only run dynamic tools tests")
    parser.add_argument("--test-mode", choices=["all", "core", "tools", "async", "spec"], default="all", 
                      help="Test mode: all, core, tools, async, or spec")
    parser.add_argument("--spec-coverage-only", action="store_true", 
                      help="Only run tests for spec coverage")
    parser.add_argument("--test-timeout", type=int, default=30,
                      help="Timeout in seconds for individual tests")
    parser.add_argument("--tools-timeout", type=int, default=30,
                      help="Timeout in seconds for tools tests")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Parse tests to skip
    skip_tests = []
    if args.skip_tests:
        skip_tests = [t.strip() for t in args.skip_tests.split(',')]
    
    if skip_tests:
        log_with_timestamp(f"Skipping tests: {', '.join(skip_tests)}")
    
    # Ensure output directory exists
    output_dir = os.path.join(parent_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for report filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Collect test cases based on test mode and flags
    tests = []
    
    if args.dynamic_only:
        log_with_timestamp("Running in dynamic-only mode - tests will adapt to the server's capabilities")
        tests.extend(INIT_TEST_CASES)  # Always include initialization tests
        tests.extend(DYNAMIC_TOOL_TEST_CASES)
        
        if args.protocol_version == "2025-03-26" and not args.skip_async:
            tests.extend(DYNAMIC_ASYNC_TEST_CASES)
    
    elif args.spec_coverage_only:
        log_with_timestamp("Running specification coverage tests only")
        tests.extend(SPEC_COVERAGE_TEST_CASES)
    
    else:
        # Normal mode - collect tests based on test_mode
        if args.test_mode in ["all", "core"]:
            tests.extend(INIT_TEST_CASES)
            
        if args.test_mode in ["all", "tools"]:
            tests.extend(TOOLS_TEST_CASES)
            
        if args.test_mode in ["all", "async"] and args.protocol_version == "2025-03-26" and not args.skip_async:
            tests.extend(ASYNC_TOOLS_TEST_CASES)
            
        if args.test_mode in ["all", "spec"]:
            tests.extend(SPEC_COVERAGE_TEST_CASES)
    
    # Filter out tests to skip
    if skip_tests:
        original_count = len(tests)
        tests = [(func, name) for func, name in tests if name not in skip_tests]
        skipped_count = original_count - len(tests)
        if skipped_count > 0:
            log_with_timestamp(f"Skipped {skipped_count} tests based on configuration")
    
    log_with_timestamp(f"Running compliance tests for protocol {args.protocol_version}...")
    log_with_timestamp(f"Server URL: {args.server_url}")
    log_with_timestamp(f"Test mode: {args.test_mode}")
    log_with_timestamp(f"Total tests to run: {len(tests)}")
    
    # Create HTTP transport adapter
    transport = HttpTransportAdapter(
        server_url=args.server_url,
        debug=args.debug,
        timeout=args.test_timeout
    )
    
    # Run the tests
    start_time = time.time()
    
    # Set timeouts based on arguments
    test_timeout = args.test_timeout
    tools_timeout = args.tools_timeout
    
    # Group tests by type and run with appropriate timeouts
    tool_tests = [(func, name) for func, name in tests if name.startswith("test_tool_") or name.startswith("test_tools_")]
    non_tool_tests = [(func, name) for func, name in tests if not (name.startswith("test_tool_") or name.startswith("test_tools_"))]
    
    results = {
        "results": [],
        "total": len(tests),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "timeouts": 0
    }
    
    # Run non-tool tests first with standard timeout
    if non_tool_tests:
        log_with_timestamp(f"Running {len(non_tool_tests)} non-tool tests with {test_timeout}s timeout")
        non_tool_results = await run_tests(
            non_tool_tests, 
            protocol=args.protocol_version, 
            transport="http",  # Use HTTP transport
            server_command=args.server_url,  # Pass server URL as the command
            env_vars={},  # No environment variables needed for HTTP
            debug=args.debug,
            timeout=test_timeout
        )
        results["results"].extend(non_tool_results["results"])
        results["passed"] += non_tool_results["passed"]
        results["failed"] += non_tool_results["failed"]
        results["skipped"] += non_tool_results.get("skipped", 0)
        results["timeouts"] += non_tool_results.get("timeouts", 0)
    
    # Run tool tests with extended timeout
    if tool_tests:
        log_with_timestamp(f"Running {len(tool_tests)} tool tests with {tools_timeout}s timeout")
        tool_results = await run_tests(
            tool_tests, 
            protocol=args.protocol_version, 
            transport="http",  # Use HTTP transport
            server_command=args.server_url,  # Pass server URL as the command
            env_vars={},  # No environment variables needed for HTTP
            debug=args.debug,
            timeout=tools_timeout
        )
        results["results"].extend(tool_results["results"])
        results["passed"] += tool_results["passed"]
        results["failed"] += tool_results["failed"]
        results["skipped"] += tool_results.get("skipped", 0)
        results["timeouts"] += tool_results.get("timeouts", 0)
    
    # Calculate compliance percentage
    total_tests = results["total"] - results["skipped"]
    compliance_percentage = (results["passed"] / total_tests) * 100 if total_tests > 0 else 0
    
    # Determine compliance status
    if compliance_percentage == 100:
        compliance_status = "✅ Fully Compliant"
    elif compliance_percentage >= 80:
        compliance_status = "⚠️ Mostly Compliant"
    else:
        compliance_status = "❌ Non-Compliant"
    
    log_with_timestamp("\nCompliance Test Results:")
    log_with_timestamp(f"Total tests: {results['total']}")
    log_with_timestamp(f"Passed: {results['passed']}")
    log_with_timestamp(f"Failed: {results['failed']}")
    log_with_timestamp(f"Skipped: {results['skipped']}")
    log_with_timestamp(f"Compliance Status: {compliance_status} ({compliance_percentage:.1f}%)")
    
    # Generate report filename
    server_name = "HTTP MCP Server"  # Generic name for HTTP server
    report_basename = f"cr_{server_name}_{args.protocol_version}_{timestamp}"
    
    # Generate markdown report
    markdown_lines = [
        f"# {server_name} MCP Compliance Report",
        "",
        "## Server Information",
        "",
        f"- **Server URL**: `{args.server_url}`",
        f"- **Protocol Version**: {args.protocol_version}",
        f"- **Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"- **Total Tests**: {results['total']}",
        f"- **Passed**: {results['passed']} ({(results['passed'] / total_tests * 100) if total_tests > 0 else 0:.1f}%)",
        f"- **Failed**: {results['failed']} ({(results['failed'] / total_tests * 100) if total_tests > 0 else 0:.1f}%)",
        f"- **Skipped**: {results['skipped']}",
        "",
        f"**Compliance Status**: {compliance_status} ({compliance_percentage:.1f}%)",
        "",
        "## Detailed Results",
        "",
        "### Passed Tests",
        ""
    ]
    
    # Add passed tests
    passed_tests = [r for r in results["results"] if r.get("passed", False)]
    if passed_tests:
        markdown_lines.append("| Test | Duration | Message |")
        markdown_lines.append("|------|----------|---------|")
        for test in passed_tests:
            test_name = test.get("name", "").replace("test_", "").replace("_", " ").title()
            duration = f"{test.get('duration', 0):.2f}s"
            message = test.get("message", "")
            markdown_lines.append(f"| {test_name} | {duration} | {message} |")
    else:
        markdown_lines.append("No tests passed.")
    
    markdown_lines.extend([
        "",
        "### Failed Tests",
        ""
    ])
    
    # Add failed tests
    failed_tests = [r for r in results["results"] if not r.get("passed", False)]
    if failed_tests:
        markdown_lines.append("| Test | Duration | Error Message |")
        markdown_lines.append("|------|----------|--------------|")
        for test in failed_tests:
            test_name = test.get("name", "").replace("test_", "").replace("_", " ").title()
            duration = f"{test.get('duration', 0):.2f}s"
            message = test.get("message", "")
            markdown_lines.append(f"| {test_name} | {duration} | {message} |")
    else:
        markdown_lines.append("All tests passed! 🎉")
    
    # Write markdown report
    markdown_content = "\n".join(markdown_lines)
    markdown_report_path = os.path.join(output_dir, f"{report_basename}.md")
    with open(markdown_report_path, "w") as f:
        f.write(markdown_content)
    
    log_with_timestamp(f"Markdown compliance report generated: {markdown_report_path}")
    
    # Generate JSON report if requested
    if args.json:
        json_report = {
            "server": server_name,
            "server_url": args.server_url,
            "protocol_version": args.protocol_version,
            "timestamp": timestamp,
            "total_tests": results["total"],
            "passed_tests": results["passed"],
            "failed_tests": results["failed"],
            "skipped_tests": results["skipped"],
            "compliance_percentage": compliance_percentage,
            "compliance_status": compliance_status,
            "results": results["results"]
        }
        
        json_report_path = os.path.join(output_dir, f"{report_basename}.json")
        with open(json_report_path, "w") as f:
            json.dump(json_report, f, indent=2)
        
        log_with_timestamp(f"JSON report saved to: {json_report_path}")
    
    # Return success if fully compliant
    return 0 if compliance_percentage == 100 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 