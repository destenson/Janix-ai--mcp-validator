"""
Reporter for MCP Testing Framework.

This module provides utilities for generating compliance reports in various formats.
"""

from typing import Dict, Any, List
import json
from datetime import datetime
import os


def generate_markdown_report(results: Dict[str, Any], server_command: str, protocol_version: str) -> str:
    """
    Generate a Markdown compliance report.
    
    Args:
        results: The test results dictionary
        server_command: The command used to start the server
        protocol_version: The protocol version used for testing
        
    Returns:
        A string containing the Markdown report
    """
    # Extract server command details - use the base filename if it's a path
    server_name = server_command.split("/")[-1] if "/" in server_command else server_command
    
    # Get current date and time
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Start building the report
    report = [
        f"# MCP Compliance Report",
        f"",
        f"## Server Information",
        f"",
        f"- **Server Command**: `{server_command}`",
        f"- **Protocol Version**: {protocol_version}",
        f"- **Test Date**: {date_str}",
        f"",
        f"## Summary",
        f"",
        f"- **Total Tests**: {results['total']}",
        f"- **Passed**: {results['passed']} ({round(results['passed'] / results['total'] * 100, 1)}%)",
        f"- **Failed**: {results['failed']} ({round(results['failed'] / results['total'] * 100, 1)}%)",
        f"",
    ]
    
    # Add compliance badge
    if results['failed'] == 0:
        report.append(f"**Compliance Status**: ✅ Fully Compliant")
    elif results['passed'] / results['total'] >= 0.8:
        report.append(f"**Compliance Status**: ⚠️ Mostly Compliant ({round(results['passed'] / results['total'] * 100, 1)}%)")
    else:
        report.append(f"**Compliance Status**: ❌ Non-Compliant ({round(results['passed'] / results['total'] * 100, 1)}%)")
    
    report.extend([
        f"",
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


def results_to_markdown(results: Dict[str, Any], server_command: str, protocol_version: str, output_file: str = None) -> str:
    """
    Generate and save a Markdown compliance report from test results.
    
    Args:
        results: The test results dictionary
        server_command: The command used to start the server
        protocol_version: The protocol version used for testing
        output_file: The filename to save to (if None, a default name will be generated)
        
    Returns:
        The path to the saved file
    """
    report = generate_markdown_report(results, server_command, protocol_version)
    return save_markdown_report(report, output_file) 