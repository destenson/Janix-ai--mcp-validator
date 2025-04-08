# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Reporter for MCP Testing Framework.

This module provides utilities for generating compliance reports in various formats.
"""

from typing import Dict, Any, List
import json
from datetime import datetime
import os
import re

# Import the specification coverage metrics
try:
    from mcp_testing.tests.specification_coverage import get_specification_coverage
except ImportError:
    # Define a fallback if the module is not available
    def get_specification_coverage(version: str, test_mode: str = "spec") -> Dict[str, Dict[str, Any]]:
        """Fallback function if the specification_coverage module is not available."""
        coverage = {}
        for req_type in ["must", "should", "may"]:
            coverage[req_type] = {
                "total": 0,
                "covered": 0,
                "percentage": 0,
                "required": req_type == "must" or test_mode == "spec"
            }
        coverage["all"] = {
            "total": 0,
            "covered": 0,
            "percentage": 0,
            "required": True
        }
        return coverage


def extract_server_name(server_command: str) -> str:
    """
    Extract a clean server name from the server command.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        A clean server name suitable for display and filenames
    """
    # Extract the base command without paths
    server_name = server_command.split("/")[-1] if "/" in server_command else server_command
    
    # Handle npm package commands
    if "npx" in server_name and "@" in server_name:
        # Extract the package name from something like 'npx -y @modelcontextprotocol/server-brave-search'
        parts = server_name.split("@")
        if len(parts) > 1:
            # Extract the part after the @ symbol
            package_parts = parts[1].split("/")
            if len(package_parts) > 1:
                server_name = package_parts[1]  # Get the part after the slash
    else:
        # For other commands, just use the first part (before any arguments)
        server_name = server_name.split(" ")[0]
    
    # Handle Python scripts
    if server_name.endswith(".py"):
        # Extract the base name without extension
        server_name = os.path.splitext(server_name)[0]
    
    # Clean up the name
    server_name = server_name.replace("-", " ").replace("server ", "").replace("_", " ")
    server_name = re.sub(r'\s+', ' ', server_name).strip()  # Normalize whitespace
    
    # Title case the name
    return server_name.title()


def generate_markdown_report(results: Dict[str, Any], server_command: str, protocol_version: str, server_config: Dict[str, Any] = None) -> str:
    """
    Generate a Markdown compliance report.
    
    Args:
        results: The test results dictionary
        server_command: The command used to start the server
        protocol_version: The protocol version used for testing
        server_config: Optional server configuration dictionary
        
    Returns:
        A string containing the Markdown report
    """
    # Get a clean server name for display
    display_name = extract_server_name(server_command)
    
    # Get current date and time
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Start building the report with server name at the top
    report = [
        f"# {display_name} MCP Compliance Report",
        f"",
    ]
    
    # Add server metadata
    metadata = {"Server": display_name, "Version": protocol_version, "Date": date_str}
    
    # Extract additional metadata from server config
    if server_config and isinstance(server_config, dict):
        if "required_tools" in server_config:
            tools = ", ".join(server_config["required_tools"])
            metadata["Tools"] = tools
    
    # Add metadata table
    report.append("| Metadata | Value |")
    report.append("|----------|-------|")
    for key, value in metadata.items():
        report.append(f"| **{key}** | {value} |")
    report.append("")
    
    # Continue with standard report sections
    report.extend([
        f"## Server Information",
        f"",
        f"- **Server Command**: `{server_command}`",
        f"- **Protocol Version**: {protocol_version}",
        f"- **Test Date**: {date_str}",
        f"",
    ])
    
    # Add server config info if provided
    if server_config:
        report.append("## Server Configuration\n")
        for key, value in server_config.items():
            report.append(f"- **{key}**: {value}")
        report.append("")
    
    report.extend([
        f"## Summary",
        f"",
        f"- **Total Tests**: {results['total']}",
        f"- **Passed**: {results['passed']} ({round(results['passed'] / results['total'] * 100, 1)}%)",
        f"- **Failed**: {results['failed']} ({round(results['failed'] / results['total'] * 100, 1)}%)",
        f"",
    ])
    
    # Add compliance badge
    if results['failed'] == 0:
        report.append(f"**Compliance Status**: ✅ Fully Compliant")
    elif results['passed'] / results['total'] >= 0.8:
        report.append(f"**Compliance Status**: ⚠️ Mostly Compliant ({round(results['passed'] / results['total'] * 100, 1)}%)")
    else:
        report.append(f"**Compliance Status**: ❌ Non-Compliant ({round(results['passed'] / results['total'] * 100, 1)}%)")
    
    # Add specification coverage section
    coverage = get_specification_coverage(protocol_version, "spec")
    if coverage:
        report.extend([
            f"",
            f"## Specification Coverage",
            f"",
            f"This report includes tests for requirements from the {protocol_version} protocol specification.",
            f"",
        ])
        
        # Add coverage table
        report.append("| Requirement Type | Tested | Total | Coverage |")
        report.append("|-----------------|--------|-------|----------|")
        
        # MUST requirements
        must_tested = coverage["must"]["covered"]
        must_total = coverage["must"]["total"]
        must_pct = coverage["must"]["percentage"]
        report.append(f"| **MUST** | {must_tested} | {must_total} | {must_pct}% |")
        
        # SHOULD requirements
        should_tested = coverage["should"]["covered"]
        should_total = coverage["should"]["total"]
        should_pct = coverage["should"]["percentage"]
        report.append(f"| **SHOULD** | {should_tested} | {should_total} | {should_pct}% |")
        
        # MAY requirements
        may_tested = coverage["may"]["covered"]
        may_total = coverage["may"]["total"]
        may_pct = coverage["may"]["percentage"]
        report.append(f"| **MAY** | {may_tested} | {may_total} | {may_pct}% |")
        
        # Total requirements
        total_tested = coverage["all"]["covered"]
        total_reqs = coverage["all"]["total"]
        total_pct = coverage["all"]["percentage"]
        report.append(f"| **TOTAL** | {total_tested} | {total_reqs} | {total_pct}% |")
        
        report.append("")
    
    report.extend([
        f"## Detailed Results",
        f"",
        f"### Passed Tests",
        f"",
    ])
    
    # Add passed tests
    passed_tests = [r for r in results['results'] if r['passed']]
    if passed_tests:
        report.append("| Test | Duration | Message |")
        report.append("|------|----------|---------|")
        for test in passed_tests:
            # Clean up the test name by removing the "test_" prefix if present
            test_name = test['name']
            if test_name.startswith('test_'):
                test_name = test_name[5:]
            test_name = test_name.replace('_', ' ').title()
            
            duration = f"{test['duration']:.2f}s" if 'duration' in test else "N/A"
            message = test['message'] if 'message' in test else ""
            report.append(f"| {test_name} | {duration} | {message} |")
    else:
        report.append("No tests passed.")
    
    report.extend([
        f"",
        f"### Failed Tests",
        f"",
    ])
    
    # Add failed tests
    failed_tests = [r for r in results['results'] if not r['passed']]
    if failed_tests:
        report.append("| Test | Duration | Error Message |")
        report.append("|------|----------|--------------|")
        for test in failed_tests:
            # Clean up the test name by removing the "test_" prefix if present
            test_name = test['name']
            if test_name.startswith('test_'):
                test_name = test_name[5:]
            test_name = test_name.replace('_', ' ').title()
            
            duration = f"{test['duration']:.2f}s" if 'duration' in test else "N/A"
            message = test['message'] if 'message' in test else ""
            report.append(f"| {test_name} | {duration} | {message} |")
    else:
        report.append("All tests passed! 🎉")
    
    # Add test categories
    report.extend([
        f"",
        f"## Test Categories",
        f"",
    ])
    
    # Group tests by category
    categories = {}
    for test in results['results']:
        # Extract category from test name
        name = test['name']
        if name.startswith('test_'):
            name = name[5:]
            
        if '_' in name:
            # Use the part before the first underscore as the category
            category = name.split('_')[0].title()
        else:
            category = "General"
            
        if category not in categories:
            categories[category] = {'total': 0, 'passed': 0, 'failed': 0}
            
        categories[category]['total'] += 1
        if test['passed']:
            categories[category]['passed'] += 1
        else:
            categories[category]['failed'] += 1
    
    report.append("| Category | Total | Passed | Failed | Compliance |")
    report.append("|----------|-------|--------|--------|------------|")
    
    for category, stats in sorted(categories.items()):
        compliance_pct = round(stats['passed'] / stats['total'] * 100, 1)
        if compliance_pct == 100:
            compliance = "✅ 100%"
        elif compliance_pct >= 80:
            compliance = f"⚠️ {compliance_pct}%"
        else:
            compliance = f"❌ {compliance_pct}%"
            
        report.append(f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {compliance} |")
    
    # Add protocol-specific notes
    if protocol_version == "2025-03-26":
        report.extend([
            f"",
            f"## Protocol Notes",
            f"",
            f"This report includes tests for async tool functionality introduced in the 2025-03-26 protocol version.",
            f"- tools/call-async - Asynchronous tool calls",
            f"- tools/result - Polling for async tool results",
            f"- tools/cancel - Cancelling async operations",
        ])
    
    # Add footer
    report.extend([
        f"",
        f"---",
        f"Generated by MCP Testing Framework on {date_str}",
    ])
    
    return "\n".join(report)


def save_markdown_report(report: str, output_file: str = None) -> str:
    """
    Save a Markdown report to a file.
    
    Args:
        report: The Markdown report string
        output_file: The filename to save to (if None, a default name will be generated)
        
    Returns:
        The path to the saved file
    """
    if output_file is None:
        # Generate a default filename based on the current date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mcp_compliance_report_{timestamp}.md"
    
    # Create the reports directory if it doesn't exist
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Save the report
    output_path = os.path.join(reports_dir, output_file)
    with open(output_path, "w") as f:
        f.write(report)
    
    return output_path


def results_to_markdown(results: Dict[str, Any], server_command: str, protocol_version: str, output_file: str = None, server_config: Dict[str, Any] = None) -> str:
    """
    Generate and save a Markdown compliance report from test results.
    
    Args:
        results: The test results dictionary
        server_command: The command used to start the server
        protocol_version: The protocol version used for testing
        output_file: The filename to save to (if None, a default name will be generated)
        server_config: Optional server configuration dictionary
        
    Returns:
        The path to the saved file
    """
    report = generate_markdown_report(results, server_command, protocol_version, server_config)
    return save_markdown_report(report, output_file) 