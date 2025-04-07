"""
Configuration handling for the MCP protocol validator.

This module provides a centralized configuration system for the validator,
handling command-line arguments, environment variables, and default values.
"""

import os
import argparse
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


@dataclass
class MCPValidatorConfig:
    """Configuration class for the MCP protocol validator."""
    
    # Transport settings
    transport_type: str = "http"  # "http", "stdio", or "docker"
    server_url: str = "http://localhost:8080"
    client_url: str = "http://localhost:8081"
    server_command: Optional[str] = None
    docker_image: Optional[str] = None
    mount_dir: Optional[str] = None
    
    # Protocol settings
    protocol_version: str = "2024-11-05"
    
    # Test selection
    test_modules: List[str] = None
    
    # Reporting
    report_format: str = "html"
    report_path: Optional[str] = None
    
    # Debugging
    debug: bool = False
    timeout: float = 10.0
    max_retries: int = 3

    def __post_init__(self):
        """Initialize defaults for mutable fields."""
        if self.test_modules is None:
            self.test_modules = []


def load_config_from_env() -> MCPValidatorConfig:
    """
    Load configuration from environment variables.
    
    Returns:
        A MCPValidatorConfig object populated from environment variables.
    """
    return MCPValidatorConfig(
        transport_type=os.environ.get("MCP_TRANSPORT_TYPE", "http"),
        server_url=os.environ.get("MCP_SERVER_URL", "http://localhost:8080"),
        client_url=os.environ.get("MCP_CLIENT_URL", "http://localhost:8081"),
        server_command=os.environ.get("MCP_SERVER_COMMAND", None),
        docker_image=os.environ.get("MCP_DOCKER_IMAGE", None),
        mount_dir=os.environ.get("MCP_MOUNT_DIR", None),
        protocol_version=os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05"),
        test_modules=os.environ.get("MCP_TEST_MODULES", "").split(",") if os.environ.get("MCP_TEST_MODULES") else [],
        report_format=os.environ.get("MCP_REPORT_FORMAT", "html"),
        report_path=os.environ.get("MCP_REPORT_PATH", None),
        debug=os.environ.get("MCP_DEBUG", "0").lower() in ("1", "true", "yes"),
        timeout=float(os.environ.get("MCP_TIMEOUT", "10.0")),
        max_retries=int(os.environ.get("MCP_MAX_RETRIES", "3")),
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the validator.
    
    Returns:
        An argparse.Namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(description="MCP Protocol Validator")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests against an MCP server")
    test_parser.add_argument("--transport", choices=["http", "stdio", "docker"], 
                            default="http", help="Transport protocol to use")
    test_parser.add_argument("--url", help="URL for HTTP servers")
    test_parser.add_argument("--server-command", help="Command to start STDIO servers")
    test_parser.add_argument("--docker-image", help="Docker image for containerized servers")
    test_parser.add_argument("--mount-dir", help="Directory to mount in Docker container")
    test_parser.add_argument("--protocol-version", default="2024-11-05", 
                            help="Protocol version to test against")
    test_parser.add_argument("--test-modules", nargs="+", 
                            help="Specific test modules to run")
    test_parser.add_argument("--report-format", choices=["html", "json"], 
                            default="html", help="Report format")
    test_parser.add_argument("--report-path", help="Path to save the report")
    test_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    test_parser.add_argument("--timeout", type=float, default=10.0,
                            help="Timeout for requests in seconds")
    test_parser.add_argument("--max-retries", type=int, default=3,
                            help="Maximum number of retries for failed requests")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", 
                                          help="Compare protocol versions")
    compare_parser.add_argument("--version1", required=True, 
                               help="First protocol version")
    compare_parser.add_argument("--version2", required=True, 
                               help="Second protocol version")
    compare_parser.add_argument("--output", default="comparison.html", 
                               help="Output file for comparison report")
    
    return parser.parse_args()


def get_config() -> MCPValidatorConfig:
    """
    Get the configuration by combining command-line args and environment variables.
    
    Command-line arguments take precedence over environment variables.
    
    Returns:
        A MCPValidatorConfig object with the final configuration.
    """
    # Start with env vars
    config = load_config_from_env()
    
    # Parse command-line args
    args = parse_args()
    
    # If the command is 'test', update config with command-line args
    if getattr(args, "command", None) == "test":
        if args.transport:
            config.transport_type = args.transport
        if args.url:
            config.server_url = args.url
        if args.server_command:
            config.server_command = args.server_command
        if args.docker_image:
            config.docker_image = args.docker_image
        if args.mount_dir:
            config.mount_dir = args.mount_dir
        if args.protocol_version:
            config.protocol_version = args.protocol_version
        if args.test_modules:
            config.test_modules = args.test_modules
        if args.report_format:
            config.report_format = args.report_format
        if args.report_path:
            config.report_path = args.report_path
        if args.debug:
            config.debug = args.debug
        if args.timeout:
            config.timeout = args.timeout
        if args.max_retries:
            config.max_retries = args.max_retries
    
    return config 