"""
Enhanced Docker STDIO transport implementation for MCP Protocol Validator.

This module provides an improved implementation of the DockerSTDIOTransport
with better error handling, more reliable connection management, and enhanced debugging.
"""

import json
import os
import subprocess
import time
import shutil
import signal
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import logging

from transport.base import MCPTransport
from transport.stdio_client import STDIOTransport

logger = logging.getLogger("enhanced_docker")

class EnhancedDockerSTDIOTransport(STDIOTransport):
    """
    Enhanced Docker STDIO transport for communicating with MCP servers running in Docker containers.
    
    This class extends the STDIO transport to handle Docker-specific setup and communication
    with improved error handling and debugging capabilities.
    """
    
    def __init__(self, 
                docker_image: str,
                mount_path: Optional[str] = None, 
                container_path: str = "/projects",
                network_name: Optional[str] = None,
                protocol_version: Optional[str] = None,
                env_vars: Optional[Dict[str, str]] = None,
                timeout: float = 15.0,
                max_retries: int = 5,
                debug: bool = False,
                container_name: Optional[str] = None):
        """
        Initialize the Enhanced Docker STDIO transport.
        
        Args:
            docker_image: The Docker image to run
            mount_path: Local path to mount in the container (optional)
            container_path: Path in the container to mount to
            network_name: Docker network name to use (optional)
            protocol_version: Protocol version to set via environment variable
            env_vars: Additional environment variables to pass to the container
            timeout: Response timeout in seconds
            max_retries: Maximum number of retries for broken pipes
            debug: Whether to enable debug logging
            container_name: Specific name for the container (optional)
        """
        self.docker_image = docker_image
        self.mount_path = mount_path
        self.container_path = container_path
        self.network_name = network_name
        self.protocol_version = protocol_version
        self.env_vars = env_vars or {}
        self.container_name = container_name or f"mcp-validator-{int(time.time())}"
        self.container_id = None
        
        # Verify Docker is installed
        if not self._check_docker_installed():
            raise RuntimeError("Docker is not installed or not available in PATH")
        
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
    
    def _check_docker_installed(self) -> bool:
        """
        Check if Docker is installed and available.
        
        Returns:
            True if Docker is installed, False otherwise
        """
        docker_path = shutil.which("docker")
        if not docker_path:
            self.log_error("Docker is not installed or not in PATH")
            return False
        
        # Try to run a simple Docker command
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.log_error(f"Docker is installed but not functioning properly: {result.stderr}")
                return False
            
            self.log_debug(f"Docker version: {result.stdout.strip()}")
            return True
        except subprocess.TimeoutExpired:
            self.log_error("Docker command timed out. Docker daemon might not be running.")
            return False
        except Exception as e:
            self.log_error(f"Error checking Docker installation: {str(e)}")
            return False
        
    def _build_docker_command(self) -> str:
        """
        Build the Docker command string based on the configuration.
        
        Returns:
            The Docker command string
        """
        cmd_parts = ["docker", "run", "-i", "--rm"]
        
        # Add container name for easier debugging
        cmd_parts.extend(["--name", self.container_name])
        
        # Add network if specified
        if self.network_name:
            cmd_parts.extend(["--network", self.network_name])
        
        # Add mount if specified
        if self.mount_path:
            # Ensure the mount path exists and is absolute
            mount_path = os.path.abspath(self.mount_path)
            os.makedirs(mount_path, exist_ok=True)
            
            # Make the mount path readable and writable
            os.chmod(mount_path, 0o755)
            
            # Use a more reliable mounting approach
            cmd_parts.extend(["-v", f"{mount_path}:{self.container_path}"])
        
        # Add environment variables
        env_vars = self.env_vars.copy()
        if self.protocol_version:
            env_vars["MCP_PROTOCOL_VERSION"] = self.protocol_version
        
        # Debug mode environment variable
        if self.debug:
            env_vars["MCP_DEBUG"] = "true"
            
        for key, value in env_vars.items():
            cmd_parts.extend(["--env", f"{key}={value}"])
        
        # Add the image
        cmd_parts.append(self.docker_image)
        
        # Convert to string
        docker_cmd = " ".join(cmd_parts)
        self.log_debug(f"Docker command: {docker_cmd}")
        return docker_cmd
    
    def start(self) -> bool:
        """
        Start the Docker container and establish the STDIO connection.
        
        Returns:
            True if started successfully, False otherwise
        """
        # Ensure Docker network exists if specified
        if self.network_name and not self._ensure_network_exists():
            self.log_error(f"Failed to ensure Docker network '{self.network_name}' exists")
            return False
            
        # Pull the Docker image to ensure we have the latest version
        if not self._ensure_image_exists():
            self.log_error(f"Failed to ensure Docker image '{self.docker_image}' exists")
            return False
        
        # Start the container via parent class
        start_time = time.time()
        success = super().start()
        
        if success:
            self.log_debug(f"Docker container started in {time.time() - start_time:.2f} seconds")
            
            # Get the container ID for better cleanup
            self._get_container_id()
        else:
            self.log_error("Failed to start Docker container")
        
        return success
    
    def _get_container_id(self) -> Optional[str]:
        """
        Get the container ID for the running container.
        
        Returns:
            The container ID or None if not found
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"name={self.container_name}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.container_id = result.stdout.strip()
                self.log_debug(f"Container ID: {self.container_id}")
                return self.container_id
        except Exception as e:
            self.log_error(f"Error getting container ID: {str(e)}")
        
        return None
    
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
    
    def _ensure_image_exists(self) -> bool:
        """
        Ensure the Docker image exists locally, pulling it if necessary.
        
        Returns:
            True if the image exists or was pulled successfully, False otherwise
        """
        try:
            # Check if image exists
            result = subprocess.run(
                ["docker", "image", "inspect", self.docker_image],
                capture_output=True,
                text=True
            )
            
            # If image doesn't exist, pull it
            if result.returncode != 0:
                self.log_debug(f"Pulling Docker image: {self.docker_image}")
                pull_result = subprocess.run(
                    ["docker", "pull", self.docker_image],
                    capture_output=True,
                    text=True
                )
                
                if pull_result.returncode != 0:
                    self.log_error(f"Failed to pull Docker image: {pull_result.stderr}")
                    return False
                    
                self.log_debug(f"Successfully pulled Docker image: {self.docker_image}")
            else:
                self.log_debug(f"Using existing Docker image: {self.docker_image}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Error ensuring Docker image exists: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the Docker container and clean up resources.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        # First try to stop the container gracefully
        if self.container_id:
            try:
                self.log_debug(f"Stopping container {self.container_id}...")
                stop_result = subprocess.run(
                    ["docker", "stop", "--time", "5", self.container_id],
                    capture_output=True,
                    text=True
                )
                
                if stop_result.returncode == 0:
                    self.log_debug(f"Container stopped successfully")
                else:
                    self.log_error(f"Failed to stop container: {stop_result.stderr}")
                    
                    # Try to force kill as a last resort
                    self.log_debug(f"Attempting to force kill container {self.container_id}...")
                    kill_result = subprocess.run(
                        ["docker", "kill", self.container_id],
                        capture_output=True,
                        text=True
                    )
                    
                    if kill_result.returncode == 0:
                        self.log_debug(f"Container killed successfully")
                    else:
                        self.log_error(f"Failed to kill container: {kill_result.stderr}")
            except Exception as e:
                self.log_error(f"Error stopping container: {str(e)}")
        
        # Then use the parent class's stop method to clean up process resources
        return super().stop()
    
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
            self.log_debug(f"Preparing test files in {mount_path}")
            
            for file_config in test_files_config:
                file_path = mount_path / file_config.get("path", "")
                content = file_config.get("content", "")
                
                # Create parent directories if needed
                os.makedirs(file_path.parent, exist_ok=True)
                
                # Make directories readable/writable by the container
                for parent in file_path.parents:
                    if parent.is_relative_to(mount_path):
                        try:
                            os.chmod(parent, 0o755)
                        except Exception as e:
                            self.log_error(f"Error setting permissions on {parent}: {str(e)}")
                
                # Write the file
                self.log_debug(f"Writing file: {file_path}")
                with open(file_path, 'w') as f:
                    f.write(content)
                
                # Make file readable/writable by the container
                try:
                    os.chmod(file_path, 0o644)
                except Exception as e:
                    self.log_error(f"Error setting permissions on {file_path}: {str(e)}")
                    
                self.log_debug(f"Created test file: {file_path}")
                
            return True
            
        except Exception as e:
            self.log_error(f"Error preparing test files: {str(e)}")
            return False

    def get_container_logs(self) -> str:
        """
        Get the logs from the Docker container.
        
        Returns:
            The container logs as a string
        """
        if not self.container_id:
            return "No container ID available"
            
        try:
            result = subprocess.run(
                ["docker", "logs", self.container_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting container logs: {result.stderr}"
        except Exception as e:
            return f"Exception getting container logs: {str(e)}" 