#!/usr/bin/env python3
"""
Standalone tester for STDIO MCP servers.

This script tests a STDIO MCP server by sending basic MCP protocol commands
and validating the responses according to the protocol specification.
"""

import os
import sys
import json
import subprocess
import time
import argparse
import shlex
from pathlib import Path

# Test states
class TestState:
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

# Default server command
DEFAULT_SERVER_CMD = "python docker/stdio_server.py"

def run_test(test_name, server_process, request, expected_check_fn=None, cleanup_fn=None):
    """Run a single test against the server process."""
    print(f"Running test: {test_name}")
    
    # Send the request
    request_str = json.dumps(request)
    print(f"  > Sending: {request_str}")
    server_process.stdin.write(request_str + "\n")
    server_process.stdin.flush()
    
    # Read response
    response_str = server_process.stdout.readline().strip()
    print(f"  < Received: {response_str}")
    
    # Parse and validate response
    try:
        response = json.loads(response_str)
        
        # Check if response has expected structure
        if "jsonrpc" not in response or response.get("jsonrpc") != "2.0":
            print(f"  [FAIL] Missing or invalid jsonrpc version")
            return TestState.FAIL
            
        # Check request ID is echoed correctly
        if "id" in request and (response.get("id") != request["id"]):
            print(f"  [FAIL] Response ID {response.get('id')} doesn't match request ID {request['id']}")
            return TestState.FAIL
            
        # If this is a notification (no ID), there should be no response
        if "id" not in request and response_str:
            print(f"  [FAIL] Received response for a notification")
            return TestState.FAIL
            
        # Check for result or error
        if "result" not in response and "error" not in response:
            print(f"  [FAIL] Response missing both result and error fields")
            return TestState.FAIL
            
        # If there's a custom validation function, run it
        if expected_check_fn:
            result = expected_check_fn(response)
            if result != TestState.PASS:
                return result
                
        # If we got here, test passed
        print(f"  [PASS] Test passed")
        return TestState.PASS
        
    except json.JSONDecodeError:
        print(f"  [FAIL] Invalid JSON response")
        return TestState.FAIL
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return TestState.FAIL
    finally:
        # Run cleanup function if provided
        if cleanup_fn:
            cleanup_fn()

def check_init_response(response):
    """Check the initialize response conforms to MCP protocol."""
    # Check for required fields in result
    if "result" not in response:
        print(f"  [FAIL] Missing result field in response")
        return TestState.FAIL
        
    result = response["result"]
    
    # Check for protocolVersion
    if "protocolVersion" not in result:
        print(f"  [FAIL] Missing protocolVersion in result")
        return TestState.FAIL
        
    # Check for serverInfo
    if "serverInfo" not in result:
        print(f"  [FAIL] Missing serverInfo in result")
        return TestState.FAIL
        
    # Check for capabilities
    if "capabilities" not in result:
        print(f"  [FAIL] Missing capabilities in result")
        return TestState.FAIL
        
    return TestState.PASS

def check_tools_list_response(response):
    """Check the tools/list response conforms to MCP protocol."""
    if "result" not in response:
        print(f"  [FAIL] Missing result field in response")
        return TestState.FAIL
        
    result = response["result"]
    
    # Check for tools array
    if "tools" not in result or not isinstance(result["tools"], list):
        print(f"  [FAIL] Missing or invalid tools array in result")
        return TestState.FAIL
        
    # Check each tool has required fields
    for i, tool in enumerate(result["tools"]):
        if "name" not in tool:
            print(f"  [FAIL] Tool at index {i} missing name field")
            return TestState.FAIL
            
        if "description" not in tool:
            print(f"  [FAIL] Tool at index {i} missing description field")
            return TestState.FAIL
            
        if "parameters" not in tool:
            print(f"  [FAIL] Tool at index {i} missing parameters field")
            return TestState.FAIL
    
    return TestState.PASS

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test a STDIO MCP server implementation")
    parser.add_argument("--command", default=DEFAULT_SERVER_CMD,
                      help="Command to start the STDIO server")
    parser.add_argument("--args", default="",
                      help="Additional arguments for the server command")
    parser.add_argument("--protocol-version", default="2025-03-26",
                      help="MCP protocol version to test against")
    parser.add_argument("--test", default="all",
                      help="Specific test to run (all, init, tools, shutdown)")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug output")
    
    args = parser.parse_args()
    
    # Build the full command with arguments
    full_command = f"{args.command} {args.args}".strip()
    print(f"Starting server with command: {full_command}")
    
    # Start the server process
    env = os.environ.copy()
    env["MCP_PROTOCOL_VERSION"] = args.protocol_version
    if args.debug:
        env["MCP_DEBUG"] = "true"
    
    try:
        process = subprocess.Popen(
            shlex.split(full_command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Give the server a moment to start
        time.sleep(0.5)
        
        # Check if the process started successfully
        if process.poll() is not None:
            print(f"ERROR: Server process failed to start (exit code {process.returncode})")
            stderr = process.stderr.read()
            if stderr:
                print(f"Server stderr: {stderr}")
            return 1
            
        # Tests to run
        tests_to_run = []
        
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": "test-init",
            "method": "initialize",
            "params": {
                "protocolVersion": args.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "MCPTester",
                    "version": "1.0.0"
                }
            }
        }
        
        if args.test in ["all", "init"]:
            tests_to_run.append(("Initialize", init_request, check_init_response))
        
        # Tools list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "test-tools-list",
            "method": "tools/list",
            "params": {}
        }
        
        if args.test in ["all", "tools"]:
            tests_to_run.append(("Tools List", tools_request, check_tools_list_response))
        
        # Shutdown request
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "test-shutdown",
            "method": "shutdown",
            "params": {}
        }
        
        if args.test in ["all", "shutdown"]:
            tests_to_run.append(("Shutdown", shutdown_request, None))
        
        # Run the tests
        results = {}
        for name, request, check_fn in tests_to_run:
            result = run_test(name, process, request, check_fn)
            results[name] = result
            
        # Send exit notification
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
            print("Server did not exit, terminating...")
            process.terminate()
            
        # Print any stderr output
        stderr_output = process.stderr.read()
        if stderr_output and args.debug:
            print("\nServer stderr output:")
            for line in stderr_output.splitlines():
                print(f"SERVER: {line}")
        
        # Summarize results
        print("\nTest Results:")
        all_passed = True
        for name, result in results.items():
            print(f"{name}: {result}")
            if result != TestState.PASS:
                all_passed = False
                
        if all_passed:
            print("\nAll tests PASSED - Server implementation is compliant")
            return 0
        else:
            print("\nSome tests FAILED - Server implementation needs fixes")
            return 1
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 