#!/usr/bin/env python3
"""
MCP STDIO Docker Test Utility

This script runs the MCP protocol validator tests against a Docker-based
filesystem server using STDIO transport. It handles Docker setup, test execution,
and result reporting.
"""

import os
import sys
import subprocess
import time
import signal
import pytest
import argparse
import json
from pathlib import Path
import threading

# Import the test base framework
try:
    from tests.test_base import set_server_process, MCPBaseTest
except ImportError:
    def set_server_process(process):
        print("WARNING: Could not import set_server_process from test_base")
    MCPBaseTest = None

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test MCP server using STDIO transport')
    parser.add_argument('--protocol-version', '-v', 
                       default=os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05"),
                       choices=["2024-11-05", "2025-03-26"],
                       help='MCP protocol version to test against')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug output')
    parser.add_argument('--timeout', '-t', type=float, default=10.0,
                       help='Timeout for STDIO responses in seconds')
    parser.add_argument('--max-retries', '-r', type=int, default=3,
                       help='Maximum retries for broken pipes')
    parser.add_argument('--mount-dir', '-m', 
                       help='Directory to mount in the Docker container (defaults to test_data/files)')
    parser.add_argument('--docker-image', 
                       default=os.environ.get("MCP_DOCKER_IMAGE", "mcp/filesystem"),
                       help='Docker image to use for testing (default: mcp/filesystem)')
    parser.add_argument('--network-name',
                       default=os.environ.get("MCP_NETWORK_NAME", "mcp-test-network"),
                       help='Docker network name (default: mcp-test-network)')
    parser.add_argument('--run-all-tests', '-a', action='store_true',
                       help='Run all compatible tests, not just the base protocol tests')
    parser.add_argument('--report', action='store_true',
                       help='Generate HTML test report')
    parser.add_argument('--report-dir',
                       default='reports',
                       help='Directory to store HTML test reports')
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

def prepare_test_files(test_dir):
    """Prepare test files for the filesystem server."""
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a test file if it doesn't exist
    test_file = Path(test_dir) / "test.txt"
    if not test_file.exists():
        with open(test_file, 'w') as f:
            f.write("This is a test file for MCP filesystem server testing.\n")
    
    # Create a subdirectory for nested path testing
    nested_dir = Path(test_dir) / "nested"
    os.makedirs(nested_dir, exist_ok=True)
    
    # Create file in nested directory
    nested_file = nested_dir / "nested_file.txt"
    if not nested_file.exists():
        with open(nested_file, 'w') as f:
            f.write("This is a nested file for testing directory traversal.\n")
    
    # Create a test JSON file
    json_file = Path(test_dir) / "test.json"
    if not json_file.exists():
        with open(json_file, 'w') as f:
            json.dump({
                "test": "value",
                "nested": {
                    "array": [1, 2, 3],
                    "object": {"key": "value"}
                }
            }, f, indent=2)
    
    return test_dir

def start_docker_server(docker_image, network_name, mount_dir, protocol_version):
    """Start the Docker filesystem server."""
    print(f"Starting Docker filesystem server with mount at {mount_dir}")
    print(f"Docker image: {docker_image}")
    print(f"Protocol version: {protocol_version}")
    
    # Start the Docker filesystem server
    cmd = [
        "docker", "run", "-i", "--rm", 
        "--network", network_name,
        "--mount", f"type=bind,src={mount_dir},dst=/projects/files",
        "--env", f"MCP_PROTOCOL_VERSION={protocol_version}",
        docker_image, "/projects"
    ]
    
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
    print("Waiting for server to initialize...")
    time.sleep(2)
    
    return server_process

def capture_server_output(server_process):
    """Start a thread to capture server stderr output."""
    def print_server_stderr():
        for line in server_process.stderr:
            print(f"[SERVER] {line.strip()}", file=sys.stderr)
    
    stderr_thread = threading.Thread(target=print_server_stderr, daemon=True)
    stderr_thread.start()
    return stderr_thread

def cleanup_server(server_process):
    """Clean up the server process."""
    print("Stopping Docker filesystem server...")
    try:
        server_process.terminate()
        for _ in range(3):
            if server_process.poll() is not None:
                break
            time.sleep(1)
        
        if server_process.poll() is None:
            print("Force killing server process", file=sys.stderr)
            if os.name == 'nt':
                server_process.kill()
            else:
                os.killpg(os.getpgid(server_process.pid), signal.SIGKILL)
    except Exception as e:
        print(f"Error during server cleanup: {e}", file=sys.stderr)

def run_tests(args):
    """Run the tests with the specified configuration."""
    # Build pytest args
    pytest_args = ["-v"]
    
    # Skip HTTP-only tests for STDIO
    pytest_args.extend(["-m", "not http_only"])
    
    # Determine which tests to run
    if args.run_all_tests:
        # Run all compatible tests
        pytest_args.append("tests/")
    else:
        # Run only the basic protocol tests
        pytest_args.append("tests/test_base_protocol.py")
    
    # Generate HTML report if requested
    if args.report:
        os.makedirs(args.report_dir, exist_ok=True)
        report_file = f"{args.report_dir}/stdio-{args.protocol_version}-report.html"
        pytest_args.extend(["--html", report_file, "--self-contained-html"])
    
    print("\nRunning STDIO-specific tests...")
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Some tests failed (exit code: {exit_code})")
    
    if args.report and exit_code == 0:
        print(f"\nTest report generated: {args.report_dir}/stdio-{args.protocol_version}-report.html")
    
    return exit_code

def main():
    """Run the MCP protocol tests with Docker STDIO transport."""
    # Parse arguments
    args = parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent.absolute()
    test_files_dir = args.mount_dir if args.mount_dir else script_dir / "test_data" / "files"
    
    # Setup Docker network
    if not setup_docker_network(args.network_name):
        print("Failed to set up Docker network. Aborting tests.")
        return 1
    
    # Prepare test files
    prepare_test_files(test_files_dir)
    
    # Start Docker server
    server_process = start_docker_server(
        args.docker_image, 
        args.network_name, 
        test_files_dir,
        args.protocol_version
    )
    
    # Configure environment for tests
    os.environ["MCP_TRANSPORT_TYPE"] = "stdio"
    os.environ["MCP_DEBUG_STDIO"] = "1" if args.debug else "0"
    os.environ["MCP_STDIO_ONLY"] = "1"
    os.environ["MCP_PROTOCOL_VERSION"] = args.protocol_version
    os.environ["MCP_STDIO_TIMEOUT"] = str(args.timeout)
    os.environ["MCP_STDIO_MAX_RETRIES"] = str(args.max_retries)
    
    # Set the global server process
    set_server_process(server_process)
    
    # Start a thread to capture server stderr output
    capture_server_output(server_process)
    
    try:
        # Run the tests
        return run_tests(args)
    finally:
        cleanup_server(server_process)

if __name__ == "__main__":
    sys.exit(main()) 