#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Pytest configuration for MCP tests.
"""

import os
import pytest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")
MCP_TRANSPORT_TYPE = os.environ.get("MCP_TRANSPORT_TYPE", "stdio")

def pytest_configure(config):
    """Register custom markers for MCP tests."""
    # Generic requirement marker
    config.addinivalue_line("markers", 
                           "requirement(req): mark test as verifying a specific MCP requirement")
    
    # Transport type markers
    config.addinivalue_line("markers", 
                           "http_only: mark test as depending on HTTP-specific functionality")
    config.addinivalue_line("markers", 
                           "stdio_only: mark test as depending on STDIO-specific functionality")
    config.addinivalue_line("markers", 
                           "docker_only: mark test as requiring Docker")
    
    # Protocol version markers
    config.addinivalue_line("markers", 
                           "v2024_11_05: mark test as compatible with 2024-11-05 protocol version")
    config.addinivalue_line("markers", 
                           "v2025_03_26: mark test as compatible with 2025-03-26 protocol version")
    config.addinivalue_line("markers", 
                           "v2024_11_05_only: mark test as only compatible with 2024-11-05 protocol version")
    config.addinivalue_line("markers", 
                           "v2025_03_26_only: mark test as only compatible with 2025-03-26 protocol version")

def pytest_collection_modifyitems(config, items):
    """Skip tests based on protocol version and transport type compatibility."""
    protocol_version = MCP_PROTOCOL_VERSION
    transport_type = MCP_TRANSPORT_TYPE
    
    for item in items:
        # Handle protocol version compatibility
        if protocol_version == "2024-11-05":
            if item.get_closest_marker("v2025_03_26_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires 2025-03-26 protocol version"))
        elif protocol_version == "2025-03-26":
            if item.get_closest_marker("v2024_11_05_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires 2024-11-05 protocol version"))
        
        # Handle transport type compatibility
        if transport_type == "http":
            if item.get_closest_marker("stdio_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires STDIO transport"))
            if item.get_closest_marker("docker_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires Docker transport"))
        elif transport_type == "stdio":
            if item.get_closest_marker("http_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires HTTP transport"))
            if item.get_closest_marker("docker_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires Docker transport"))
        elif transport_type == "docker":
            if item.get_closest_marker("http_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires HTTP transport"))
            if item.get_closest_marker("stdio_only"):
                item.add_marker(pytest.mark.skip(reason="Test requires STDIO transport"))

@pytest.fixture(scope="session")
def protocol_version():
    """Return the current protocol version being tested."""
    return MCP_PROTOCOL_VERSION

@pytest.fixture(scope="session")
def transport_type():
    """Return the current transport type being used."""
    return MCP_TRANSPORT_TYPE 