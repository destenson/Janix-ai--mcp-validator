#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import threading

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.


def main():
    print("MCP STDIO TEST STARTING")

    # Prepare test directory
    test_dir = os.path.abspath("../test_data/files")
    os.makedirs(test_dir, exist_ok=True)
    print(f"Test directory: {test_dir}")

    # Create a test file if it doesn't exist
    test_file_path = os.path.join(test_dir, "test.txt")
    with open(test_file_path, 'w') as f:
        f.write("This is a test file for MCP filesystem server testing.\n")
    print(f"Test file updated: {test_file_path}")

    # Ensure Docker network exists
    try:
        network_result = subprocess.run(
            ["docker", "network", "inspect", "mcp-test-network"],
            capture_output=True,
            text=True
        )
        if network_result.returncode != 0:
            print("Creating Docker network: mcp-test-network")
            subprocess.run(["docker", "network", "create", "mcp-test-network"], check=True)
        else:
            print("Using existing Docker network: mcp-test-network")
    except Exception as e:
        print(f"Error with Docker network: {e}")
        sys.exit(1)

    # Start MCP filesystem server in Docker
    server_cmd = (
        f"docker run -i --rm "
        f"--network mcp-test-network "
        f"--mount type=bind,src={test_dir},dst=/projects "
        f"--env MCP_PROTOCOL_VERSION=2025-03-26 "
        f"mcp/filesystem /projects"
    )
    print(f"Server command: {server_cmd}")

    try:
        # Start the server process
        server = subprocess.Popen(
            server_cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print any initial stderr output
        print("Waiting for server to start...")
        time.sleep(2)
        
        # Log any stderr output that's already available
        if server.poll() is not None:
            print(f"Server failed to start, exit code: {server.returncode}")
            stderr = server.stderr.read()
            print(f"Server stderr: {stderr}")
            sys.exit(1)
        
        # Initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": "test_init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "TestClient",
                    "version": "1.0"
                }
            }
        }
        
        # Send the request
        print("\n1. Sending initialize request...")
        server.stdin.write(json.dumps(init_request) + "\n")
        server.stdin.flush()
        
        # Read the response
        init_response = server.stdout.readline()
        print(f"Initialize Response: {init_response}")
        init_data = json.loads(init_response)
        
        # Send the 'initialized' notification (no response expected)
        init_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        print("\n2. Sending initialized notification...")
        server.stdin.write(json.dumps(init_notification) + "\n")
        server.stdin.flush()
        
        # Request list of tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools_list",
            "method": "tools/list",
            "params": {}
        }
        
        print("\n3. Requesting tools list...")
        server.stdin.write(json.dumps(tools_request) + "\n")
        server.stdin.flush()
        
        print("Waiting for tools list response...")
        tools_response = server.stdout.readline()
        print(f"Tools Response: {tools_response}")
        tools_data = json.loads(tools_response)
        
        # List directory
        list_request = {
            "jsonrpc": "2.0",
            "id": "list_dir",
            "method": "list_directory",
            "params": {
                "path": "/projects"
            }
        }
        
        print("\n4. Listing directory...")
        server.stdin.write(json.dumps(list_request) + "\n")
        server.stdin.flush()
        
        list_response = server.stdout.readline()
        print(f"List Response: {list_response}")
        list_data = json.loads(list_response)
        
        # Write a test file
        test_content = "This is a test file created by the MCP validator"
        write_request = {
            "jsonrpc": "2.0",
            "id": "write_file",
            "method": "write_file",
            "params": {
                "path": "/projects/test_file.txt",
                "content": test_content
            }
        }
        
        print("\n5. Writing test file...")
        server.stdin.write(json.dumps(write_request) + "\n")
        server.stdin.flush()
        
        write_response = server.stdout.readline()
        print(f"Write Response: {write_response}")
        write_data = json.loads(write_response)
        
        # Read the file back
        read_request = {
            "jsonrpc": "2.0",
            "id": "read_file",
            "method": "read_file",
            "params": {
                "path": "/projects/test_file.txt"
            }
        }
        
        print("\n6. Reading test file...")
        server.stdin.write(json.dumps(read_request) + "\n")
        server.stdin.flush()
        
        read_response = server.stdout.readline()
        print(f"Read Response: {read_response}")
        read_data = json.loads(read_response)
        
        # Verify content matches
        content = read_data.get("result", {}).get("content", "")
        if content == test_content:
            print(f"\n✅ CONTENT VERIFICATION SUCCESSFUL")
        else:
            print(f"\n❌ CONTENT VERIFICATION FAILED")
            print(f"Expected: '{test_content}'")
            print(f"Got: '{content}'")
        
        # Summary
        protocol_version = init_data.get("result", {}).get("protocolVersion", "unknown")
        server_info = init_data.get("result", {}).get("serverInfo", {})
        server_name = server_info.get("name", "unknown")
        server_version = server_info.get("version", "unknown")
        
        print("\n=== TEST SUMMARY ===")
        print(f"Server: {server_name} v{server_version}")
        print(f"Protocol version: {protocol_version}")
        
        # Extract tool names from the tools response
        tool_names = []
        tools_list = tools_data.get("result", {}).get("tools", [])
        for tool in tools_list:
            if isinstance(tool, dict) and "name" in tool:
                tool_names.append(tool["name"])
        
        print(f"Available tools: {', '.join(tool_names)}")
        print("All operations completed successfully")
        
        print("\nMCP STDIO TEST COMPLETED SUCCESSFULLY")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return 1
        
    finally:
        print("\nShutting down server...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

if __name__ == "__main__":
    sys.exit(main()) 