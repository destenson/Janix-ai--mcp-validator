"""
Configuration module for MCP Protocol Validator.

This module provides configuration options and utilities for the validator,
allowing for customization of transports, servers, and test parameters.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
from enum import Enum, auto

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)

# Set default protocol version
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26"]

class TransportType(Enum):
    HTTP = auto()
    STDIO = auto()
    DOCKER = auto()

# Default transport configurations
DEFAULT_TRANSPORT_CONFIG = {
    TransportType.HTTP: {
        "host": "localhost",
        "port": 7091,
        "timeout": 10.0
    },
    TransportType.STDIO: {
        "command": None,  # Must be provided
        "timeout": 10.0,
        "max_retries": 3
    },
    TransportType.DOCKER: {
        "docker_image": None,  # Must be provided
        "mount_path": None,
        "container_path": "/projects",
        "network_name": "mcp-test-network",
        "timeout": 15.0,
        "max_retries": 5,
        "use_enhanced": True  # Use the enhanced Docker transport by default
    }
}

def get_transport_config(transport_type: TransportType, **overrides) -> Dict[str, Any]:
    """
    Get transport configuration with any overrides applied.
    
    Args:
        transport_type: Type of transport to configure
        **overrides: Override any configuration values
        
    Returns:
        Dictionary of transport configuration values
    """
    config = DEFAULT_TRANSPORT_CONFIG[transport_type].copy()
    config.update(overrides)
    return config

def get_protocol_version() -> str:
    """
    Get the protocol version to use, considering environment variables.
    
    Returns:
        Protocol version string
    """
    return os.environ.get("MCP_PROTOCOL_VERSION", DEFAULT_PROTOCOL_VERSION)

def is_docker_available() -> bool:
    """
    Check if Docker is available on the system.
    
    Returns:
        True if Docker is available, False otherwise
    """
    import shutil
    import subprocess
    
    docker_path = shutil.which("docker")
    if not docker_path:
        return False
    
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def get_transport_instance(transport_type: TransportType, **kwargs) -> Any:
    """
    Create and return an instance of the specified transport.
    
    Args:
        transport_type: Type of transport to create
        **kwargs: Configuration overrides for the transport
        
    Returns:
        An instance of the requested transport
    """
    config = get_transport_config(transport_type, **kwargs)
    
    if transport_type == TransportType.HTTP:
        from transport.http_client import HTTPTransport
        return HTTPTransport(
            host=config["host"],
            port=config["port"],
            timeout=config["timeout"]
        )
    
    elif transport_type == TransportType.STDIO:
        from transport.stdio_client import STDIOTransport
        
        if not config.get("command"):
            raise ValueError("STDIO transport requires a 'command' parameter")
        
        return STDIOTransport(
            command=config["command"],
            timeout=config["timeout"],
            max_retries=config["max_retries"],
            debug=config.get("debug", False)
        )
    
    elif transport_type == TransportType.DOCKER:
        if not config.get("docker_image"):
            raise ValueError("Docker transport requires a 'docker_image' parameter")
            
        # Use the enhanced Docker transport by default
        if config.get("use_enhanced", True):
            from transport.enhanced_docker_client import EnhancedDockerSTDIOTransport
            return EnhancedDockerSTDIOTransport(
                docker_image=config["docker_image"],
                mount_path=config["mount_path"],
                container_path=config["container_path"],
                network_name=config["network_name"],
                protocol_version=config.get("protocol_version", get_protocol_version()),
                env_vars=config.get("env_vars"),
                timeout=config["timeout"],
                max_retries=config["max_retries"],
                debug=config.get("debug", False)
            )
        else:
            # Use the original implementation for backward compatibility
            from transport.docker_client import DockerSTDIOTransport
            return DockerSTDIOTransport(
                docker_image=config["docker_image"],
                mount_path=config["mount_path"],
                container_path=config["container_path"],
                network_name=config["network_name"],
                protocol_version=config.get("protocol_version", get_protocol_version()),
                env_vars=config.get("env_vars"),
                timeout=config["timeout"],
                max_retries=config["max_retries"],
                debug=config.get("debug", False)
            )
    
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

def configure_logging(level: Union[int, str] = logging.INFO):
    """
    Configure logging at the specified level.
    
    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    ) 