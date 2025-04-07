#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Validator - Main entry point

This script serves as the main entry point for the MCP Protocol Validator,
providing a unified interface for testing MCP servers with different
transport protocols and protocol versions.
"""

import os
import sys
import importlib.util

# Check if running in a virtual environment
in_venv = sys.prefix != sys.base_prefix

# If not in a virtual environment, re-execute this script in the .venv Python
if not in_venv and os.path.exists(".venv/bin/python"):
    print("Activating virtual environment...")
    os.environ["PYTHONPATH"] = "." + (":" + os.environ["PYTHONPATH"] if "PYTHONPATH" in os.environ else "")
    os.execv(".venv/bin/python", [".venv/bin/python"] + sys.argv)

# Add the current directory to the Python path
if "." not in sys.path:
    sys.path.insert(0, ".")

# Now that we're in the right environment, import dependencies
import asyncio
import importlib
from pathlib import Path
from typing import List, Optional
import pytest

# Import our configuration and logging utilities
from utils.config import get_config, MCPValidatorConfig
from utils.logging import configure_logging, get_logger

# Set up logging
logger = get_logger("main")


def run_tests(config: MCPValidatorConfig) -> int:
    """
    Run the test suite with the given configuration.
    
    Args:
        config: The configuration for the test run
        
    Returns:
        The exit code (0 for success, non-zero for failure)
    """
    # Configure logging
    configure_logging(config.debug)
    
    # Set up the environment variables for compatibility with the tests
    os.environ["MCP_TRANSPORT_TYPE"] = config.transport_type
    os.environ["MCP_SERVER_URL"] = config.server_url
    os.environ["MCP_CLIENT_URL"] = config.client_url
    os.environ["MCP_PROTOCOL_VERSION"] = config.protocol_version
    if config.server_command:
        os.environ["MCP_SERVER_COMMAND"] = config.server_command
    if config.docker_image:
        os.environ["MCP_DOCKER_IMAGE"] = config.docker_image
    if config.mount_dir:
        os.environ["MCP_MOUNT_DIR"] = config.mount_dir
    if config.debug:
        os.environ["MCP_DEBUG"] = "1"
    
    # Build the pytest arguments
    pytest_args = ["-v"]
    
    # Add report format if specified
    if config.report_format:
        if config.report_format == "html":
            pytest_args.append("--html=reports/report.html")
        elif config.report_format == "json":
            pytest_args.append("--json-report")
            pytest_args.append("--json-report-file=reports/report.json")
    
    # Add test modules if specified
    test_files = []
    if config.test_modules:
        for module in config.test_modules:
            if module.startswith("test_"):
                test_files.append(f"tests/{module}.py")
            else:
                test_files.append(f"tests/test_{module}.py")
    else:
        # Default to running all tests
        test_files = ["tests/"]
    
    pytest_args.extend(test_files)
    
    # Create the reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Run the tests
    logger.info(f"Running tests with configuration: {config}")
    logger.info(f"Pytest arguments: {pytest_args}")
    return pytest.main(pytest_args)


def compare_versions(version1: str, version2: str, output: str) -> int:
    """
    Compare two protocol versions and generate a report.
    
    Args:
        version1: The first protocol version to compare
        version2: The second protocol version to compare
        output: The output file for the comparison report
        
    Returns:
        The exit code (0 for success, non-zero for failure)
    """
    # Import the comparison tool
    try:
        compare_tool = importlib.import_module("compare_protocol_versions")
        return compare_tool.compare_versions(version1, version2, output)
    except ImportError:
        logger.error("Could not import comparison tool")
        return 1
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        return 1


async def main() -> int:
    """
    Main entry point for the validator.
    
    Returns:
        The exit code (0 for success, non-zero for failure)
    """
    # Print environment information if debug is enabled
    if any(arg in ["--debug", "-d"] or arg.startswith("--debug=") for arg in sys.argv):
        print(f"Python version: {sys.version}")
        print(f"Python executable: {sys.executable}")
        print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Get configuration
    config = get_config()
    
    # Check if any command-line arguments were provided
    if len(sys.argv) > 1:
        # Handle different commands
        if sys.argv[1] == "compare":
            # We're comparing protocol versions
            if len(sys.argv) < 4:
                print("Usage: python run_validator.py compare --version1 <version1> --version2 <version2> [--output <o>]")
                return 1
                
            version1 = sys.argv[2]
            version2 = sys.argv[3]
            output = sys.argv[4] if len(sys.argv) > 4 else "comparison.html"
            
            return compare_versions(version1, version2, output)
        elif sys.argv[1] == "test":
            # We're running tests with explicit "test" command
            return run_tests(config)
    
    # Default to running tests if no command is specified
    return run_tests(config)


if __name__ == "__main__":
    # Run the main function in an asyncio event loop
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 