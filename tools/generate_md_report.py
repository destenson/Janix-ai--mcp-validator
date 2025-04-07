#!/usr/bin/env python3
"""
Generate markdown reports from test results.
"""

import os
import sys
import subprocess
import datetime
import json
import argparse
import os.path

def run_test(test_spec, protocol_version="2024-11-05", server_command=None):
    """
    Run a test and capture the output.
    
    Args:
        test_spec: Tuple of (module, class, method) or just a string for module
        protocol_version: The protocol version to test against
        server_command: The command to run the server
        
    Returns:
        A dictionary with test results
    """
    # Build pytest command
    cmd = ["python", "-m", "pytest", "-v"]
    
    # Add test target
    if isinstance(test_spec, tuple):
        module, cls, method = test_spec
        test_path = f"tests/{module}.py"
        if cls:
            test_path += f"::{cls}"
            if method:
                test_path += f"::{method}"
        cmd.append(test_path)
    else:
        cmd.append(f"tests/{test_spec}.py")
    
    # Set environment variables
    env = os.environ.copy()
    env["MCP_PROTOCOL_VERSION"] = protocol_version
    env["MCP_TRANSPORT_TYPE"] = "stdio"
    
    if server_command:
        env["MCP_SERVER_COMMAND"] = server_command
    
    env["MCP_DEBUG"] = "true"
    
    # Run the command
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    return {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "test_spec": test_spec,
        "protocol_version": protocol_version
    }

def generate_report(test_results, output_path):
    """
    Generate a markdown report from test results.
    
    Args:
        test_results: List of test result dictionaries
        output_path: Path to save the report
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d at %H:%M:%S")
    
    # Create report header
    lines = [
        "# MCP Protocol Validator Test Report",
        "",
        f"*Report generated on {date_str}*",
        "",
        "## Summary",
        "",
    ]
    
    # Add summary statistics
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["returncode"] == 0)
    failed_tests = total_tests - passed_tests
    
    lines.extend([
        f"- **Total Tests:** {total_tests}",
        f"- **Passed:** {passed_tests}",
        f"- **Failed:** {failed_tests}",
        "",
        "## Test Results",
        ""
    ])
    
    # Add detailed results
    for i, result in enumerate(test_results, 1):
        test_spec = result["test_spec"]
        
        if isinstance(test_spec, tuple):
            module, cls, method = test_spec
            test_name = f"{module}"
            if cls:
                test_name += f".{cls}"
            if method:
                test_name += f".{method}"
        else:
            test_name = test_spec
        
        status = "PASS" if result["returncode"] == 0 else "FAIL"
        protocol = result["protocol_version"]
        
        lines.extend([
            f"### {i}. {test_name} ({protocol}) - {status}",
            "",
            "```",
            f"Command: {result['command']}",
            f"Exit code: {result['returncode']}",
            "```",
            "",
            "#### Output:",
            "",
            "```",
            result["stdout"][:2000] + ("..." if len(result["stdout"]) > 2000 else ""),
            "```",
            ""
        ])
        
        if result["stderr"]:
            lines.extend([
                "#### Errors:",
                "",
                "```",
                result["stderr"][:1000] + ("..." if len(result["stderr"]) > 1000 else ""),
                "```",
                ""
            ])
        
        lines.append("---")
        lines.append("")
    
    # Write the report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"Report generated: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate markdown reports from test results")
    parser.add_argument(
        "--protocol-version", 
        default="2024-11-05",
        choices=["2024-11-05", "2025-03-26"],
        help="Protocol version to test"
    )
    parser.add_argument(
        "--server-command", 
        default="./minimal_mcp_server/minimal_mcp_server.py",
        help="Command to run the server"
    )
    parser.add_argument(
        "--output-path", 
        default="reports/test_report.md",
        help="Path to save the report"
    )
    parser.add_argument(
        "--test", 
        default="basic",
        choices=["basic", "tools", "resources", "all"],
        help="Which test set to run"
    )
    
    args = parser.parse_args()
    
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
    
    # Run tests and collect results
    results = []
    for test_spec in tests:
        result = run_test(test_spec, args.protocol_version, args.server_command)
        results.append(result)
    
    # Generate the report
    generate_report(results, args.output_path)
    
    # Return non-zero if any test failed
    return 1 if any(r["returncode"] != 0 for r in results) else 0

if __name__ == "__main__":
    sys.exit(main()) 