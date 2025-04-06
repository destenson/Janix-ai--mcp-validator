#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Pytest configuration for MCP tests.
"""

import pytest

def pytest_configure(config):
    """Register custom markers for MCP tests."""
    config.addinivalue_line("markers", 
                           "requirement(req): mark test as verifying a specific MCP requirement")
    config.addinivalue_line("markers", 
                           "http_only: mark test as depending on HTTP-specific functionality") 