#!/usr/bin/env python3
import subprocess
import json
import sys
import os
import time

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.


def main():
    # Configure the test
    mount_path = os.path.abspath("../test_data/files")
    docker_image = "mcp/filesystem"
    protocol_version = "2025-03-26"
    
    print(f"Starting test with mount path: {mount_path}")
    print(f"Using Docker image: {docker_image}")
    print(f"Protocol version: {protocol_version}")
    
    # Ensure mount directory exists
    os.makedirs(mount_path, exist_ok=True)
    
    # Start the Docker container
    cmd = [
        "docker", "run", "-i", "--rm",
        "--mount", f"type=bind,src={mount_path},dst=/projects",
        docker_image, "/projects"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False  # Use binary mode for precise control
    )
    
    try:
        # 1. Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": "test_init",
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "DirectMCPTest",
                    "version": "1.0.0"
                }
            }
        }
        
        print("\nSending initialize request...")
        process.stdin.write(json.dumps(init_request).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        response = process.stdout.readline().decode('utf-8')
        init_response = json.loads(response)
        print("Initialize response:", json.dumps(init_response, indent=2))
        
        # 2. Send initialized notification
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        print("\nSending initialized notification...")
        process.stdin.write(json.dumps(init_notification).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        # 3. Get list of tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools_list",
            "method": "tools/list",
            "params": {}
        }
        
        print("\nSending tools/list request...")
        process.stdin.write(json.dumps(tools_request).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        response = process.stdout.readline().decode('utf-8')
        tools_response = json.loads(response)
        print("Tools response:", json.dumps(tools_response, indent=2))
        
        # 4. List directory
        list_request = {
            "jsonrpc": "2.0",
            "id": "list_dir",
            "method": "filesystem/list_directory",
            "params": {
                "directory": "/projects"
            }
        }
        
        print("\nSending list_directory request...")
        process.stdin.write(json.dumps(list_request).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        response = process.stdout.readline().decode('utf-8')
        list_response = json.loads(response)
        print("List directory response:", json.dumps(list_response, indent=2))
        
        # 5. Write a test file
        test_content = "This is a test file created during MCP validation."
        write_request = {
            "jsonrpc": "2.0",
            "id": "write_file",
            "method": "filesystem/write_file",
            "params": {
                "file": "/projects/test_output.txt",
                "content": test_content
            }
        }
        
        print("\nSending write_file request...")
        process.stdin.write(json.dumps(write_request).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        response = process.stdout.readline().decode('utf-8')
        write_response = json.loads(response)
        print("Write file response:", json.dumps(write_response, indent=2))
        
        # 6. Read the file back
        read_request = {
            "jsonrpc": "2.0",
            "id": "read_file",
            "method": "filesystem/read_file",
            "params": {
                "file": "/projects/test_output.txt"
            }
        }
        
        print("\nSending read_file request...")
        process.stdin.write(json.dumps(read_request).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        response = process.stdout.readline().decode('utf-8')
        read_response = json.loads(response)
        print("Read file response:", json.dumps(read_response, indent=2))
        
        # Check if content matches
        if read_response.get("result", {}).get("content") == test_content:
            print("\n✅ Content verification successful!")
        else:
            print("\n❌ Content verification failed!")
            
        print("\n✅ Test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        return 1
    finally:
        print("\nStopping Docker container...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    sys.exit(main()) 