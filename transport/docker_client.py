"""
Docker STDIO transport implementation for MCP Protocol Validator.

This module provides an implementation of the MCPTransport interface
for communicating with MCP servers running in Docker via STDIO.
"""

import json
import os
import subprocess
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from transport.base import MCPTransport
from transport.stdio_client import STDIOTransport


class DockerSTDIOTransport(STDIOTransport):
    """
    Docker STDIO transport for communicating with MCP servers running in Docker containers.
    
    This class extends the STDIO transport to handle Docker-specific setup and communication.
    """
    
    def __init__(self, 
                docker_image: str,
                mount_path: Optional[str] = None, 
                container_path: str = "/projects",
                network_name: str = "mcp-test-network",
                protocol_version: Optional[str] = None,
                env_vars: Optional[Dict[str, str]] = None,
                timeout: float = 10.0,
                max_retries: int = 3,
                debug: bool = False):
        """
        Initialize the Docker STDIO transport.
        
        Args:
            docker_image: The Docker image to run
            mount_path: Local path to mount in the container (optional)
            container_path: Path in the container to mount to
            network_name: Docker network name to use
            protocol_version: Protocol version to set via environment variable
            env_vars: Additional environment variables to pass to the container
            timeout: Response timeout in seconds
            max_retries: Maximum number of retries for broken pipes
            debug: Whether to enable debug logging
        """
        self.docker_image = docker_image
        self.mount_path = mount_path
        self.container_path = container_path
        self.network_name = network_name
        self.protocol_version = protocol_version
        self.env_vars = env_vars or {}
        
        # Build the Docker command
        docker_cmd = self._build_docker_command()
        
        # Initialize the parent STDIO transport
        super().__init__(
            command=docker_cmd,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug,
            use_shell=True  # Use shell for Docker commands
        )
        
    def _build_docker_command(self) -> str:
        """
        Build the Docker command string based on the configuration.
        
        Returns:
            The Docker command string
        """
        cmd_parts = ["docker", "run", "-i", "--rm"]
        
        # Add network if specified
        if self.network_name:
            cmd_parts.extend(["--network", self.network_name])
        
        # Add mount if specified
        if self.mount_path:
            # Ensure the mount path exists and is absolute
            mount_path = os.path.abspath(self.mount_path)
            os.makedirs(mount_path, exist_ok=True)
            cmd_parts.extend(["--mount", f"type=bind,src={mount_path},dst={self.container_path}"])
        
        # Add environment variables
        env_vars = self.env_vars.copy()
        if self.protocol_version:
            env_vars["MCP_PROTOCOL_VERSION"] = self.protocol_version
            
        for key, value in env_vars.items():
            cmd_parts.extend(["--env", f"{key}={value}"])
        
        # Add the image and command
        cmd_parts.append(self.docker_image)
        cmd_parts.append(self.container_path)
        
        # Convert to string
        return " ".join(cmd_parts)
    
    def start(self) -> bool:
        """
        Start the Docker container and establish the STDIO connection.
        
        Returns:
            True if started successfully, False otherwise
        """
        # Ensure Docker network exists
        if self.network_name and not self._ensure_network_exists():
            self.log_error(f"Failed to ensure Docker network '{self.network_name}' exists")
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
                self.log_debug(f"Creating Docker network: {self.network_name}")
                create_result = subprocess.run(
                    ["docker", "network", "create", self.network_name],
                    capture_output=True,
                    text=True
                )
                
                if create_result.returncode != 0:
                    self.log_error(f"Failed to create Docker network: {create_result.stderr}")
                    return False
                    
                self.log_debug(f"Created Docker network: {self.network_name}")
            else:
                self.log_debug(f"Using existing Docker network: {self.network_name}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Error ensuring Docker network exists: {str(e)}")
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
            self.log_error("Cannot prepare test files: No mount path specified")
            return False
            
        try:
            mount_path = Path(os.path.abspath(self.mount_path))
            
            for file_config in test_files_config:
                file_path = mount_path / file_config.get("path", "")
                content = file_config.get("content", "")
                
                # Create parent directories if needed
                os.makedirs(file_path.parent, exist_ok=True)
                
                # Write the file
                with open(file_path, 'w') as f:
                    f.write(content)
                    
                self.log_debug(f"Created test file: {file_path}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Error preparing test files: {str(e)}")
            return False
    
    def send_request(self, request: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the Docker container via STDIO and get the response.
        
        Args:
            request: Either a complete request object or a method name string
            params: Parameters to pass to the method (if request is a method name)
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            The JSON-RPC response from the server
        """
        # Use the parent class's implementation
        return super().send_request(request, params, request_id)
        
    def send_notification(self, notification: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification to the Docker container via STDIO.
        
        Args:
            notification: Either a complete notification object or a method name string
            params: Parameters to pass to the method (if notification is a method name)
        """
        # Use the parent class's implementation
        super().send_notification(notification, params) 