#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP HTTP Server package (v2).

This package provides a reference implementation of the MCP HTTP server.
"""

# Version of the package
__version__ = "2.0.0"

from minimal_http_server.v2.server import (
    run_server, main, MCPHTTPServer, MCPHTTPRequestHandler, 
    DEFAULT_HOST, DEFAULT_PORT, SUPPORTED_VERSIONS
)

__all__ = [
    'run_server', 
    'main',
    'MCPHTTPServer',
    'MCPHTTPRequestHandler',
    'DEFAULT_HOST',
    'DEFAULT_PORT',
    'SUPPORTED_VERSIONS',
] 