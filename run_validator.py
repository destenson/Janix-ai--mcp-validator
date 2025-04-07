#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Validator

A unified testing framework for validating MCP protocol server implementations.
Supports both HTTP and STDIO transport protocols and multiple protocol versions.
"""

import os
import sys
import argparse
import subprocess
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_validator")

# Default values
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TRANSPORT = "http"
DEFAULT_PORT = 3000
DEFAULT_REPORT_FORMAT = "html"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP Protocol Validator")
    
    # Transport configuration
    transport_group = parser.add_argument_group("Transport Configuration")
    transport_group.add_argument(
        "--transport",
        choices=["http", "stdio", "docker"],
        default=DEFAULT_TRANSPORT,
        help=f"Transport protocol to use (default: {DEFAULT_TRANSPORT})"
    )
    transport_group.add_argument(
        "--server-url",
        help="URL for HTTP transport (e.g., http://localhost:3000)"
    )
    transport_group.add_argument(
        "--server-command",
        help="Command to start the STDIO server"
    )
    transport_group.add_argument(
        "--docker-image",
        help="Docker image for containerized testing"
    )
    transport_group.add_argument(
        "--mount-dir",
        help="Directory to mount in Docker container"
    )
    
    # Protocol configuration
    protocol_group = parser.add_argument_group("Protocol Configuration")
    protocol_group.add_argument(
        "--protocol-version",
        default=DEFAULT_PROTOCOL_VERSION,
        help=f"MCP protocol version to test (default: {DEFAULT_PROTOCOL_VERSION})"
    )
    
    # Test selection
    test_group = parser.add_argument_group("Test Selection")
    test_group.add_argument(
        "--test-module",
        help="Specific test module to run (e.g., test_tools)"
    )
    test_group.add_argument(
        "--test-class",
        help="Specific test class to run (e.g., TestToolsProtocol)"
    )
    test_group.add_argument(
        "--test-method",
        help="Specific test method to run (e.g., test_tools_list)"
    )
    
    # Reporting
    report_group = parser.add_argument_group("Reporting")
    report_group.add_argument(
        "--report-format",
        choices=["html", "json", "xml"],
        default=DEFAULT_REPORT_FORMAT,
        help=f"Report format (default: {DEFAULT_REPORT_FORMAT})"
    )
    report_group.add_argument(
        "--report-path",
        help="Path to save the report"
    )
    
    # Miscellaneous
    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    misc_group.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for server operations (default: 30)"
    )
    
    return parser.parse_args()


def validate_args(args):
    """Validate command line arguments."""
    # Validate transport-specific arguments
    if args.transport == "http" and not args.server_url:
        args.server_url = f"http://localhost:{DEFAULT_PORT}"
        logger.info(f"Using default server URL: {args.server_url}")
    
    if args.transport == "stdio" and not args.server_command:
        logger.error("--server-command is required for STDIO transport")
        return False
    
    if args.transport == "docker" and not args.docker_image:
        logger.error("--docker-image is required for Docker transport")
        return False
    
    # Validate protocol version
    if args.protocol_version not in ["2024-11-05", "2025-03-26"]:
        logger.warning(f"Unknown protocol version: {args.protocol_version}")
    
    return True


def setup_environment(args):
    """Set up environment variables for testing."""
    # Set environment variables based on arguments
    os.environ["MCP_PROTOCOL_VERSION"] = args.protocol_version
    os.environ["MCP_TRANSPORT_TYPE"] = args.transport
    
    if args.server_url:
        os.environ["MCP_SERVER_URL"] = args.server_url
    
    if args.server_command:
        os.environ["MCP_SERVER_COMMAND"] = args.server_command
    
    if args.docker_image:
        os.environ["MCP_DOCKER_IMAGE"] = args.docker_image
    
    if args.mount_dir:
        os.environ["MCP_MOUNT_DIR"] = args.mount_dir
    
    if args.debug:
        os.environ["MCP_DEBUG"] = "true"
    
    os.environ["MCP_TIMEOUT"] = str(args.timeout)
    
    # Report settings
    if args.report_path:
        os.environ["MCP_REPORT_PATH"] = args.report_path
    
    os.environ["MCP_REPORT_FORMAT"] = args.report_format


def get_test_command(args):
    """Build the pytest command based on arguments."""
    cmd = ["python", "-m", "pytest"]
    
    # Add verbose flag
    cmd.append("-v")
    
    # Add specific test targets if specified
    if args.test_module:
        test_path = f"tests/{args.test_module}.py"
        if args.test_class:
            test_path += f"::{args.test_class}"
            if args.test_method:
                test_path += f"::{args.test_method}"
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # Add report format
    if args.report_format == "html":
        cmd.extend(["--html", args.report_path or "report.html", "--self-contained-html"])
    elif args.report_format == "json":
        cmd.extend(["--json", args.report_path or "report.json"])
    elif args.report_format == "xml":
        cmd.extend(["--junitxml", args.report_path or "report.xml"])
    
    return cmd


def run_tests(cmd):
    """Run the tests using pytest."""
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print the output
        print(process.stdout)
        
        if process.stderr:
            logger.error(f"Test errors: {process.stderr}")
        
        return process.returncode
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for the validator."""
    args = parse_args()
    
    if not validate_args(args):
        sys.exit(1)
    
    setup_environment(args)
    cmd = get_test_command(args)
    returncode = run_tests(cmd)
    
    sys.exit(returncode)


if __name__ == "__main__":
    main() 