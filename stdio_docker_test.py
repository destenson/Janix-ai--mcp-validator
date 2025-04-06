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
from typing import Dict, Any, Optional, List, Tuple

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

class STDIODockerTester:
    """Test an MCP STDIO server running in Docker"""
    
    def __init__(self, docker_image: str, mount_path: str, protocol_version: str = "2025-03-26", debug: bool = False):
        self.docker_image = docker_image
        self.mount_path = os.path.abspath(mount_path)
        self.protocol_version = protocol_version
        self.debug = debug
        self.request_id = 0
        self.process = None
        
    def start_server(self) -> None:
        """Start the Docker server process"""
        # Prepare the docker command
        cmd = [
            "docker", "run", "-i", "--rm",
            "--mount", f"type=bind,src={self.mount_path},dst=/projects",
            self.docker_image, "/projects"
        ]
        
        if self.debug:
            print(f"Starting Docker container with command: {' '.join(cmd)}")
            
        # Start the Docker container with STDIO
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Use binary mode for precise control
        )
        
    def stop_server(self) -> None:
        """Stop the Docker server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            
    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the server and get the response"""
        if not self.process:
            raise RuntimeError("Server not started")
            
        # Create the request
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": f"test_{self.request_id}",
            "method": method,
            "params": params
        }
        
        # Send the request
        request_json = json.dumps(request) + "\n"
        if self.debug:
            print(f"Sending request: {request_json.strip()}")
            
        self.process.stdin.write(request_json.encode('utf-8'))
        self.process.stdin.flush()
        
        # Read the response
        response_json = self.process.stdout.readline().decode('utf-8')
        if self.debug:
            print(f"Received response: {response_json.strip()}")
            
        response = json.loads(response_json)
        return response
    
    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a notification to the server (no response expected)"""
        if not self.process:
            raise RuntimeError("Server not started")
            
        # Create the notification
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        # Send the notification
        notification_json = json.dumps(notification) + "\n"
        if self.debug:
            print(f"Sending notification: {notification_json.strip()}")
            
        self.process.stdin.write(notification_json.encode('utf-8'))
        self.process.stdin.flush()
        
    def initialize(self) -> Dict[str, Any]:
        """Initialize the server"""
        init_params = {
            "protocolVersion": self.protocol_version,
            "capabilities": {
                "roots": {
                    "listChanged": True
                }
            },
            "clientInfo": {
                "name": "STDIODockerTester",
                "version": "1.0.0"
            }
        }
        
        response = self._send_request("initialize", init_params)
        
        # Send the initialized notification
        self._send_notification("initialized", {})
        
        return response
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get the list of available tools"""
        response = self._send_request("tools/list", {})
        return response.get("result", [])
    
    def list_directory(self, directory: str) -> List[Dict[str, Any]]:
        """List contents of a directory"""
        response = self._send_request("filesystem/list_directory", {"directory": directory})
        return response.get("result", [])
    
    def read_file(self, file_path: str) -> str:
        """Read the contents of a file"""
        response = self._send_request("filesystem/read_file", {"file": file_path})
        return response.get("result", {}).get("content", "")
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file"""
        response = self._send_request("filesystem/write_file", {
            "file": file_path,
            "content": content
        })
        return "result" in response
    
    def run_simple_test(self) -> Tuple[bool, str]:
        """Run a simple test sequence to verify server functionality"""
        try:
            # Start the server
            self.start_server()
            
            # Initialize
            init_response = self.initialize()
            if "error" in init_response:
                return False, f"Initialization failed: {init_response['error']}"
                
            protocol_version = init_response.get("result", {}).get("protocolVersion")
            if protocol_version != self.protocol_version:
                print(f"Warning: Server responded with protocol version {protocol_version}, requested {self.protocol_version}")
            
            # Get tools list
            tools = self.get_tools_list()
            if not tools:
                return False, "Failed to get tools list or list is empty"
                
            # Test listing directory
            files = self.list_directory("/projects")
            if not isinstance(files, list):
                return False, "Failed to list directory"
                
            # Test writing a file
            test_content = "This is a test file created by STDIODockerTester"
            write_success = self.write_file("/projects/test_file.txt", test_content)
            if not write_success:
                return False, "Failed to write file"
                
            # Test reading a file
            read_content = self.read_file("/projects/test_file.txt")
            if read_content != test_content:
                return False, f"File content doesn't match: expected '{test_content}', got '{read_content}'"
            
            return True, "All tests passed successfully"
            
        except Exception as e:
            return False, f"Test failed with error: {str(e)}"
        finally:
            self.stop_server()

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