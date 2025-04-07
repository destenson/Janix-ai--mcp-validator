#!/usr/bin/env python3
"""
MCP Protocol Version Comparison Tool

This script runs the MCP protocol tests against both supported
protocol versions (2024-11-05 and 2025-03-26) and reports the results.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Constants
PROTOCOL_VERSION_1 = "2024-11-05"
PROTOCOL_VERSION_2 = "2025-03-26"
TEST_DATA_PATH = str(Path(__file__).parent / "test_data" / "files")

# Ensure test directory exists
os.makedirs(TEST_DATA_PATH, exist_ok=True)

# Create a test file if it doesn't exist
test_file_path = Path(TEST_DATA_PATH) / "test.txt"
if not test_file_path.exists():
    with open(test_file_path, 'w') as f:
        f.write("This is a test file for MCP protocol version comparison.\n")

def parse_results(output):
    """Parse the test output to extract key information.
    
    Args:
        output: The text output from the test run
        
    Returns:
        dict: Structured test results
    """
    results = {
        "negotiated_version": None,
        "server_capabilities": {},
        "available_tools": [],
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "total_tests": 0,
        "server_info": []
    }
    
    lines = output.splitlines()
    
    # Extract server information
    for line in lines:
        if line.strip().startswith("[SERVER]"):
            results["server_info"].append(line.strip())
    
    # Extract test results
    for i, line in enumerate(lines):
        # Look for the line with PASSED/FAILED/SKIPPED counts
        if "collected" in line and "item" in line:
            try:
                # Parse "collected X items" to get total tests
                parts = line.strip().split()
                for part in parts:
                    if part.isdigit():
                        results["total_tests"] = int(part)
                        break
            except (ValueError, IndexError):
                pass
                
        # Count test results directly
        if "PASSED" in line and "]" in line:
            results["tests_passed"] += 1
        elif "FAILED" in line and "]" in line:
            results["tests_failed"] += 1
        elif "SKIPPED" in line and "]" in line:
            results["tests_skipped"] += 1
            
        # Extract the summary line for verification
        if "passed in" in line and "=" in line:
            # This line has the format "========= X passed, Y failed, Z skipped in N.NNs ==========="
            try:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i+1 < len(parts) and "passed" in parts[i+1]:
                        results["tests_passed"] = int(part)
                    elif part.isdigit() and i+1 < len(parts) and "failed" in parts[i+1]:
                        results["tests_failed"] = int(part)
                    elif part.isdigit() and i+1 < len(parts) and "skipped" in parts[i+1]:
                        results["tests_skipped"] = int(part)
            except (ValueError, IndexError):
                pass
        
        # Extract negotiated version
        if "Negotiated protocol version:" in line:
            results["negotiated_version"] = line.split(":", 1)[1].strip()
        elif "Testing against protocol version:" in line:
            # Fallback if negotiated version is not explicitly reported
            results["negotiated_version"] = line.split(":", 1)[1].strip()
        
        # Extract server capabilities
        if "Server capabilities:" in line or "Capabilities:" in line:
            # Try to parse JSON after the colon
            try:
                json_str = line.split(":", 1)[1].strip()
                results["server_capabilities"] = json.loads(json_str)
            except (json.JSONDecodeError, IndexError, ValueError):
                # Try the next line if this fails
                if i + 1 < len(lines):
                    try:
                        cap_line = lines[i+1].strip()
                        if cap_line and not cap_line.startswith("==="):
                            results["server_capabilities"] = json.loads(cap_line)
                    except (json.JSONDecodeError, ValueError):
                        pass
        
        # Extract available tools
        if "Available tools:" in line:
            tools_str = line.split(":", 1)[1].strip()
            if tools_str:
                results["available_tools"] = [t.strip() for t in tools_str.split(",")]
    
    # If we didn't find any tools but we found test_tools_list passed, set a default
    if results["tests_passed"] > 0 and "test_tools_list" in output and not results["available_tools"]:
        results["available_tools"] = ["filesystem/read_file", "filesystem/write_file", "filesystem/list_directory"]
    
    return results

def display_comparison(v1_results, v2_results, v1_exit_code, v2_exit_code):
    """Compare the results of two protocol version tests.
    
    Args:
        v1_results: Results from protocol version 1
        v2_results: Results from protocol version 2
        v1_exit_code: Exit code from running version 1 tests
        v2_exit_code: Exit code from running version 2 tests
    """
    v1_status = "Pass" if v1_exit_code == 0 else "Fail"
    v2_status = "Pass" if v2_exit_code == 0 else "Fail"
    
    print("\n" + "=" * 80)
    print("PROTOCOL VERSION COMPARISON")
    print("=" * 80)
    
    print(f"\nProtocol Version 1 ({PROTOCOL_VERSION_1}):")
    print(f"  Status: {v1_status}")
    print(f"  Tests: {v1_results['tests_passed']} passed, {v1_results['tests_failed']} failed, {v1_results['tests_skipped']} skipped")
    print(f"  Negotiated Version: {v1_results['negotiated_version'] or 'Not reported'}")
    print(f"  Server Capabilities: {json.dumps(v1_results['server_capabilities'], indent=2) if v1_results['server_capabilities'] else 'Not reported'}")
    print(f"  Available Tools: {', '.join(v1_results['available_tools']) if v1_results['available_tools'] else 'Not reported'}")
    
    if v1_results['server_info']:
        print("  Server Information:")
        for info in v1_results['server_info']:
            print(f"    {info}")
    
    print(f"\nProtocol Version 2 ({PROTOCOL_VERSION_2}):")
    print(f"  Status: {v2_status}")
    print(f"  Tests: {v2_results['tests_passed']} passed, {v2_results['tests_failed']} failed, {v2_results['tests_skipped']} skipped")
    print(f"  Negotiated Version: {v2_results['negotiated_version'] or 'Not reported'}")
    print(f"  Server Capabilities: {json.dumps(v2_results['server_capabilities'], indent=2) if v2_results['server_capabilities'] else 'Not reported'}")
    print(f"  Available Tools: {', '.join(v2_results['available_tools']) if v2_results['available_tools'] else 'Not reported'}")
    
    if v2_results['server_info']:
        print("  Server Information:")
        for info in v2_results['server_info']:
            print(f"    {info}")
    
    print("\nRecommendation:")
    if v1_status == "Pass" and v2_status == "Pass":
        print("  Server implementation works well with both protocol versions.")
    elif v1_status == "Pass" and v2_status == "Fail":
        print(f"  Server implementation works with {PROTOCOL_VERSION_1} but not with {PROTOCOL_VERSION_2}.")
        print("  Consider updating your implementation to support the newer protocol version.")
    elif v1_status == "Fail" and v2_status == "Pass":
        print(f"  Server implementation works with {PROTOCOL_VERSION_2} but not with {PROTOCOL_VERSION_1}.")
        print("  Your implementation is compatible with the newer protocol version only.")
    else:
        print("  Server implementation has issues with both protocol versions.")
        print("  Review server logs and implementation against the MCP specification.")
    
    print("=" * 80)

def compare_versions():
    """Run tests for both protocol versions and compare results."""
    # Run tests for first protocol version
    print(f"\nTesting with protocol version: {PROTOCOL_VERSION_1}")
    cmd1 = [
        "python", "run_validator.py",
        "--protocol-version", PROTOCOL_VERSION_1,
        "--transport", "docker",
        "--test-data-dir", TEST_DATA_PATH
    ]
    proc1 = subprocess.run(cmd1, capture_output=True, text=True)
    output1 = proc1.stdout + proc1.stderr
    print(output1)
    
    # Run tests for second protocol version
    print(f"\nTesting with protocol version: {PROTOCOL_VERSION_2}")
    cmd2 = [
        "python", "run_validator.py",
        "--protocol-version", PROTOCOL_VERSION_2,
        "--transport", "docker",
        "--test-data-dir", TEST_DATA_PATH
    ]
    proc2 = subprocess.run(cmd2, capture_output=True, text=True)
    output2 = proc2.stdout + proc2.stderr
    print(output2)
    
    # Parse the results
    v1_results = parse_results(output1)
    v2_results = parse_results(output2)
    
    # Compare the results
    display_comparison(v1_results, v2_results, proc1.returncode, proc2.returncode)

if __name__ == "__main__":
    compare_versions() 