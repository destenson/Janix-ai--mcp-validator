# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Report module for MCP Testing Framework.

This module re-exports reporting functions for easier imports.
"""

from mcp_testing.utils.reporter import (
    generate_markdown_report,
    save_markdown_report,
    results_to_markdown
)


def generate_compliance_score(results):
    """
    Calculate the compliance score from test results.
    
    Args:
        results: The test results dictionary
        
    Returns:
        A float representing the compliance score as a percentage
    """
    if results['total'] == 0:
        return 0.0
    
    return round(results['passed'] / results['total'] * 100, 1) 