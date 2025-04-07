#!/usr/bin/env python3
"""
Test the minimal STDIO server and generate a markdown report.
This script directly runs the tests without relying on the pytest-md plugin.
"""

import os
import sys
import subprocess
import datetime
import argparse
import os.path

def run_test(test_spec, protocol_version, server_path, reports_dir):
    """
    Run a test against the minimal STDIO server and generate a markdown report.
    
    Args:
        test_spec: Tuple of (module, class, method)
        protocol_version: The protocol version to test against
        server_path: Path to the server script
        reports_dir: Directory to write reports to
    
    Returns:
        The exit code of the test process
    """
    module, cls, method = test_spec
    
    # Set environment variables
    env = os.environ.copy()
    env["MCP_TRANSPORT_TYPE"] = "stdio"
    env["MCP_SERVER_COMMAND"] = server_path
    env["MCP_PROTOCOL_VERSION"] = protocol_version
    env["MCP_DEBUG"] = "true"
    
    # Build the pytest command
    cmd = [
        "python", "-m", "pytest", "-v",
        f"tests/{module}.py::{cls}::{method}"
    ]
    
    print(f"\nRunning test: {' '.join(cmd)}")
    print(f"Environment:")
    print(f"  MCP_TRANSPORT_TYPE: stdio")
    print(f"  MCP_SERVER_COMMAND: {server_path}")
    print(f"  MCP_PROTOCOL_VERSION: {protocol_version}")
    
    # Run the test
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60  # Add a 60-second timeout to prevent hanging
    )
    
    # Generate report filename (using absolute path)
    report_filename = os.path.join(reports_dir, f"stdio_test_{protocol_version}_{module}_{method}.md")
    
    # Print debugging info
    print(f"\nGenerating report at: {report_filename}")
    print(f"Reports directory exists: {os.path.exists(reports_dir)}")
    print(f"Reports directory is writable: {os.access(reports_dir, os.W_OK)}")
    
    # Create reports directory if it doesn't exist
    try:
        os.makedirs(reports_dir, exist_ok=True)
        print(f"Created/verified reports directory: {reports_dir}")
    except Exception as e:
        print(f"Error creating reports directory: {str(e)}")
    
    # Get current time
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d at %H:%M:%S")
    
    # Create report
    try:
        with open(report_filename, "w") as f:
            f.write(f"# STDIO Server Test Report\n\n")
            f.write(f"*Report generated on {date_str}*\n\n")
            
            f.write("## Test Details\n\n")
            f.write(f"- **Test:** {module}.{cls}.{method}\n")
            f.write(f"- **Protocol Version:** {protocol_version}\n")
            f.write(f"- **Server:** Minimal MCP STDIO Server\n")
            f.write(f"- **Server Path:** {server_path}\n\n")
            
            f.write("## Result\n\n")
            status = "PASS" if result.returncode == 0 else "FAIL"
            f.write(f"- **Status:** {status}\n")
            f.write(f"- **Exit Code:** {result.returncode}\n\n")
            
            f.write("## Command\n\n")
            f.write(f"```\n{' '.join(cmd)}\n```\n\n")
            
            f.write("## Standard Output\n\n")
            f.write("```\n")
            f.write(result.stdout)
            f.write("\n```\n\n")
            
            if result.stderr:
                f.write("## Standard Error\n\n")
                f.write("```\n")
                f.write(result.stderr)
                f.write("\n```\n\n")
        
        print(f"Report successfully written to: {report_filename}")
        
        # Double-check file was created
        if os.path.exists(report_filename):
            print(f"Verified report file exists: {report_filename}")
            print(f"File size: {os.path.getsize(report_filename)} bytes")
        else:
            print(f"ERROR: Report file does not exist after writing: {report_filename}")
    
    except Exception as e:
        print(f"Error writing report: {str(e)}")
    
    return result.returncode

def main():
    """Main entry point for the script."""
    # Get the path to the root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_path = os.path.join(root_dir, "minimal_mcp_server", "minimal_mcp_server.py")
    reports_dir = os.path.join(root_dir, "reports")
    
    parser = argparse.ArgumentParser(description="Test the minimal STDIO server")
    parser.add_argument(
        "--protocol-version",
        default="2024-11-05",
        choices=["2024-11-05", "2025-03-26"],
        help="Protocol version to test against"
    )
    parser.add_argument(
        "--test",
        default="basic",
        choices=["basic", "tools", "resources", "batch", "all"],
        help="Which test to run"
    )
    parser.add_argument(
        "--server-path",
        default=server_path,
        help="Path to the server script"
    )
    parser.add_argument(
        "--reports-dir",
        default=reports_dir,
        help="Directory to write reports to"
    )
    
    args = parser.parse_args()
    
    # Make server path absolute
    if not os.path.isabs(args.server_path):
        args.server_path = os.path.abspath(args.server_path)
    
    # Make reports directory absolute
    if not os.path.isabs(args.reports_dir):
        args.reports_dir = os.path.abspath(args.reports_dir)
    
    # Print configuration
    print("\n" + "=" * 60)
    print("Test Configuration")
    print("=" * 60)
    print(f"Protocol Version: {args.protocol_version}")
    print(f"Test Type: {args.test}")
    print(f"Server Path: {args.server_path}")
    print(f"Reports Directory: {args.reports_dir}")
    print("=" * 60)
    
    # Set up test specifications
    tests = []
    
    if args.test == "basic" or args.test == "all":
        tests.append(("test_base_protocol", "TestBasicSTDIO", "test_initialization"))
    
    if args.test == "tools" or args.test == "all":
        tests.append(("test_tools", "TestToolsProtocol", "test_initialization"))
        tests.append(("test_tools", "TestToolsProtocol", "test_tools_list"))
    
    if args.test == "resources" or args.test == "all":
        tests.append(("test_resources", "TestResourcesProtocol", "test_initialization"))
        tests.append(("test_resources", "TestResourcesProtocol", "test_resources_list"))
    
    if args.test == "batch" or args.test == "all":
        tests.append(("test_base_protocol", "TestBasicSTDIO", "test_batch_request"))
    
    # Run the tests
    exit_codes = []
    for test_spec in tests:
        exit_code = run_test(test_spec, args.protocol_version, args.server_path, args.reports_dir)
        exit_codes.append((test_spec, exit_code))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for i, ((module, cls, method), exit_code) in enumerate(exit_codes, 1):
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"{i}. {module}.{cls}.{method}: {status}")
    
    print("=" * 60)
    
    # Return non-zero if any test failed
    return 1 if any(code != 0 for _, code in exit_codes) else 0

if __name__ == "__main__":
    sys.exit(main()) 