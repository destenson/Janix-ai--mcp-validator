#!/usr/bin/env python3

import subprocess
import json
import sys
import os

def main():
    # Start Docker container and test the MCP Filesystem server
    mount_path = os.path.abspath("../test_data/files")
    print(f"Mount path: {mount_path}")
    
    cmd = [
        "docker", "run", "-i", "--rm",
        "--mount", f"type=bind,src={mount_path},dst=/projects",
        "mcp/filesystem", "/projects"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )
    
    try:
        # Send initialize request
        init_req = {
            "jsonrpc": "2.0",
            "id": "test_init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "TestClient", "version": "1.0"}
            }
        }
        
        print("Sending initialize request")
        process.stdin.write(json.dumps(init_req).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline().decode('utf-8')
        print(f"Response: {response}")
        
        # Send initialized notification
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        print("Sending initialized notification")
        process.stdin.write(json.dumps(init_notification).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        # Get tools list
        tools_req = {
            "jsonrpc": "2.0",
            "id": "tools_list",
            "method": "tools/list",
            "params": {}
        }
        
        print("Requesting tools list")
        process.stdin.write(json.dumps(tools_req).encode('utf-8') + b'\n')
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline().decode('utf-8')
        print(f"Tools list: {response}")
        
        return 0
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    finally:
        # Cleanup
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    sys.exit(main()) 