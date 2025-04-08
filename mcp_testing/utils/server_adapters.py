#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Server Adapters for MCP Testing Framework.

This module provides server-specific adapters to handle different MCP server implementations.
Each adapter encapsulates the knowledge about how to properly interact with a specific server.
"""

import os
import shlex
from typing import Dict, Any, Optional, List, Tuple

# Available server types
SERVER_TYPES = [
    "generic",          # Standard MCP server
    "fetch",            # Fetch MCP server
    "github",           # GitHub MCP server
    "brave-search",     # Brave Search MCP server
    "postgres",         # PostgreSQL MCP server
    "minimal",          # Minimal MCP server
]


class ServerAdapter:
    """Base class for server adapters."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """
        Initialize the server adapter.
        
        Args:
            server_command: The command to start the server
            debug: Whether to enable debug output
        """
        self.server_command = server_command
        self.debug = debug
        self.server_config = {}
    
    def get_transport_config(self) -> Dict[str, Any]:
        """
        Get transport configuration for this server.
        
        Returns:
            A dictionary with transport configuration
        """
        return {
            "use_shell": False,
            "command_prefix": None
        }
    
    def get_server_config(self) -> Dict[str, Any]:
        """
        Get server-specific configuration.
        
        Returns:
            A dictionary with server configuration
        """
        return self.server_config
    
    def get_environment_vars(self, base_env: Dict[str, str]) -> Dict[str, str]:
        """
        Get environment variables for this server.
        
        Args:
            base_env: Base environment variables
            
        Returns:
            A dictionary with environment variables
        """
        return base_env
    
    def should_skip_shutdown(self) -> bool:
        """
        Check if shutdown should be skipped for this server.
        
        Returns:
            True if shutdown should be skipped, False otherwise
        """
        return False


class GenericServerAdapter(ServerAdapter):
    """Adapter for standard MCP servers."""
    
    def get_transport_config(self) -> Dict[str, Any]:
        """Get transport configuration for generic servers."""
        config = super().get_transport_config()
        
        # Check if the command needs a shell
        if "&&" in self.server_command or ";" in self.server_command:
            config["use_shell"] = True
        elif self.server_command.startswith("source "):
            config["use_shell"] = True
            
        return config


class FetchServerAdapter(ServerAdapter):
    """Adapter for Fetch MCP server."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """Initialize the Fetch server adapter."""
        super().__init__(server_command, debug)
        self.server_config = {
            "skip_shutdown": True,
            "required_tools": ["fetch"]
        }
    
    def get_transport_config(self) -> Dict[str, Any]:
        """Get transport configuration for Fetch server."""
        config = super().get_transport_config()
        
        # Fetch server runs better with shell=True
        config["use_shell"] = True
        
        # Check if we're running from venv
        if "venv" in self.server_command or "fetch_venv" in self.server_command:
            config["use_shell"] = True
            
        return config
    
    def should_skip_shutdown(self) -> bool:
        """Skip shutdown for Fetch server."""
        return True


class GitHubServerAdapter(ServerAdapter):
    """Adapter for GitHub MCP server."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """Initialize the GitHub server adapter."""
        super().__init__(server_command, debug)
        self.server_config = {
            "skip_shutdown": True,
            "required_tools": [
                "create_or_update_file", 
                "push_files", 
                "search_repositories", 
                "get_file_contents"
            ]
        }
    
    def get_environment_vars(self, base_env: Dict[str, str]) -> Dict[str, str]:
        """Get environment variables for GitHub server."""
        env = base_env.copy()
        
        # Ensure GitHub token is set
        if "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
            # Use a default token if available
            if "MCP_DEFAULT_GITHUB_TOKEN" in env:
                env["GITHUB_PERSONAL_ACCESS_TOKEN"] = env["MCP_DEFAULT_GITHUB_TOKEN"]
            elif self.debug:
                print("Warning: GITHUB_PERSONAL_ACCESS_TOKEN not set")
                
        return env
    
    def should_skip_shutdown(self) -> bool:
        """Skip shutdown for GitHub server."""
        return True


class BraveSearchServerAdapter(ServerAdapter):
    """Adapter for Brave Search MCP server."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """Initialize the Brave Search server adapter."""
        super().__init__(server_command, debug)
        self.server_config = {
            "skip_shutdown": True,
            "required_tools": ["brave_web_search", "brave_local_search"]
        }
    
    def get_environment_vars(self, base_env: Dict[str, str]) -> Dict[str, str]:
        """Get environment variables for Brave Search server."""
        env = base_env.copy()
        
        # Ensure Brave API key is set
        if "BRAVE_API_KEY" not in env:
            # Use a default key if available
            if "MCP_DEFAULT_BRAVE_API_KEY" in env:
                env["BRAVE_API_KEY"] = env["MCP_DEFAULT_BRAVE_API_KEY"]
            elif self.debug:
                print("Warning: BRAVE_API_KEY not set")
                
        return env
    
    def should_skip_shutdown(self) -> bool:
        """Skip shutdown for Brave Search server."""
        return True


class PostgresServerAdapter(ServerAdapter):
    """Adapter for PostgreSQL MCP server."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """Initialize the PostgreSQL server adapter."""
        super().__init__(server_command, debug)
        self.server_config = {
            "skip_shutdown": True,
            "required_tools": ["query"]
        }
    
    def get_transport_config(self) -> Dict[str, Any]:
        """Get transport configuration for PostgreSQL server."""
        config = super().get_transport_config()
        
        # PostgreSQL server might need shell=True if run via Python module
        if self.server_command.startswith("python") or "mcp_server" in self.server_command:
            config["use_shell"] = True
            
        return config


class MinimalServerAdapter(ServerAdapter):
    """Adapter for Minimal MCP server."""
    
    def __init__(self, server_command: str, debug: bool = False):
        """Initialize the Minimal server adapter."""
        super().__init__(server_command, debug)
        self.server_config = {
            "required_tools": ["echo", "add"]
        }


def create_server_adapter(server_command: str, server_type: Optional[str] = None, 
                         debug: bool = False) -> ServerAdapter:
    """
    Create a server adapter for the specified server type.
    
    Args:
        server_command: The command to start the server
        server_type: The type of server, or None to auto-detect
        debug: Whether to enable debug output
        
    Returns:
        A server adapter instance
    """
    # Auto-detect server type if not specified
    if server_type is None:
        server_type = detect_server_type(server_command)
        if debug:
            print(f"Auto-detected server type: {server_type}")
    
    # Create the appropriate adapter
    if server_type == "fetch":
        return FetchServerAdapter(server_command, debug)
    elif server_type == "github":
        return GitHubServerAdapter(server_command, debug)
    elif server_type == "brave-search":
        return BraveSearchServerAdapter(server_command, debug)
    elif server_type == "postgres":
        return PostgresServerAdapter(server_command, debug)
    elif server_type == "minimal":
        return MinimalServerAdapter(server_command, debug)
    else:
        return GenericServerAdapter(server_command, debug)


def detect_server_type(server_command: str) -> str:
    """
    Detect the server type from the server command.
    
    Args:
        server_command: The command to start the server
        
    Returns:
        The detected server type
    """
    # Check for known server types
    cmd_lower = server_command.lower()
    
    if "fetch" in cmd_lower or "mcp-server-fetch" in cmd_lower:
        return "fetch"
    elif "github" in cmd_lower or "server-github" in cmd_lower:
        return "github"
    elif "brave" in cmd_lower or "server-brave-search" in cmd_lower:
        return "brave-search"
    elif "postgres" in cmd_lower or "server-postgres" in cmd_lower:
        return "postgres"
    elif "minimal" in cmd_lower or "minimal-mcp-server" in cmd_lower:
        return "minimal"
    
    # Default to generic
    return "generic" 