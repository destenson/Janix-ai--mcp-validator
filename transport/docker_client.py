"""
Docker STDIO transport implementation for MCP Protocol Validator.

DEPRECATED: Please use EnhancedDockerSTDIOTransport from enhanced_docker_client.py instead.
"""

import os
import json
import subprocess
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import logging
import warnings

from transport.base import MCPTransport
from transport.stdio_client import STDIOTransport
from transport.enhanced_docker_client import EnhancedDockerSTDIOTransport

logger = logging.getLogger("docker")

class DockerSTDIOTransport(STDIOTransport):
    """
    DEPRECATED: Docker STDIO transport for MCP Protocol Validator.
    Please use EnhancedDockerSTDIOTransport from enhanced_docker_client.py instead.
    
    This class is maintained for backward compatibility.
    """
    
    def __init__(self, 
                docker_image: str,
                mount_path: Optional[str] = None, 
                container_path: str = "/projects",
                network_name: Optional[str] = None,
                protocol_version: Optional[str] = None,
                env_vars: Optional[Dict[str, str]] = None,
                timeout: float = 10.0,
                max_retries: int = 3,
                debug: bool = False):
        """
        Initialize the Docker STDIO transport.
        
        DEPRECATED: Please use EnhancedDockerSTDIOTransport instead.
        """
        warnings.warn(
            "DockerSTDIOTransport is deprecated. Please use EnhancedDockerSTDIOTransport instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.docker_image = docker_image
        self.mount_path = mount_path
        self.container_path = container_path
        self.network_name = network_name
        self.protocol_version = protocol_version
        self.env_vars = env_vars or {}
        
        # Log that we're using the deprecated implementation
        logger.warning("Using deprecated DockerSTDIOTransport - please migrate to EnhancedDockerSTDIOTransport")
        
        # Build the Docker command
        docker_cmd = self._build_docker_command()
        
        # Initialize the parent STDIO transport
        super().__init__(
            command=docker_cmd,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug
        )
    
    def _build_docker_command(self) -> str:
        """
        Build the Docker command string based on the configuration.
        
        Returns:
            The Docker command string
        """
        cmd_parts = ["docker", "run", "-i", "--rm"]
        
        # Add container name for easier debugging
        container_name = f"mcp-validator-{int(time.time())}"
        cmd_parts.extend(["--name", container_name])
        
        # Add network if specified
        if self.network_name:
            cmd_parts.extend(["--network", self.network_name])
        
        # Add mount if specified
        if self.mount_path:
            # Make sure the mount path exists
            os.makedirs(self.mount_path, exist_ok=True)
            cmd_parts.extend(["-v", f"{self.mount_path}:{self.container_path}"])
        
        # Add environment variables
        if self.protocol_version:
            cmd_parts.extend(["--env", f"MCP_PROTOCOL_VERSION={self.protocol_version}"])
        
        for key, value in self.env_vars.items():
            cmd_parts.extend(["--env", f"{key}={value}"])
        
        # Add the image
        cmd_parts.append(self.docker_image)
        
        # Convert to string
        docker_cmd = " ".join(cmd_parts)
        logger.debug(f"Docker command: {docker_cmd}")
        return docker_cmd
    
    def start(self) -> bool:
        """
        Start the Docker container and establish the STDIO connection.
        
        Returns:
            True if started successfully, False otherwise
        """
        # Ensure Docker network exists if specified
        if self.network_name and not self._ensure_network_exists():
            logger.error(f"Failed to ensure Docker network '{self.network_name}' exists")
            return False
        
        # Start the container via parent class
        return super().start()
    
    def _ensure_network_exists(self) -> bool:
        """
        Ensure the specified Docker network exists, creating it if necessary.
        
        Returns:
            True if the network exists or was created, False otherwise
        """
        try:
            # Check if network exists
            result = subprocess.run(
                ["docker", "network", "inspect", self.network_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.debug(f"Creating Docker network: {self.network_name}")
                create_result = subprocess.run(
                    ["docker", "network", "create", self.network_name],
                    capture_output=True,
                    text=True
                )
                
                if create_result.returncode != 0:
                    logger.error(f"Failed to create Docker network: {create_result.stderr}")
                    return False
                    
                logger.debug(f"Created Docker network: {self.network_name}")
            else:
                logger.debug(f"Using existing Docker network: {self.network_name}")
                
            return True
        except Exception as e:
            logger.error(f"Error ensuring Docker network exists: {str(e)}")
            return False
    
    def prepare_test_files(self, test_files_config: List[Dict[str, Any]]) -> bool:
        """
        Prepare test files in the mounted directory.
        
        Args:
            test_files_config: List of file configs with 'path' and 'content' keys
            
        Returns:
            True if files were prepared successfully, False otherwise
        """
        if not self.mount_path:
            logger.error("Cannot prepare test files: No mount path specified")
            return False
            
        try:
            mount_path = Path(self.mount_path)
            
            for file_config in test_files_config:
                file_path = mount_path / file_config.get("path", "")
                content = file_config.get("content", "")
                
                # Create parent directories if needed
                os.makedirs(file_path.parent, exist_ok=True)
                
                # Write the file
                with open(file_path, 'w') as f:
                    f.write(content)
                
                logger.debug(f"Created test file: {file_path}")
                
            return True
        except Exception as e:
            logger.error(f"Error preparing test files: {str(e)}")
            return False

# Create a factory function to get the recommended implementation
def get_docker_transport(*args, **kwargs) -> MCPTransport:
    """
    Factory function to get the recommended Docker transport implementation.
    
    This currently returns EnhancedDockerSTDIOTransport, which has improved error handling and reliability.
    
    Returns:
        An instance of EnhancedDockerSTDIOTransport
    """
    return EnhancedDockerSTDIOTransport(*args, **kwargs) 