#!/usr/bin/env python3
"""
Run a basic test against the minimal MCP STDIO server and generate a markdown report.
This script is designed to run to completion and generate a report reliably.
"""

import os
import subprocess
import time
import datetime

# Configuration
SERVER_COMMAND = "./minimal_mcp_server/minimal_mcp_server.py"
PROTOCOL_VERSION = "2024-11-05"
TEST_MODULE = "test_base_protocol"
TEST_CLASS = "TestBasicSTDIO"
TEST_METHOD = "test_initialization"
OUTPUT_DIR = "reports"
OUTPUT_FILE = f"{OUTPUT_DIR}/basic_test_{PROTOCOL_VERSION}.md"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set environment variables
test_env = os.environ.copy()
test_env["MCP_TRANSPORT_TYPE"] = "stdio"
test_env["MCP_SERVER_COMMAND"] = SERVER_COMMAND
test_env["MCP_PROTOCOL_VERSION"] = PROTOCOL_VERSION
test_env["MCP_DEBUG"] = "true"

# Command to run
test_cmd = [
    "python", "-m", "pytest", "-v",
    f"tests/{TEST_MODULE}.py::{TEST_CLASS}::{TEST_METHOD}",
    "--md", OUTPUT_FILE
]

print("=" * 80)
print(f"Running test: {' '.join(test_cmd)}")
print(f"With environment:")
print(f" - MCP_TRANSPORT_TYPE: stdio")
print(f" - MCP_SERVER_COMMAND: {SERVER_COMMAND}")
print(f" - MCP_PROTOCOL_VERSION: {PROTOCOL_VERSION}")
print("=" * 80)

# Run the test
try:
    result = subprocess.run(
        test_cmd,
        env=test_env,
        check=False,
        capture_output=True,
        text=True
    )
    
    # Generate a backup report in case pytest-md fails
    backup_file = f"{OUTPUT_DIR}/backup_report_{time.time()}.md"
    
    with open(backup_file, "w") as f:
        # Write header
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d at %H:%M:%S")
        
        f.write(f"# Backup Test Report\n\n")
        f.write(f"*Report generated on {date_str}*\n\n")
        f.write(f"## Test Details\n\n")
        f.write(f"- **Module:** {TEST_MODULE}\n")
        f.write(f"- **Class:** {TEST_CLASS}\n")
        f.write(f"- **Method:** {TEST_METHOD}\n")
        f.write(f"- **Protocol Version:** {PROTOCOL_VERSION}\n\n")
        f.write(f"## Command\n\n```\n{' '.join(test_cmd)}\n```\n\n")
        f.write(f"## Result\n\n")
        f.write(f"Exit code: {result.returncode}\n\n")
        f.write(f"## Standard Output\n\n```\n{result.stdout}\n```\n\n")
        
        if result.stderr:
            f.write(f"## Standard Error\n\n```\n{result.stderr}\n```\n\n")
    
    print(f"Test completed with exit code: {result.returncode}")
    print(f"Backup report saved to: {backup_file}")
    
    # Check if the pytest-md report was generated
    if os.path.exists(OUTPUT_FILE):
        print(f"Report generated successfully: {OUTPUT_FILE}")
    else:
        print(f"Report file {OUTPUT_FILE} was not created by pytest-md")
        print(f"Using backup report: {backup_file}")
        
        # Copy backup to expected location
        with open(backup_file, "r") as src:
            with open(OUTPUT_FILE, "w") as dest:
                dest.write(src.read())
        
        print(f"Copied backup report to: {OUTPUT_FILE}")
        
except Exception as e:
    print(f"Error running test: {str(e)}")
    raise

print("=" * 80)
print("Test execution complete") 