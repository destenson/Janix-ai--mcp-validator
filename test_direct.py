#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import time

# Redirect output to a file
output_file = open("test_direct_output.txt", "w")

def log(message):
    print(message, file=output_file, flush=True)
    
log("Starting direct test of Fetch MCP server")

# Start the server process
server_cmd = "/tmp/fetch_venv/bin/python -m mcp_server_fetch"
log(f"Running command: {server_cmd}")

process = subprocess.Popen(
    server_cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    shell=True,
    bufsize=1  # Line buffered
)

log(f"Server started with PID {process.pid}")

# Allow server to start
time.sleep(1)

# Check if it's still running
if process.poll() is not None:
    log(f"ERROR: Server exited with code {process.returncode}")
    stderr = process.stderr.read()
    log(f"STDERR: {stderr}")
    sys.exit(1)

# Send initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": "init",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "TestClient",
            "version": "1.0.0"
        }
    }
}

log(f"Sending request: {json.dumps(init_request)}")
process.stdin.write(json.dumps(init_request) + "\n")
process.stdin.flush()

# Read response with timeout
start_time = time.time()
response = None
stderr_output = ""

while time.time() - start_time < 5 and not response:
    # Check for response
    if process.stdout.readable():
        line = process.stdout.readline().strip()
        if line:
            try:
                response = json.loads(line)
                log(f"Got response: {line}")
            except json.JSONDecodeError:
                log(f"Non-JSON response: {line}")
    
    # Check for stderr
    if process.stderr.readable():
        line = process.stderr.readline().strip()
        if line:
            stderr_output += line + "\n"
            log(f"STDERR: {line}")
    
    # Check if server died
    if process.poll() is not None:
        log(f"Server exited with code {process.returncode}")
        remaining_stderr = process.stderr.read()
        if remaining_stderr:
            log(f"Final stderr: {remaining_stderr}")
        break
        
    time.sleep(0.1)

if not response:
    log("No response received!")
    if stderr_output:
        log(f"Stderr output: {stderr_output}")
    else:
        # Try one last read of stderr
        stderr = process.stderr.read()
        if stderr:
            log(f"Final stderr: {stderr}")
else:
    log("Test passed!")
    
# Cleanup
try:
    process.terminate()
    process.wait(timeout=2)
except subprocess.TimeoutExpired:
    process.kill()
    process.wait()
    
log("Test completed")
output_file.close() 