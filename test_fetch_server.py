#!/usr/bin/env python3
import subprocess
import json
import time
import sys
import os

def main():
    print("Starting Fetch MCP server test")
    
    # Print environment information
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Start the server process with full virtual env path
    venv_python = "/tmp/fetch_venv/bin/python"
    if os.path.exists(venv_python):
        server_cmd = f"{venv_python} -m mcp_server_fetch"
    else:
        server_cmd = "python -m mcp_server_fetch"
        
    print(f"Using command: {server_cmd}")
    
    # Run with shell=True to properly use environment
    process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        shell=True,
        env=os.environ.copy()
    )
    
    print(f"Server process started with PID {process.pid}")
    
    try:
        # Wait a bit for server to initialize
        time.sleep(1)
        
        # Check if process is still running
        if process.poll() is not None:
            print(f"ERROR: Server process exited with code {process.returncode}")
            stderr = process.stderr.read()
            print(f"Server error output: {stderr}")
            return 1
        
        # Send initialize request
        print("Sending initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-test",
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
        
        # Convert request to JSON and add newline
        request_str = json.dumps(init_request) + "\n"
        print(f"Request: {request_str.strip()}")
        
        # Send the request
        process.stdin.write(request_str)
        process.stdin.flush()
        
        # Read the response with a timeout
        start_time = time.time()
        response_str = ""
        stderr_output = ""
        
        while time.time() - start_time < 5:
            # Check if there's data to read from stdout
            if process.stdout.readable():
                line = process.stdout.readline().strip()
                if line:
                    response_str = line
                    break
            
            # Check if there's error output
            if process.stderr.readable():
                stderr_line = process.stderr.readline().strip()
                if stderr_line:
                    stderr_output += stderr_line + "\n"
                    print(f"STDERR: {stderr_line}")
            
            # Check if process is still running
            if process.poll() is not None:
                print(f"ERROR: Server process exited with code {process.returncode}")
                stderr = process.stderr.read()
                if stderr:
                    stderr_output += stderr + "\n"
                    print(f"Server error output: {stderr}")
                return 1
                
            # Short delay
            time.sleep(0.1)
        
        if not response_str:
            print("ERROR: No response received from server")
            
            # Check for pending stderr output
            stderr = process.stderr.read()
            if stderr:
                stderr_output += stderr + "\n"
                print(f"Server error output: {stderr}")
                
            if not stderr_output:
                print("No error output either - server might not be responding to stdio")
                
            return 1
        
        print(f"Response: {response_str}")
        
        # Parse the response
        try:
            response = json.loads(response_str)
            print("Successfully parsed response")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON response: {e}")
            return 1
        
        # Send initialized notification
        print("\nSending initialized notification...")
        notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        notification_str = json.dumps(notification) + "\n"
        print(f"Notification: {notification_str.strip()}")
        
        process.stdin.write(notification_str)
        process.stdin.flush()
        
        # No response expected for notification, wait a bit
        time.sleep(1)
        
        # Get list of tools
        print("\nSending tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools-test",
            "method": "tools/list",
            "params": {}
        }
        
        tools_request_str = json.dumps(tools_request) + "\n"
        print(f"Request: {tools_request_str.strip()}")
        
        process.stdin.write(tools_request_str)
        process.stdin.flush()
        
        # Read the response with a timeout
        start_time = time.time()
        response_str = ""
        while time.time() - start_time < 5:
            if process.stdout.readable():
                line = process.stdout.readline().strip()
                if line:
                    response_str = line
                    break
            
            # Check if there's error output
            if process.stderr.readable():
                stderr_line = process.stderr.readline().strip()
                if stderr_line:
                    print(f"STDERR: {stderr_line}")
            
            if process.poll() is not None:
                print(f"ERROR: Server process exited with code {process.returncode}")
                stderr = process.stderr.read()
                print(f"Server error output: {stderr}")
                return 1
                
            time.sleep(0.1)
        
        if not response_str:
            print("ERROR: No response received from server")
            stderr = process.stderr.read()
            print(f"Server error output: {stderr}")
            return 1
        
        print(f"Response: {response_str}")
        
        # Parse the response
        try:
            response = json.loads(response_str)
            print("Successfully parsed response")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON response: {e}")
            return 1
        
        print("\nTest completed successfully!")
        return 0
        
    finally:
        # Clean up
        print("\nShutting down server...")
        try:
            process.terminate()
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            print("Process didn't terminate, killing...")
            process.kill()
            process.wait()

if __name__ == "__main__":
    sys.exit(main()) 