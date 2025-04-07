#!/usr/bin/env python3
"""
Simple direct test for STDIO server
"""

import json
import subprocess
import sys

# Test data
INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": "test-init",
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {
            "name": "TestClient",
            "version": "1.0.0"
        }
    }
}

# Start the STDIO server process
cmd = ["python", "docker/stdio_server.py"]
process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print(f"Started server with pid {process.pid}")

# Send the initialize request
init_request_str = json.dumps(INITIALIZE_REQUEST)
print(f"Sending: {init_request_str}")
process.stdin.write(init_request_str + "\n")
process.stdin.flush()

# Read the response
response_str = process.stdout.readline().strip()
print(f"Received: {response_str}")

# Parse the response
try:
    response = json.loads(response_str)
    if "result" in response:
        print("Result:", json.dumps(response["result"], indent=2))
    else:
        print("No result in response")
except json.JSONDecodeError:
    print("Invalid JSON response")

# Shut down the server
shutdown_request = {
    "jsonrpc": "2.0",
    "id": "test-shutdown",
    "method": "shutdown",
    "params": {}
}
process.stdin.write(json.dumps(shutdown_request) + "\n")
process.stdin.flush()

# Read the shutdown response
shutdown_response = process.stdout.readline().strip()
print(f"Shutdown response: {shutdown_response}")

# Send exit notification
exit_notification = {
    "jsonrpc": "2.0",
    "method": "exit",
    "params": {}
}
process.stdin.write(json.dumps(exit_notification) + "\n")
process.stdin.flush()

# Terminate if necessary
try:
    process.wait(timeout=5)
except subprocess.TimeoutExpired:
    print("Server did not exit, terminating...")
    process.terminate()

# Print any error output
stderr_output = process.stderr.read()
if stderr_output:
    print("Server stderr output:")
    print(stderr_output)

print("Test complete") 