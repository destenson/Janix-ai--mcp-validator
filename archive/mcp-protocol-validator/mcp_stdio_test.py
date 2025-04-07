#!/usr/bin/env python3
import os, sys, subprocess, json, time
print("MCP STDIO TEST STARTING")
test_dir = os.path.abspath("../test_data/files")
os.makedirs(test_dir, exist_ok=True)
print(f"Test directory: {test_dir}")
server_cmd = f"docker run -i --rm --network mcp-test-network --mount type=bind,src={test_dir},dst=/projects mcp/filesystem /projects"
print(f"Server command: {server_cmd}")
server = subprocess.Popen(server_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(2)
init_request = {"jsonrpc": "2.0", "id": "test_init", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "TestClient", "version": "1.0"}}}
server.stdin.write(json.dumps(init_request) + "\n")
server.stdin.flush()
response = server.stdout.readline()
print(f"Response: {response}")
server.terminate()
print("MCP STDIO TEST ENDING")
