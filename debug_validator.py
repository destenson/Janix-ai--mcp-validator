#!/usr/bin/env python3
"""
Debug script for the MCP validator's STDIO transport
"""

import os
import sys
import json
import logging
import subprocess
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("debug_validator")

# Read the validator's STDIO transport
def read_transport_code():
    try:
        transport_file = Path("tests/transports/stdio_transport.py")
        if transport_file.exists():
            logger.info(f"Reading transport code from {transport_file}")
            with open(transport_file, "r") as f:
                return f.read()
        else:
            logger.warning(f"Transport file not found: {transport_file}")
            return None
    except Exception as e:
        logger.error(f"Error reading transport code: {e}")
        return None

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

def main():
    logger.info("Starting debug session")
    
    # Display transport code if available
    transport_code = read_transport_code()
    if transport_code:
        logger.info("Found transport code")
    
    # Start the STDIO server process
    cmd = ["python", "docker/stdio_server.py"]
    logger.info(f"Starting server with command: {cmd}")
    
    env = os.environ.copy()
    env["MCP_BASE_DIR"] = str(Path(__file__).parent / "test_data")
    env["MCP_DEBUG"] = "true"
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    logger.info(f"Server process started with PID: {process.pid}")
    
    # Give the server time to initialize
    time.sleep(0.1)
    
    # Send the initialize request
    init_request_str = json.dumps(INITIALIZE_REQUEST)
    logger.info(f"Sending request: {init_request_str}")
    process.stdin.write(init_request_str + "\n")
    process.stdin.flush()
    
    # Read the response with timeout
    start_time = time.time()
    timeout = 5  # seconds
    response_str = None
    
    while time.time() - start_time < timeout:
        # Check if there's data to read
        if process.stdout.readable() and process.poll() is None:
            line = process.stdout.readline().strip()
            if line:
                response_str = line
                break
        time.sleep(0.1)
    
    if response_str:
        logger.info(f"Received response: {response_str}")
        try:
            response = json.loads(response_str)
            if "result" in response:
                logger.info(f"Result: {json.dumps(response['result'], indent=2)}")
            else:
                logger.warning("No result in response")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response")
    else:
        logger.error("No response received within timeout")
    
    # Shut down the server
    logger.info("Sending shutdown request")
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
    logger.info(f"Shutdown response: {shutdown_response}")
    
    # Send exit notification
    logger.info("Sending exit notification")
    exit_notification = {
        "jsonrpc": "2.0",
        "method": "exit",
        "params": {}
    }
    process.stdin.write(json.dumps(exit_notification) + "\n")
    process.stdin.flush()
    
    # Wait for process to terminate
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server did not exit, terminating...")
        process.terminate()
    
    # Print stderr output
    stderr_output = process.stderr.read()
    if stderr_output:
        logger.info("Server stderr output:")
        for line in stderr_output.splitlines():
            logger.info(f"SERVER: {line}")
    
    logger.info("Debug session complete")

if __name__ == "__main__":
    main() 