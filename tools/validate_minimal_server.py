#!/usr/bin/env python3
"""
Run validation tests against the minimal MCP STDIO server.
"""

import os
import sys
import subprocess
import time
import argparse
import os.path

# Get the path to the root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PATH = os.path.join(ROOT_DIR, "minimal_mcp_stdio_server", "minimal_mcp_stdio_server.py")
VALIDATOR_PATH = os.path.join(ROOT_DIR, "run_validator.py")

def run_test(test_spec, protocol_version="2024-11-05", report_name=None):
    """
    Run a specific test against the minimal MCP STDIO server.
    
    Args:
        test_spec: Tuple of (module, class, method) or just a string for module
        protocol_version: The protocol version to test against
        report_name: Name for the HTML report file
    
    Returns:
        Exit code of the test process
    """
    # Default report name if not provided
    if not report_name:
        if isinstance(test_spec, tuple):
            parts = [p for p in test_spec if p]
            report_name = f"minimal_stdio_{'_'.join(parts)}.html"
        else:
            report_name = f"minimal_stdio_{test_spec}.html"
    
    report_path = os.path.join(ROOT_DIR, "reports", report_name)
    
    # Build the command
    cmd = [VALIDATOR_PATH]
    cmd.extend(["--transport", "stdio"])
    cmd.extend(["--server-command", SERVER_PATH])
    cmd.extend(["--protocol-version", protocol_version])
    cmd.extend(["--report-path", report_path])
    
    # Add test specification
    if isinstance(test_spec, tuple):
        module, cls, method = test_spec
        if module:
            cmd.extend(["--test-module", module])
        if cls:
            cmd.extend(["--test-class", cls])
        if method:
            cmd.extend(["--test-method", method])
    else:
        cmd.extend(["--test-module", test_spec])
    
    # Add debug flag
    cmd.append("--debug")
    
    # Run the command
    print(f"\n\n{'='*80}")
    print(f"Running test: {' '.join(cmd)}")
    print(f"{'='*80}\n")
    
    # Set environment variables
    os.environ["MCP_DEBUG"] = "true"
    
    # Run the process and capture output
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Stream output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        exit_code = process.poll()
        print(f"\nTest completed with exit code: {exit_code}")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Run tests against the minimal MCP STDIO server")
    parser.add_argument(
        "--protocol-version", 
        default="2024-11-05",
        choices=["2024-11-05", "2025-03-26"],
        help="Protocol version to test"
    )
    parser.add_argument(
        "--test", 
        default="basic",
        choices=["basic", "tools", "resources", "all"],
        help="Which test set to run"
    )
    
    args = parser.parse_args()
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(ROOT_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
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
        
    if args.test == "all":
        # Add batch request test
        tests.append(("test_base_protocol", "TestBasicSTDIO", "test_batch_request"))
        
    # Run all specified tests
    exit_codes = []
    for test_spec in tests:
        exit_code = run_test(
            test_spec, 
            protocol_version=args.protocol_version, 
            report_name=f"minimal_stdio_{args.protocol_version}_{test_spec[0]}_{test_spec[2]}.html"
        )
        exit_codes.append(exit_code)
        
        # Short pause between tests
        time.sleep(1)
    
    # Print summary
    print("\n\n" + "="*80)
    print("Test Summary:")
    for i, (test_spec, exit_code) in enumerate(zip(tests, exit_codes)):
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"{i+1}. {test_spec[0]}.{test_spec[2]}: {status} (exit code: {exit_code})")
    print("="*80)
    
    # Return non-zero if any test failed
    return 1 if any(code != 0 for code in exit_codes) else 0

if __name__ == "__main__":
    sys.exit(main()) 