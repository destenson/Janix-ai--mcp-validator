#!/usr/bin/env python3
"""
Generate a compliance report for an MCP server.

This script runs all tests against an MCP server and generates a detailed compliance report.
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
    """Run the compliance tests and generate a report."""
    parser = argparse.ArgumentParser(description="Generate an MCP server compliance report")
    
    # Server configuration
    parser.add_argument("--server-command", required=True, help="Command to start the server")
    parser.add_argument("--protocol-version", choices=["2024-11-05", "2025-03-26"], 
                        default="2025-03-26", help="Protocol version to use")
    
    # Output options
    parser.add_argument("--output-dir", default="reports", help="Directory to store the report files")
    parser.add_argument("--report-prefix", default="compliance_report", help="Prefix for report filenames")
    parser.add_argument("--json", action="store_true", help="Generate a JSON report")
    
    # Testing options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--skip-async", action="store_true", help="Skip async tool tests (for 2025-03-26)")
    
    args = parser.parse_args()
    
    # Set environment variables for the server
    env_vars = os.environ.copy()
    env_vars["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    # Ensure output directory exists
    output_dir = os.path.join(parent_dir, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for report filenames
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Collect all test cases
    all_tests = []
    all_tests.extend(INIT_TEST_CASES)
    all_tests.extend(TOOLS_TEST_CASES)
    
    # Include async tool tests for 2025-03-26 if not skipped
    if args.protocol_version == "2025-03-26" and not args.skip_async:
        all_tests.extend(ASYNC_TOOLS_TEST_CASES)
    
    print(f"Running compliance tests for protocol {args.protocol_version}...")
    print(f"Server command: {args.server_command}")
    print(f"Total tests to run: {len(all_tests)}")
    
    # Run the tests
    results = await run_tests(
        tests=all_tests,
        protocol=args.protocol_version,
        transport="stdio",
        server_command=args.server_command,
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
        server_command=args.server_command,
        protocol_version=args.protocol_version,
        output_file=markdown_filename
    )
    print(f"\nMarkdown compliance report generated: {report_path}")
    
    # Generate JSON report if requested
    if args.json:
        json_filename = f"{args.report_prefix}_{args.protocol_version}_{timestamp}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        # Add additional metadata to the results
        results["metadata"] = {
            "server_command": args.server_command,
            "protocol_version": args.protocol_version,
            "timestamp": timestamp,
            "compliance_score": compliance_pct,
        }
        
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"JSON report generated: {json_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 