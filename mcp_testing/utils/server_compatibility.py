# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Server Compatibility Utilities for MCP Testing Framework.

This module provides utilities for handling different server implementations
and ensuring compatibility with various server features.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Directory for server configuration files
SERVER_CONFIG_DIR = Path(__file__).parent.parent / "server_configs"


def is_shutdown_skipped() -> bool:
    """
    Check if shutdown should be skipped based on environment variable.
    
    Returns:
        bool: True if shutdown should be skipped, False otherwise
    """
    skip_shutdown = os.environ.get("MCP_SKIP_SHUTDOWN", "").lower()
    return skip_shutdown in ("true", "1", "yes")


def load_server_configs() -> Dict[str, Dict[str, Any]]:
    """
    Load server configurations from the server_configs directory.
    
    Each server can have a JSON configuration file in the server_configs directory.
    The filename should be descriptive of the server, e.g., brave-search.json.
    
    Returns:
        Dictionary mapping server identifiers to their configurations
    """
    configs = {}
    
    # Ensure the config directory exists
    SERVER_CONFIG_DIR.mkdir(exist_ok=True, parents=True)
    
    # Load each JSON configuration file
    for config_file in SERVER_CONFIG_DIR.glob("*.json"):
        try:
            with open(config_file, "r") as f:
                server_config = json.load(f)
                
                # Check if the config has identifiers and is valid
                if "identifiers" in server_config and isinstance(server_config["identifiers"], list):
                    for identifier in server_config["identifiers"]:
                        configs[identifier] = server_config
                else:
                    print(f"Warning: Skipping {config_file.name} - missing 'identifiers' array")
                    
        except Exception as e:
            print(f"Error loading server configuration from {config_file.name}: {str(e)}")
            
    return configs


def prepare_environment_for_server(server_command: str) -> Dict[str, str]:
    """
    Prepare environment variables for a specific server.
    
    This function analyzes the server command to find a matching configuration
    and applies the required environment variables.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        A dictionary of environment variables to set
    """
    env_vars = os.environ.copy()
    
    # Load server configurations
    server_configs = load_server_configs()
    
    # Find matching server configuration
    matching_config = None
    matching_identifier = None
    
    for identifier, config in server_configs.items():
        if identifier in server_command:
            matching_config = config
            matching_identifier = identifier
            break
    
    # Default configs for known servers - fallback if no JSON configs exist
    if not matching_config:
        # Check for known server patterns
        if "server-brave-search" in server_command:
            # Create default Brave Search config
            matching_config = {
                "name": "Brave Search",
                "identifiers": ["server-brave-search"],
                "environment": {
                    "BRAVE_API_KEY": "API key for Brave Search API access",
                    "MCP_SKIP_SHUTDOWN": "true"
                },
                "skip_tests": ["test_shutdown", "test_exit_after_shutdown"],
                "required_tools": ["brave_web_search", "brave_local_search"],
                "recommended_protocol": "2024-11-05"
            }
            matching_identifier = "server-brave-search"
            
            # Save the default config for future use
            try:
                os.makedirs(SERVER_CONFIG_DIR, exist_ok=True)
                config_path = SERVER_CONFIG_DIR / "brave-search.json"
                with open(config_path, "w") as f:
                    json.dump(matching_config, f, indent=2)
                print(f"Created default configuration for Brave Search at {config_path}")
            except Exception as e:
                print(f"Warning: Couldn't save default Brave Search config: {str(e)}")
    
    # Apply configuration if found
    if matching_config and "environment" in matching_config:
        print(f"Found configuration for {matching_config.get('name', matching_identifier)}")
        
        # Apply each required environment variable
        for var_name, description in matching_config["environment"].items():
            # Skip if already set in the environment
            if var_name in env_vars and env_vars[var_name]:
                continue
            
            # Check if there's a default value set through MCP_DEFAULT_{VAR_NAME}
            default_var = f"MCP_DEFAULT_{var_name}"
            if default_var in os.environ:
                env_vars[var_name] = os.environ[default_var]
                print(f"Using default value for {var_name} from {default_var}")
            else:
                # For some variables, we can set automatic defaults
                if var_name == "MCP_SKIP_SHUTDOWN":
                    env_vars[var_name] = "true"
                else:
                    # Warn about missing required environment variables
                    print(f"Warning: {matching_identifier} requires {var_name} ({description})")
                    print(f"Set {var_name} environment variable or {default_var} for automated tests")
    
    return env_vars


def get_server_specific_test_config(server_command: str) -> Dict[str, Any]:
    """
    Get server-specific test configuration.
    
    Args:
        server_command: The command used to start the server
        
    Returns:
        A dictionary of server-specific test configuration
    """
    # Load server configurations
    server_configs = load_server_configs()
    
    # Default configuration
    config = {}
    
    # Find matching server configuration
    for identifier, server_config in server_configs.items():
        if identifier in server_command:
            # Extract test configuration
            if "skip_tests" in server_config:
                config["skip_tests"] = server_config["skip_tests"]
                
            if "required_tools" in server_config:
                config["required_tools"] = server_config["required_tools"]
            
            # Found a match, no need to continue searching
            return config
    
    # Fallback for known servers
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
    # Load server configurations
    server_configs = load_server_configs()
    
    # Find matching server configuration
    for identifier, config in server_configs.items():
        if identifier in server_command:
            # Return recommended protocol if defined
            return config.get("recommended_protocol", None)
    
    # Fallback for known servers
    if "server-brave-search" in server_command:
        return "2024-11-05"
        
    return None 