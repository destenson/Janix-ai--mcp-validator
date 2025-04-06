#!/usr/bin/env python3
"""
MCP STDIO Direct Test Script

This script provides a direct test of STDIO transport functionality with the MCP filesystem server,
without using pytest for simplified debugging.
"""

import os
import sys
import subprocess
import json
import time
import signal
from pathlib import Path

print("DEBUG: Script starting")
sys.stdout.flush()

def setup_docker_network(network_name="mcp-test-network"):
    """Create a Docker network if it doesn't exist."""
    print("DEBUG: Setting up Docker network")
    sys.stdout.flush()
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
    print(f"DEBUG: Preparing mount directory: {mount_dir}")
    sys.stdout.flush()
    os.makedirs(mount_dir, exist_ok=True)
    
    test_file = Path(mount_dir) / "test.txt"
    if not test_file.exists():
        with open(test_file, 'w') as f:
            f.write("This is a test file for MCP filesystem server testing.\n")
    
    return mount_dir

def start_server(docker_image="mcp/filesystem", network_name="mcp-test-network", 
                protocol_version="2025-03-26", mount_dir=None):
    """Start the MCP server in Docker."""
    print("DEBUG: Starting server")
    sys.stdout.flush()
    if mount_dir is None:
        mount_dir = Path(__file__).parent.parent / "test_data" / "files"
        os.makedirs(mount_dir, exist_ok=True)
    
    prepare_mount_directory(mount_dir)
    
    server_cmd = (
        f"docker run -i --rm "
        f"--network {network_name} "
        f"--mount type=bind,src={mount_dir},dst=/projects "
        f"--env MCP_PROTOCOL_VERSION={protocol_version} "
        f"{docker_image} /projects"
    )
    
    print(f"Starting server with command: {server_cmd}")
    sys.stdout.flush()
    
    server_process = subprocess.Popen(
        server_cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,  # Line buffered
        text=False  # Binary mode for handling potential binary data
    )
    
    # Give it a moment to start
    print("DEBUG: Waiting for server to start")
    sys.stdout.flush()
    time.sleep(2)
    
    # Check if started successfully
    if server_process.poll() is not None:
        print(f"Server failed to start, exit code: {server_process.returncode}")
        stderr = server_process.stderr.read().decode('utf-8')
        print(f"Server error output: {stderr}")
        return None
    
    # Start a thread to read stderr
    import threading
    
    def read_stderr():
        while server_process.poll() is None:
            try:
                line = server_process.stderr.readline()
                if line:
                    print(f"[SERVER] {line.decode('utf-8').strip()}")
                    sys.stdout.flush()
            except Exception as e:
                print(f"Error reading server stderr: {e}")
                break
    
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()
    
    return server_process

def send_request(server_process, request):
    """Send a request to the server process via STDIO."""
    print(f"DEBUG: Sending request")
    sys.stdout.flush()
    if server_process.poll() is not None:
        print(f"Server process is no longer running, exit code: {server_process.returncode}")
        return None
    
    # Add newline to the request
    request_str = json.dumps(request) + "\n"
    print(f"Sending request: {request_str.strip()}")
    sys.stdout.flush()
    
    # Send the request
    server_process.stdin.write(request_str.encode('utf-8'))
    server_process.stdin.flush()
    
    # Read the response
    print("DEBUG: Waiting for response")
    sys.stdout.flush()
    response_line = server_process.stdout.readline()
    if not response_line:
        print("No response received")
        return None
    
    response_str = response_line.decode('utf-8').strip()
    print(f"Received response: {response_str}")
    sys.stdout.flush()
    
    try:
        response = json.loads(response_str)
        return response
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response: {response_str}")
        return None

def run_basic_tests(server_process):
    """Run some basic tests against the server."""
    print("DEBUG: Running basic tests")
    sys.stdout.flush()
    if server_process is None:
        print("No server process provided")
        return False
    
    # Test 1: Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": "test_init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "MCPDirectTest",
                "version": "0.1.0"
            }
        }
    }
    
    init_response = send_request(server_process, init_request)
    if not init_response:
        print("Initialization failed - no response")
        return False
    
    print(f"Initialization response: {json.dumps(init_response, indent=2)}")
    sys.stdout.flush()
    
    # Check if the response has the expected fields
    if "result" not in init_response:
        print("Initialization failed - no result field")
        return False
    
    # Test 2: Send 'initialized' notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    # No response expected for notifications
    send_request(server_process, initialized_notification)
    
    # Test 3: List available tools
    tools_request = {
        "jsonrpc": "2.0",
        "id": "test_tools",
        "method": "tools/list",
        "params": {}
    }
    
    tools_response = send_request(server_process, tools_request)
    if not tools_response:
        print("Tools list failed - no response")
        return False
    
    print(f"Tools list response: {json.dumps(tools_response, indent=2)}")
    sys.stdout.flush()
    
    # Test 4: List directory
    list_request = {
        "jsonrpc": "2.0",
        "id": "test_list",
        "method": "filesystem/list_directory",
        "params": {
            "path": "/projects"
        }
    }
    
    list_response = send_request(server_process, list_request)
    if not list_response:
        print("List directory failed - no response")
        return False
    
    print(f"List directory response: {json.dumps(list_response, indent=2)}")
    sys.stdout.flush()
    
    print("All basic tests completed successfully")
    return True

def main():
    """Main function to run the STDIO direct test."""
    print("DEBUG: In main function")
    sys.stdout.flush()
    # Setup Docker network
    if not setup_docker_network():
        print("Failed to set up Docker network. Aborting tests.")
        return 1
    
    # Start the server
    server_process = start_server()
    if not server_process:
        print("Failed to start server. Aborting tests.")
        return 1
    
    try:
        # Run the tests
        success = run_basic_tests(server_process)
        
        if success:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Tests failed!")
            return 1
    finally:
        # Clean up the server process
        if server_process:
            print("Stopping server...")
            try:
                server_process.terminate()
                time.sleep(1)
                if server_process.poll() is None:
                    server_process.kill()
            except Exception as e:
                print(f"Error stopping server: {e}")

print("DEBUG: About to call main")
sys.stdout.flush()
if __name__ == "__main__":
    sys.exit(main()) 