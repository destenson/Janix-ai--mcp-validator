#!/usr/bin/env python3
"""
MCP STDIO Test Wrapper

This script provides a wrapper to correctly configure STDIO testing with mcp_validator.py.
It properly sets up environment variables and server process configuration.
"""

import os
import sys
import subprocess
import argparse
import time
import signal
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='STDIO test wrapper for mcp_validator.py')
    parser.add_argument('--protocol-version', '-v', 
                      default=os.environ.get("MCP_PROTOCOL_VERSION", "2025-03-26"),
                      choices=["2024-11-05", "2025-03-26"],
                      help='MCP protocol version to test against')
    parser.add_argument('--docker-image', 
                      default=os.environ.get("MCP_DOCKER_IMAGE", "mcp/filesystem"),
                      help='Docker image to use for testing (default: mcp/filesystem)')
    parser.add_argument('--network-name',
                      default=os.environ.get("MCP_NETWORK_NAME", "mcp-test-network"),
                      help='Docker network name (default: mcp-test-network)')
    parser.add_argument('--mount-dir', '-m', 
                      help='Directory to mount in the Docker container (defaults to test_data/files)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug output')
    parser.add_argument('--report', 
                      default="./mcp-stdio-report.html",
                      help='Path to save the test report')
    parser.add_argument('--format', 
                      default="html", 
                      choices=["html", "json", "markdown"],
                      help='Report format')
    parser.add_argument('--test-modules', 
                      default="base",
                      help='Comma-separated list of test modules to run (base,resources,tools,prompts,utilities)')
    return parser.parse_args()

def setup_docker_network(network_name):
    """Create a Docker network if it doesn't exist."""
    try:
        # Check if network exists
        result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Creating Docker network: {network_name}")
            subprocess.run(
                ["docker", "network", "create", network_name],
                check=True
            )
        else:
            print(f"Using existing Docker network: {network_name}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Docker network: {e}")
        return False

def prepare_mount_directory(mount_dir):
    """Prepare the mount directory for testing."""
    os.makedirs(mount_dir, exist_ok=True)
    
    test_file = Path(mount_dir) / "test.txt"
    if not test_file.exists():
        with open(test_file, 'w') as f:
            f.write("This is a test file for MCP filesystem server testing.\n")
    
    return mount_dir

def find_mcp_validator():
    """Find the mcp_validator.py script."""
    # Try different possible locations
    possible_paths = [
        Path("mcp_validator.py"),  # Current directory
        Path("../mcp_validator.py"),  # Parent directory
        Path("../mcp-protocol-validator/mcp_validator.py")  # Another common location
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # If we can't find it, search for it
    try:
        result = subprocess.run(
            ["find", ".", "-name", "mcp_validator.py"],
            capture_output=True,
            text=True,
            check=True
        )
        paths = result.stdout.strip().split("\n")
        if paths and paths[0]:
            return paths[0]
    except subprocess.CalledProcessError:
        pass
    
    # Default to this location and hope it works
    return "mcp_validator.py"

def main():
    """Main function to run the STDIO test wrapper."""
    args = parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent.absolute()
    mount_dir = args.mount_dir if args.mount_dir else script_dir.parent / "test_data" / "files"
    
    # Setup Docker network
    if not setup_docker_network(args.network_name):
        print("Failed to set up Docker network. Aborting tests.")
        return 1
    
    # Prepare mount directory
    prepare_mount_directory(mount_dir)
    
    # Define the server command to use for Docker
    # Modified to mount directly to /projects instead of /projects/files
    server_cmd = (
        f"docker run -i --rm "
        f"--network {args.network_name} "
        f"--mount type=bind,src={mount_dir},dst=/projects "
        f"--env MCP_PROTOCOL_VERSION={args.protocol_version} "
        f"{args.docker_image} /projects"
    )
    
    # Find the path to mcp_validator.py
    validator_path = find_mcp_validator()
    
    # Run mcp_validator.py with the proper server command
    cmd = [
        "python", validator_path, "test",
        # Use a dummy URL (required by the script but not actually used for STDIO)
        "--url", "http://dummy-not-used", 
        "--server-command", server_cmd,
        "--report", args.report,
        "--format", args.format,
        "--version", args.protocol_version,
        "--stdio-only"  # Important flag
    ]
    
    # Add debug flag if specified
    if args.debug:
        cmd.append("--debug")
    
    # Add test modules if specified
    if args.test_modules:
        cmd.extend(["--test-modules", args.test_modules])
    
    # Set environment variables for STDIO testing
    test_env = os.environ.copy()
    test_env["MCP_TRANSPORT_TYPE"] = "stdio"
    test_env["MCP_DEBUG_STDIO"] = "1" if args.debug else "0"
    test_env["MCP_STDIO_ONLY"] = "1"
    test_env["MCP_PROTOCOL_VERSION"] = args.protocol_version
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        # Run the mcp_validator.py script with the proper setup
        subprocess.run(cmd, env=test_env, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(main()) 