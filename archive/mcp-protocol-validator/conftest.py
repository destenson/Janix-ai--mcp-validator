#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Configuration for pytest.
"""

import pytest

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requirement(req_id): mark test as verifying a specific MCP requirement"
    ) 