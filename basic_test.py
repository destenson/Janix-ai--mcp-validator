#!/usr/bin/env python3
"""
Basic test for the mcp_server_fetch implementation.
Only tests for successful initialization to verify functionality.
"""

import subprocess
import json
import time
import os

def main():
    """
    Run a simple test to initialize the MCP fetch server and
    create a compliance report showing it's functional.
    """
    print("\n=== BASIC MCP FETCH SERVER TEST ===\n")
    
    # Create the reports directory if it doesn't exist
    if not os.path.exists("./reports"):
        os.makedirs("./reports")
    
    # Start the server
    print("Starting the server process...")
    process = subprocess.Popen(
        ["python", "-m", "mcp_server_fetch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Give it a moment to start
    time.sleep(1)
    
    # Check if process is running
    if process.poll() is not None:
        print("❌ ERROR: Server failed to start")
        return 1
    
    print("✅ Server started successfully")
    
    # Send initialize request
    print("\nSending initialization request...")
    init_request = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "BasicTest", "version": "1.0.0"}
        }
    }
    
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()
    
    # Wait for response
    response_str = process.stdout.readline().strip()
    
    if not response_str:
        print("❌ ERROR: No response received")
        process.terminate()
        return 1
    
    try:
        response = json.loads(response_str)
        if "result" in response:
            server_info = response["result"].get("serverInfo", {})
            print(f"✅ Server initialized successfully: {server_info}")
            
            # Generate a simple report
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_path = f"./reports/fetch_success_{timestamp}.md"
            
            with open(report_path, "w") as f:
                f.write("# MCP Fetch Server Compliance Report\n\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## Status: Success\n\n")
                f.write("## Test Details\n\n")
                f.write("- ✅ Server Initialization: Successful\n")
                f.write(f"  - Server Info: {server_info}\n")
                f.write("\n## Summary\n\n")
                f.write("The MCP Fetch Server was successfully initialized with the MCP 2024-11-05 protocol.\n")
                f.write("This report confirms the server can properly respond to initialization requests.\n")
            
            print(f"\nSuccess report created: {report_path}")
        else:
            print(f"❌ ERROR: Initialization failed: {response.get('error', {})}")
            process.terminate()
            return 1
    except json.JSONDecodeError:
        print(f"❌ ERROR: Invalid JSON response: {response_str}")
        process.terminate()
        return 1
    
    # Clean up
    print("\nTerminating server process...")
    process.terminate()
    
    print("\nTest completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main()) 