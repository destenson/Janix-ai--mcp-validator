#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
from pathlib import Path
import threading

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.


print("Starting STDIO test")

# Check if Docker network exists
network_cmd = ["docker", "network", "inspect", "mcp-test-network"]
result = subprocess.run(network_cmd, capture_output=True, text=True)
print("Network exists:", result.returncode == 0)

# Make sure we have a test directory
test_dir = Path(__file__).parent.parent / "test_data" / "files"
os.makedirs(test_dir, exist_ok=True)
print(f"Test directory: {test_dir}")

# Create a test file if it doesn't exist
test_file = test_dir / "test.txt"
if not test_file.exists():
    with open(test_file, 'w') as f:
        f.write("This is a test file for MCP filesystem server testing.\n")
    print(f"Created test file: {test_file}")
else:
    print(f"Test file already exists: {test_file}")

# Start the Docker container
server_cmd = (
    "docker run -i --rm "
    "--network mcp-test-network "
    f"--mount type=bind,src={test_dir},dst=/projects "
    "--env MCP_PROTOCOL_VERSION=2025-03-26 "
    "mcp/filesystem /projects"
)
print(f"Starting server with command: {server_cmd}")

server_process = subprocess.Popen(
    server_cmd,
    shell=True,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=1,  # Line buffered
    text=False  # Binary mode for handling potential binary data
)

# Function to read and print the server's stderr output
def read_stderr():
    while server_process.poll() is None:
        try:
            line = server_process.stderr.readline()
            if line:
                print(f"[SERVER] {line.decode('utf-8').strip()}")
        except Exception as e:
            print(f"Error reading server stderr: {e}")
            break

# Start the stderr reader thread
stderr_thread = threading.Thread(target=read_stderr, daemon=True)
stderr_thread.start()

# Give the server time to start
print("Waiting for server to start...")
time.sleep(2)

if server_process.poll() is not None:
    print(f"Server failed to start, exit code: {server_process.returncode}")
    stderr = server_process.stderr.read().decode('utf-8')
    print(f"Server error output: {stderr}")
    sys.exit(1)

print("Server started successfully")

# Function to send a request and read the response
def send_request(request):
    request_str = json.dumps(request) + "\n"
    print(f"Sending request: {request_str.strip()}")
    
    server_process.stdin.write(request_str.encode('utf-8'))
    server_process.stdin.flush()
    
    response_line = server_process.stdout.readline()
    if not response_line:
        print("No response received")
        return None
    
    response_str = response_line.decode('utf-8').strip()
    print(f"Received response: {response_str}")
    
    try:
        return json.loads(response_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        print(f"Raw response: {response_str}")
        return None

# Run a test to initialize the connection
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

print("Sending initialization request...")
init_response = send_request(init_request)

if init_response:
    print("Initialization successful")
    print("Response:", json.dumps(init_response, indent=2))
else:
    print("Initialization failed")

# Send initialized notification (no response expected)
init_notification = {
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {}
}
print("Sending initialized notification...")
send_request(init_notification)

# Get list of available tools
tools_request = {
    "jsonrpc": "2.0",
    "id": "list_tools",
    "method": "tools/list",
    "params": {}
}
print("Requesting available tools...")
tools_response = send_request(tools_request)

if tools_response:
    print("Tools list successful")
    print("Available tools:", json.dumps(tools_response, indent=2))
else:
    print("Failed to get tools list")

# Clean up by stopping the server
print("Stopping server...")
server_process.terminate()
time.sleep(1)
if server_process.poll() is None:
    print("Server still running, force killing...")
    server_process.kill()

print("Test completed") 