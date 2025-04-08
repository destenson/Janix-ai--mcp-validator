# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Server Compatibility Utilities for MCP Testing Framework.

This module provides utilities for handling different server implementations
and ensuring compatibility with various server features.
"""

import os
from typing import Dict, Any, Optional


def is_shutdown_skipped() -> bool:
    """
    Check if shutdown should be skipped based on environment variable.
    
    Returns:
        bool: True if shutdown should be skipped, False otherwise
    """
    skip_shutdown = os.environ.get("MCP_SKIP_SHUTDOWN", "").lower()
    return skip_shutdown in ("true", "1", "yes")


def prepare_environment_for_server(server_command: str) -> Dict[str, str]:
    """
    Prepare environment variables for a specific server.
    
    This function analyzes the server command to determine if any
    special handling is needed for testing this server.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        A dictionary of environment variables to set
    """
    env_vars = os.environ.copy()
    
    # Automatically detect servers known to need shutdown skipping
    if "server-brave-search" in server_command:
        env_vars["MCP_SKIP_SHUTDOWN"] = "true"
    
    return env_vars


def get_server_specific_test_config(server_command: str) -> Dict[str, Any]:
    """
    Get server-specific test configuration.
    
    This function analyzes the server command to determine if any
    server-specific test configuration is needed.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        A dictionary of server-specific test configuration
    """
    config = {}
    
    # Brave Search server configuration
    if "server-brave-search" in server_command:
        config["skip_tests"] = ["test_shutdown", "test_exit_after_shutdown"]
        config["required_tools"] = ["brave_web_search", "brave_local_search"]
    
    return config


def get_recommended_protocol_version(server_command: str) -> Optional[str]:
    """
    Get the recommended protocol version for a specific server.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        The recommended protocol version or None if no specific recommendation
    """
    # Brave Search server uses 2024-11-05
    if "server-brave-search" in server_command:
        return "2024-11-05"
        
    return None 