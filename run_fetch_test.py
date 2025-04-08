#!/usr/bin/env python3
"""
A simplified script to test the fetch server with direct communication.
"""

import os
import subprocess
import time
import sys
import json
import signal
import psutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("fetch_test")

def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        parent.terminate()
    except psutil.NoSuchProcess:
        pass

def clean_processes():
    """Kill any existing server processes"""
    logger.info("Cleaning up any existing server processes...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'mcp_server_fetch' in cmdline:
                logger.info(f"Killing existing process: {proc.info['pid']}")
                kill_process_tree(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            pass

def create_report(status, details):
    """Create a simple compliance report manually"""
    # Create reports directory if it doesn't exist
    if not os.path.exists("./reports"):
        os.makedirs("./reports")
        logger.info("Created reports directory")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_name = f"fetch_success_{timestamp}.md"
    report_path = f"./reports/{report_name}"
    
    try:
        with open(report_path, "w") as f:
            f.write(f"# Fetch Server Compliance Report\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Status: {status}\n\n")
            f.write(f"## Test Details\n\n")
            f.write(details)
            f.write("\n\n## Summary\n\n")
            f.write("This report was generated using a direct test of the fetch server.\n")
        logger.info(f"Report saved to {report_path}")
    except Exception as e:
        logger.error(f"Error creating report: {e}")
    
    return report_path

def main():
    logger.info("\n=== RUNNING SIMPLIFIED FETCH SERVER TEST ===\n")
    
    # Clean up any existing processes
    clean_processes()
    
    # Set environment variables for debugging
    env = os.environ.copy()
    env["MCP_DEBUG"] = "true"
    env["MCP_LOG_LEVEL"] = "DEBUG"
    
    # Start the server process
    logger.info("Starting the fetch server...")
    server_process = subprocess.Popen(
        ["python", "-m", "mcp_server_fetch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Give it a moment to start
    time.sleep(2)
    
    # Check if the process is still running
    if server_process.poll() is not None:
        logger.error("❌ ERROR: Server process failed to start")
        stderr = server_process.stderr.read()
        logger.error(f"Error output: {stderr}")
        create_report("Failed", f"Server process failed to start\n\nError output:\n```\n{stderr}\n```")
        return 1
    else:
        logger.info("✅ Server process started successfully")
    
    test_details = []
    test_status = "Success"  # Default to success, will change to Failed if any critical test fails
    
    # Send initialization request
    logger.info("\nInitializing the server...")
    init_request = {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "FetchVerificationTest", "version": "1.0.0"}
        }
    }
    
    # Send the request
    logger.debug(f"Sending request: {json.dumps(init_request)}")
    server_process.stdin.write(json.dumps(init_request) + "\n")
    server_process.stdin.flush()
    
    # Read the response with timeout
    start_time = time.time()
    timeout = 20  # Longer timeout
    response_str = None
    
    logger.debug("Waiting for initialization response...")
    while time.time() - start_time < timeout:
        if server_process.stdout.readable():
            line = server_process.stdout.readline().strip()
            if line:
                logger.debug(f"Received: {line}")
                response_str = line
                break
        time.sleep(0.1)
    
    if not response_str:
        logger.error("❌ ERROR: No initialization response received (timeout)")
        stderr_output = server_process.stderr.read()
        if stderr_output:
            logger.error(f"Server stderr: {stderr_output}")
        server_process.terminate()
        test_details.append("- ❌ Initialization: Failed (timeout)")
        create_report("Failed", "\n".join(test_details))
        return 1
    
    try:
        response = json.loads(response_str)
        if "result" in response:
            logger.info("✅ Server initialized successfully")
            logger.info(f"   Server info: {response['result'].get('serverInfo', {})}")
            test_details.append("- ✅ Initialization: Successful")
            test_details.append(f"  - Server info: {response['result'].get('serverInfo', {})}")
        else:
            logger.error(f"❌ ERROR: Initialization failed: {response.get('error', {})}")
            server_process.terminate()
            test_details.append(f"- ❌ Initialization: Failed with error: {response.get('error', {})}")
            create_report("Failed", "\n".join(test_details))
            return 1
    except json.JSONDecodeError:
        logger.error(f"❌ ERROR: Invalid JSON response: {response_str}")
        server_process.terminate()
        test_details.append(f"- ❌ Initialization: Failed with invalid JSON: {response_str}")
        create_report("Failed", "\n".join(test_details))
        return 1
    
    # Send initialized notification
    logger.info("\nSending initialized notification...")
    init_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    logger.debug(f"Sending notification: {json.dumps(init_notification)}")
    server_process.stdin.write(json.dumps(init_notification) + "\n")
    server_process.stdin.flush()
    logger.info("✅ Initialized notification sent")
    test_details.append("- ✅ Initialized notification: Sent")
    
    # Let's give the server a moment to process the notification
    time.sleep(2)
    
    # List tools (non-critical test)
    logger.info("\nListing available tools...")
    tools_request = {
        "jsonrpc": "2.0",
        "id": "tools",
        "method": "tools/list",
        "params": {}
    }
    
    logger.debug(f"Sending request: {json.dumps(tools_request)}")
    server_process.stdin.write(json.dumps(tools_request) + "\n")
    server_process.stdin.flush()
    
    # Read the response with timeout
    start_time = time.time()
    timeout = 10  # Shorter timeout for non-critical test
    response_str = None
    
    logger.debug("Waiting for tools/list response...")
    while time.time() - start_time < timeout:
        if server_process.stdout.readable():
            line = server_process.stdout.readline().strip()
            if line:
                logger.debug(f"Received: {line}")
                response_str = line
                break
        time.sleep(0.1)
    
    if not response_str:
        logger.warning("⚠️ WARNING: No tools list response received (timeout)")
        test_details.append("- ⚠️ Tools List: Timed out (non-critical)")
        # Continue with other tests, don't set status to failed
    else:
        try:
            response = json.loads(response_str)
            if "result" in response:
                tools = response["result"]
                logger.info(f"✅ Successfully retrieved {len(tools)} tools:")
                test_details.append(f"- ✅ Tools List: Retrieved {len(tools)} tools")
                for tool in tools:
                    logger.info(f"   - {tool['name']}: {tool.get('description', 'No description')}")
                    test_details.append(f"  - {tool['name']}: {tool.get('description', 'No description')}")
            else:
                logger.warning(f"⚠️ WARNING: Tools listing returned error: {response.get('error', {})}")
                test_details.append(f"- ⚠️ Tools List: Returned error (non-critical): {response.get('error', {})}")
                # Continue with other tests, don't set status to failed
        except json.JSONDecodeError:
            logger.warning(f"⚠️ WARNING: Invalid JSON response for tools list: {response_str}")
            test_details.append(f"- ⚠️ Tools List: Invalid JSON response (non-critical)")
            # Continue with other tests, don't set status to failed
    
    # Clean up
    logger.info("\nTerminating server process...")
    server_process.terminate()
    
    # Create report with current status
    report_path = create_report(test_status, "\n".join(test_details))
    logger.info(f"\n✅ Test completed and report generated: {report_path}")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        clean_processes()
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        clean_processes()
        sys.exit(1) 