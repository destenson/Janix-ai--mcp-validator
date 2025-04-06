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
import traceback

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

def run_direct_test(server_command, debug=False):
    """Run a direct test using the STDIO transport directly, bypassing pytest."""
    print("Attempting direct STDIO test...")
    
    # Start the server as a subprocess
    print(f"Starting server with command: {server_command}")
    try:
        server_process = subprocess.Popen(
            server_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1  # Line buffered
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        if server_process.poll() is not None:
            print(f"Server failed to start, exit code: {server_process.returncode}")
            stderr = server_process.stderr.read().decode('utf-8')
            print(f"Server error output: {stderr}")
            return False
        
        # Import the test_base module to manually set the server process
        try:
            print("Attempting to import test_base module...")
            
            # Try to directly import set_server_process
            try:
                sys.path.insert(0, os.getcwd())
                from tests.test_base import set_server_process
                print("Successfully imported set_server_process")
                set_server_process(server_process)
                print("Successfully set server process")
            except ImportError as e:
                print(f"Could not import set_server_process: {e}")
                try:
                    # Debugging: list the test directory
                    print(f"Contents of ./tests directory:")
                    if os.path.exists("./tests"):
                        print(subprocess.check_output(["ls", "-la", "./tests"]).decode('utf-8'))
                    else:
                        print("./tests directory does not exist")
                    
                    # Try finding the test_base.py file
                    find_output = subprocess.check_output(["find", ".", "-name", "test_base.py"]).decode('utf-8')
                    print(f"Found test_base.py at: {find_output}")
                    
                    # If we found it, try importing it directly
                    if find_output:
                        base_path = find_output.strip().split("\n")[0]
                        base_dir = os.path.dirname(base_path)
                        sys.path.insert(0, os.path.dirname(base_dir))
                        module_name = f"{os.path.basename(base_dir)}.test_base"
                        print(f"Trying to import {module_name}")
                        
                        # Create a variable in the global namespace
                        import importlib
                        test_base = importlib.import_module(module_name)
                        test_base.set_server_process(server_process)
                        print("Successfully set server process using alternative method")
                except Exception as inner_e:
                    print(f"Error during alternative import: {inner_e}")
                    
            # Indicate that we have the server process ready
            os.environ["MCP_SERVER_PROCESS_READY"] = "1"
            
        except Exception as e:
            print(f"Error setting up server process: {e}")
            traceback.print_exc()
            server_process.terminate()
            return False
            
        return True
        
    except Exception as e:
        print(f"Error starting server process: {e}")
        traceback.print_exc()
        return False

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
    
    # First try direct STDIO testing to debug
    if args.debug:
        if run_direct_test(server_cmd, debug=True):
            print("Direct STDIO test setup successful")
        else:
            print("Direct STDIO test setup failed")
    
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