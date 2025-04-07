#!/usr/bin/env python3
"""
Comprehensive validation for the minimal MCP STDIO server.

This script runs a complete test suite against the minimal MCP STDIO server,
testing all major protocol features with both supported protocol versions.
"""

import os
import sys
import subprocess
import time
import argparse
import json
import datetime
from pathlib import Path

# Get the path to the root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PATH = os.path.join(ROOT_DIR, "minimal_mcp_server", "minimal_mcp_server.py")
VALIDATOR_PATH = os.path.join(ROOT_DIR, "run_validator.py")

# Define the comprehensive test matrix
TEST_MATRIX = [
    # Basic protocol features
    ("test_base_protocol", "TestBasicSTDIO", "test_initialization"),
    ("test_base_protocol", "TestBasicSTDIO", "test_batch_request"),
    
    # Tools features
    ("test_tools", "TestToolsProtocol", "test_tools_list"),
    ("test_tools", "TestToolsProtocol", "test_tools_call"),
    
    # Resources features
    ("test_resources", "TestResourcesProtocol", "test_resources_list"),
    ("test_resources", "TestResourcesProtocol", "test_resources_create"),
    ("test_resources", "TestResourcesProtocol", "test_resources_get"),
    
    # Prompt features
    ("test_prompts", "TestPromptsProtocol", "test_prompt_completion"),
    ("test_prompts", "TestPromptsProtocol", "test_prompt_models"),
    
    # Utilities features
    ("test_utilities", "TestUtilitiesProtocol", "test_server_info"),
    ("test_utilities", "TestUtilitiesProtocol", "test_stdio_specific_behaviors"),
]

# Protocol versions to test
PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26"]

def run_test(test_spec, protocol_version, reports_dir):
    """
    Run a specific test against the minimal MCP STDIO server.
    
    Args:
        test_spec: Tuple of (module, class, method)
        protocol_version: The protocol version to test against
        reports_dir: Directory to store the reports
        
    Returns:
        Dict with test results
    """
    module, cls, method = test_spec
    
    # Generate report name
    report_name = f"stdio_{protocol_version}_{module}_{cls}_{method}.html"
    report_path = os.path.join(reports_dir, report_name)
    
    # Build the command
    cmd = [VALIDATOR_PATH]
    cmd.extend(["--transport", "stdio"])
    cmd.extend(["--server-command", SERVER_PATH])
    cmd.extend(["--protocol-version", protocol_version])
    cmd.extend(["--test-module", module])
    cmd.extend(["--test-class", cls])
    cmd.extend(["--test-method", method])
    cmd.extend(["--report-format", "html"])
    cmd.extend(["--report-path", report_path])
    cmd.extend(["--debug"])
    
    # Print test information
    print(f"\n{'='*80}")
    print(f"Running test: {module}.{cls}.{method}")
    print(f"Protocol version: {protocol_version}")
    print(f"Report: {report_path}")
    print(f"{'='*80}\n")
    
    # Start timer
    start_time = time.time()
    
    # Set environment variables
    env = os.environ.copy()
    env["MCP_DEBUG"] = "true"
    
    # Run the process
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Determine status
        status = "PASS" if process.returncode == 0 else "FAIL"
        
        # Print status
        status_symbol = "✅" if status == "PASS" else "❌"
        print(f"{status_symbol} {status}: {module}.{cls}.{method} ({duration:.2f}s)")
        
        # Return results
        return {
            "test_spec": test_spec,
            "protocol_version": protocol_version,
            "report_path": report_path,
            "status": status,
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "duration": duration,
            "cmd": " ".join(cmd)
        }
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {
            "test_spec": test_spec,
            "protocol_version": protocol_version,
            "report_path": report_path,
            "status": "ERROR",
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration": time.time() - start_time,
            "cmd": " ".join(cmd)
        }

def generate_summary_report(results, reports_dir):
    """
    Generate a summary report in Markdown format.
    
    Args:
        results: List of test results
        reports_dir: Directory containing reports
        
    Returns:
        Path to the summary report
    """
    # Create report filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(reports_dir, f"validation_summary_{timestamp}.md")
    
    # Calculate statistics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["status"] == "PASS")
    failed_tests = sum(1 for r in results if r["status"] == "FAIL")
    error_tests = sum(1 for r in results if r["status"] == "ERROR")
    pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # Generate report content
    with open(report_path, "w") as f:
        # Header
        f.write("# MCP STDIO Server Validation Report\n\n")
        f.write(f"*Report generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Server Tested**: Minimal MCP STDIO Server\n")
        f.write(f"- **Server Path**: {SERVER_PATH}\n")
        f.write(f"- **Protocol Versions**: {', '.join(PROTOCOL_VERSIONS)}\n")
        f.write(f"- **Total Tests**: {total_tests}\n")
        f.write(f"- **Passed Tests**: {passed_tests}\n")
        f.write(f"- **Failed Tests**: {failed_tests}\n")
        f.write(f"- **Error Tests**: {error_tests}\n")
        f.write(f"- **Pass Rate**: {pass_rate:.2f}%\n\n")
        
        # Results by protocol version
        for version in PROTOCOL_VERSIONS:
            version_results = [r for r in results if r["protocol_version"] == version]
            version_total = len(version_results)
            version_passed = sum(1 for r in version_results if r["status"] == "PASS")
            version_failed = sum(1 for r in version_results if r["status"] == "FAIL")
            version_pass_rate = (version_passed / version_total) * 100 if version_total > 0 else 0
            
            f.write(f"## Protocol Version: {version}\n\n")
            f.write(f"- **Tests Run**: {version_total}\n")
            f.write(f"- **Tests Passed**: {version_passed}\n")
            f.write(f"- **Tests Failed**: {version_failed}\n")
            f.write(f"- **Pass Rate**: {version_pass_rate:.2f}%\n\n")
            
            # Results table
            f.write("| Test | Status | Duration (s) | Report |\n")
            f.write("|------|--------|--------------|--------|\n")
            
            for result in version_results:
                module, cls, method = result["test_spec"]
                test_name = f"{module}.{cls}.{method}"
                report_name = os.path.basename(result["report_path"])
                report_rel_path = os.path.relpath(result["report_path"], reports_dir)
                
                status_symbol = "✅" if result["status"] == "PASS" else "❌"
                f.write(f"| {test_name} | {status_symbol} {result['status']} | {result['duration']:.2f} | [Report]({report_rel_path}) |\n")
            
            f.write("\n")
        
        # Detailed failure analysis
        if failed_tests > 0 or error_tests > 0:
            f.write("## Failed Tests\n\n")
            
            for result in results:
                if result["status"] in ["FAIL", "ERROR"]:
                    module, cls, method = result["test_spec"]
                    test_name = f"{module}.{cls}.{method}"
                    
                    f.write(f"### {test_name} ({result['protocol_version']})\n\n")
                    f.write(f"- **Status**: {result['status']}\n")
                    f.write(f"- **Exit Code**: {result['exit_code']}\n")
                    f.write(f"- **Duration**: {result['duration']:.2f}s\n")
                    f.write(f"- **Report**: [Link]({os.path.relpath(result['report_path'], reports_dir)})\n\n")
                    
                    if result["stderr"]:
                        f.write("**Error Output:**\n")
                        f.write("```\n")
                        f.write(result["stderr"])
                        f.write("\n```\n\n")
        
        # Recommendations section
        f.write("## Recommendations\n\n")
        
        if failed_tests == 0 and error_tests == 0:
            f.write("✅ **The minimal MCP STDIO server is fully compliant with both protocol versions.**\n\n")
            f.write("All tests passed successfully. The server can be considered production-ready and fully compliant with the protocol specification.\n")
        else:
            f.write("To achieve full protocol compliance, the following issues need to be addressed:\n\n")
            
            failures_by_category = {}
            
            for result in results:
                if result["status"] in ["FAIL", "ERROR"]:
                    module, cls, method = result["test_spec"]
                    category = module.replace("test_", "")
                    
                    if category not in failures_by_category:
                        failures_by_category[category] = []
                    
                    failures_by_category[category].append({
                        "test_name": f"{cls}.{method}",
                        "protocol_version": result["protocol_version"]
                    })
            
            for category, failures in failures_by_category.items():
                f.write(f"### {category.title()} Issues\n\n")
                
                for failure in failures:
                    f.write(f"- {failure['test_name']} (Protocol {failure['protocol_version']})\n")
                
                f.write("\n")
    
    print(f"\nSummary report written to: {report_path}")
    return report_path

def main():
    parser = argparse.ArgumentParser(description="Run comprehensive validation against the minimal MCP STDIO server")
    parser.add_argument(
        "--reports-dir", 
        default=os.path.join(ROOT_DIR, "reports", "validation"),
        help="Directory to store validation reports"
    )
    
    args = parser.parse_args()
    
    # Create reports directory
    os.makedirs(args.reports_dir, exist_ok=True)
    print(f"Reports will be saved to: {args.reports_dir}")
    
    # Make server file executable
    if os.path.exists(SERVER_PATH):
        os.chmod(SERVER_PATH, 0o755)
        print(f"Server path: {SERVER_PATH} (made executable)")
    else:
        print(f"ERROR: Server not found at {SERVER_PATH}")
        return 1
    
    # Run all tests
    results = []
    
    for protocol_version in PROTOCOL_VERSIONS:
        print(f"\n{'#'*80}")
        print(f"# Testing protocol version: {protocol_version}")
        print(f"{'#'*80}")
        
        for test_spec in TEST_MATRIX:
            result = run_test(test_spec, protocol_version, args.reports_dir)
            results.append(result)
    
    # Generate summary report
    summary_path = generate_summary_report(results, args.reports_dir)
    
    # Calculate final statistics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["status"] == "PASS")
    failed_tests = sum(1 for r in results if r["status"] == "FAIL")
    error_tests = sum(1 for r in results if r["status"] == "ERROR")
    pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"Validation Summary")
    print(f"{'='*80}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ({pass_rate:.2f}%)")
    print(f"Failed: {failed_tests}")
    print(f"Errors: {error_tests}")
    print(f"\nSummary report: {summary_path}")
    
    # Return 0 if all tests passed, otherwise 1
    return 0 if (failed_tests == 0 and error_tests == 0) else 1

if __name__ == "__main__":
    sys.exit(main()) 