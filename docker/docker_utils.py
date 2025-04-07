"""
Docker utilities for the MCP protocol validator.

This module provides utility functions for managing Docker containers and networks
for testing MCP servers in an isolated environment.
"""

import os
import subprocess
import time
import json
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


def ensure_network_exists(network_name: str, debug: bool = False) -> bool:
    """
    Ensure that a Docker network exists, creating it if necessary.
    
    Args:
        network_name: The name of the Docker network
        debug: Whether to enable debug output
        
    Returns:
        True if the network exists or was created, False otherwise
    """
    try:
        # Check if network exists
        if debug:
            print(f"Checking if Docker network '{network_name}' exists...")
            
        result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            if debug:
                print(f"Creating Docker network: {network_name}")
                
            create_result = subprocess.run(
                ["docker", "network", "create", network_name],
                capture_output=True,
                text=True
            )
            
            if create_result.returncode != 0:
                print(f"Failed to create Docker network: {create_result.stderr}")
                return False
                
            if debug:
                print(f"Created Docker network: {network_name}")
        else:
            if debug:
                print(f"Using existing Docker network: {network_name}")
                
        return True
        
    except Exception as e:
        print(f"Error ensuring Docker network exists: {str(e)}")
        return False


def prepare_test_files(test_dir: str, debug: bool = False) -> str:
    """
    Prepare test files for the filesystem server.
    
    Args:
        test_dir: The directory to create test files in
        debug: Whether to enable debug output
        
    Returns:
        The absolute path to the test directory
    """
    # Ensure absolute path
    test_dir = os.path.abspath(test_dir)
    
    # Create the directory if it doesn't exist
    os.makedirs(test_dir, exist_ok=True)
    
    if debug:
        print(f"Preparing test files in {test_dir}")
    
    # Create a test file
    test_file = Path(test_dir) / "test.txt"
    with open(test_file, 'w') as f:
        f.write("This is a test file for MCP protocol validator.\n")
    
    # Create a subdirectory for nested path testing
    nested_dir = Path(test_dir) / "nested"
    os.makedirs(nested_dir, exist_ok=True)
    
    # Create file in nested directory
    nested_file = nested_dir / "nested_file.txt"
    with open(nested_file, 'w') as f:
        f.write("This is a nested file for testing directory traversal.\n")
    
    # Create a test JSON file
    json_file = Path(test_dir) / "test.json"
    with open(json_file, 'w') as f:
        json.dump({
            "test": "value",
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"}
            }
        }, f, indent=2)
    
    # Create a larger test file
    large_file = Path(test_dir) / "large.txt"
    with open(large_file, 'w') as f:
        for i in range(1000):
            f.write(f"Line {i} of large test file.\n")
    
    # Create a binary file
    binary_file = Path(test_dir) / "binary.bin"
    with open(binary_file, 'wb') as f:
        f.write(os.urandom(1024))  # 1KB of random data
    
    if debug:
        print(f"Created test files: {test_file}, {nested_file}, {json_file}, {large_file}, {binary_file}")
    
    return test_dir


def start_stdio_docker_server(docker_image: str, 
                             network_name: str, 
                             mount_dir: str, 
                             protocol_version: str,
                             env_vars: Optional[Dict[str, str]] = None,
                             container_path: str = "/projects",
                             debug: bool = False) -> subprocess.Popen:
    """
    Start a Docker container with an MCP server using STDIO transport.
    
    Args:
        docker_image: The Docker image to use
        network_name: The Docker network to use
        mount_dir: The local directory to mount
        protocol_version: The MCP protocol version to use
        env_vars: Additional environment variables to set
        container_path: The path to mount to in the container
        debug: Whether to enable debug output
        
    Returns:
        The subprocess.Popen object for the Docker container
    """
    if debug:
        print(f"Starting Docker STDIO server with image: {docker_image}")
        print(f"Protocol version: {protocol_version}")
        print(f"Mount: {mount_dir} -> {container_path}")
    
    # Ensure the mount directory exists
    mount_dir = os.path.abspath(mount_dir)
    os.makedirs(mount_dir, exist_ok=True)
    
    # Build the Docker command
    cmd = [
        "docker", "run", "-i", "--rm", 
        "--network", network_name,
        "--mount", f"type=bind,src={mount_dir},dst={container_path}",
        "--env", f"MCP_PROTOCOL_VERSION={protocol_version}"
    ]
    
    # Add additional environment variables
    if env_vars:
        for key, value in env_vars.items():
            cmd.extend(["--env", f"{key}={value}"])
    
    # Add the image and command
    cmd.append(docker_image)
    cmd.append(container_path)
    
    if debug:
        cmd_str = " ".join(cmd)
        print(f"Docker command: {cmd_str}")
    
    # Start the Docker container
    server_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        start_new_session=True
    )
    
    # Give the server a moment to start up
    if debug:
        print("Waiting for server to initialize...")
    time.sleep(2)
    
    return server_process


def start_http_docker_server(docker_image: str,
                            network_name: str,
                            mount_dir: Optional[str] = None,
                            port: int = 8080,
                            protocol_version: str = "2025-03-26",
                            env_vars: Optional[Dict[str, str]] = None,
                            container_path: str = "/projects",
                            debug: bool = False) -> Tuple[subprocess.Popen, str]:
    """
    Start a Docker container with an MCP server using HTTP transport.
    
    Args:
        docker_image: The Docker image to use
        network_name: The Docker network to use
        mount_dir: The local directory to mount (optional)
        port: The port to expose the HTTP server on
        protocol_version: The MCP protocol version to use
        env_vars: Additional environment variables to set
        container_path: The path to mount to in the container
        debug: Whether to enable debug output
        
    Returns:
        A tuple of (subprocess.Popen, URL) for the Docker container
    """
    if debug:
        print(f"Starting Docker HTTP server with image: {docker_image}")
        print(f"Protocol version: {protocol_version}")
        if mount_dir:
            print(f"Mount: {mount_dir} -> {container_path}")
    
    # Generate a unique container name
    container_name = f"mcp-http-server-{int(time.time())}"
    
    # Build the Docker command
    cmd = [
        "docker", "run", "--rm", "-d",
        "--name", container_name,
        "--network", network_name,
        "-p", f"{port}:8080",
        "--env", f"MCP_PROTOCOL_VERSION={protocol_version}",
        "--env", "MCP_TRANSPORT=http"
    ]
    
    # Add mount if specified
    if mount_dir:
        mount_dir = os.path.abspath(mount_dir)
        os.makedirs(mount_dir, exist_ok=True)
        cmd.extend(["--mount", f"type=bind,src={mount_dir},dst={container_path}"])
    
    # Add additional environment variables
    if env_vars:
        for key, value in env_vars.items():
            cmd.extend(["--env", f"{key}={value}"])
    
    # Add the image
    cmd.append(docker_image)
    
    if debug:
        cmd_str = " ".join(cmd)
        print(f"Docker command: {cmd_str}")
    
    # Start the Docker container
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Failed to start Docker container: {result.stderr}")
    
    # Get the container ID
    container_id = result.stdout.strip()
    
    # Start a process to capture container logs
    log_process = subprocess.Popen(
        ["docker", "logs", "-f", container_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Wait for the container to start up
    if debug:
        print("Waiting for HTTP server to initialize...")
    time.sleep(5)
    
    # Return the log process and the URL
    return log_process, f"http://localhost:{port}"


def get_container_ip(container_name: str) -> str:
    """
    Get the IP address of a Docker container.
    
    Args:
        container_name: The name of the Docker container
        
    Returns:
        The IP address of the container
    """
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to get container IP: {result.stderr}")
    
    return result.stdout.strip()


def stop_container(container_name_or_id: str, debug: bool = False) -> None:
    """
    Stop a Docker container.
    
    Args:
        container_name_or_id: The name or ID of the Docker container
        debug: Whether to enable debug output
    """
    if debug:
        print(f"Stopping Docker container: {container_name_or_id}")
    
    subprocess.run(
        ["docker", "stop", container_name_or_id],
        check=False,  # Don't raise an exception if the container doesn't exist
        capture_output=True
    )


def cleanup_process(process: subprocess.Popen, debug: bool = False) -> None:
    """
    Clean up a subprocess.
    
    Args:
        process: The subprocess.Popen object
        debug: Whether to enable debug output
    """
    if process is None:
        return
        
    try:
        if debug:
            print("Terminating process...")
            
        process.terminate()
        
        # Give it a moment to terminate gracefully
        for _ in range(3):
            if process.poll() is not None:
                break
            time.sleep(1)
        
        # If it's still running, force kill it
        if process.poll() is None:
            if debug:
                print("Force killing process...")
                
            if os.name == 'nt':
                process.kill()
            else:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    # Fallback if the process group ID is not available
                    process.kill()
                    
    except Exception as e:
        print(f"Error cleaning up process: {str(e)}") 