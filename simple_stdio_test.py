#!/usr/bin/env python3
"""
Simple STDIO server test that runs a single test and generates a Markdown report.
This script focuses on simplicity and debugging to ensure reports are generated correctly.
"""

import os
import sys
import subprocess
import datetime
import argparse
import tempfile
import traceback

def main():
    """Main entry point for the script."""
    # Get the path to the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set default paths relative to the current directory
    root_dir = current_dir
    server_path = os.path.join(root_dir, "minimal_mcp_server", "minimal_mcp_server.py")
    reports_dir = os.path.join(root_dir, "simple_reports")
    
    parser = argparse.ArgumentParser(description="Simple test for the minimal STDIO server")
    parser.add_argument(
        "--protocol-version",
        default="2024-11-05",
        help="Protocol version to test against"
    )
    parser.add_argument(
        "--server-path",
        default=server_path,
        help="Path to the server script"
    )
    parser.add_argument(
        "--reports-dir",
        default=reports_dir,
        help="Directory to write reports to"
    )
    
    args = parser.parse_args()
    
    # Make server path absolute
    if not os.path.isabs(args.server_path):
        args.server_path = os.path.abspath(args.server_path)
    
    # Make reports directory absolute
    if not os.path.isabs(args.reports_dir):
        args.reports_dir = os.path.abspath(args.reports_dir)
    
    # Print configuration
    print("\n" + "=" * 60)
    print("Test Configuration")
    print("=" * 60)
    print(f"Current Directory: {current_dir}")
    print(f"Root Directory: {root_dir}")
    print(f"Protocol Version: {args.protocol_version}")
    print(f"Server Path: {args.server_path}")
    print(f"Reports Directory: {args.reports_dir}")
    print("=" * 60)
    
    # Debug: Check permissions and existence
    print("\nSystem Information:")
    print(f"Current user: {os.getuid()}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Server script exists: {os.path.exists(args.server_path)}")
    print(f"Server script is executable: {os.access(args.server_path, os.X_OK)}")
    
    # Ensure reports directory exists
    try:
        print(f"\nCreating reports directory: {args.reports_dir}")
        os.makedirs(args.reports_dir, exist_ok=True)
        print(f"Reports directory exists now: {os.path.exists(args.reports_dir)}")
        print(f"Reports directory is writable: {os.access(args.reports_dir, os.W_OK)}")
    except Exception as e:
        print(f"Error creating reports directory: {e}")
        traceback.print_exc()
        return 1
    
    # Set environment variables
    env = os.environ.copy()
    env["MCP_TRANSPORT_TYPE"] = "stdio"
    env["MCP_SERVER_COMMAND"] = args.server_path
    env["MCP_PROTOCOL_VERSION"] = args.protocol_version
    env["MCP_DEBUG"] = "true"
    
    # Test specification
    module = "test_base_protocol"
    cls = "TestBasicSTDIO"
    method = "test_initialization"
    
    # Build the pytest command
    cmd = [
        "python", "-m", "pytest", "-v",
        f"tests/{module}.py::{cls}::{method}"
    ]
    
    print(f"\nRunning test: {' '.join(cmd)}")
    print(f"Environment:")
    print(f"  MCP_TRANSPORT_TYPE: {env['MCP_TRANSPORT_TYPE']}")
    print(f"  MCP_SERVER_COMMAND: {env['MCP_SERVER_COMMAND']}")
    print(f"  MCP_PROTOCOL_VERSION: {env['MCP_PROTOCOL_VERSION']}")
    
    # First verify we can write to a temp file
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write("Test file write capability")
            temp_path = temp.name
        
        print(f"\nSuccessfully wrote to temp file: {temp_path}")
        if os.path.exists(temp_path):
            print(f"Temp file exists and is {os.path.getsize(temp_path)} bytes")
            os.unlink(temp_path)
            print(f"Temp file deleted")
    except Exception as e:
        print(f"Error writing temp file: {e}")
        traceback.print_exc()
    
    # Run the test
    try:
        print("\nStarting test subprocess...")
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        print(f"Subprocess completed with return code: {result.returncode}")
    except Exception as e:
        print(f"Error running test: {e}")
        traceback.print_exc()
        return 1
    
    # Generate report filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = os.path.join(args.reports_dir, f"stdio_test_{timestamp}.md")
    
    # Create report
    try:
        print(f"\nWriting report to: {report_filename}")
        with open(report_filename, "w") as f:
            f.write(f"# STDIO Server Test Report\n\n")
            f.write(f"*Report generated on {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n\n")
            
            f.write("## Test Details\n\n")
            f.write(f"- **Test:** {module}.{cls}.{method}\n")
            f.write(f"- **Protocol Version:** {args.protocol_version}\n")
            f.write(f"- **Server:** Minimal MCP STDIO Server\n")
            f.write(f"- **Server Path:** {args.server_path}\n\n")
            
            f.write("## Result\n\n")
            status = "PASS" if result.returncode == 0 else "FAIL"
            f.write(f"- **Status:** {status}\n")
            f.write(f"- **Exit Code:** {result.returncode}\n\n")
            
            f.write("## Command\n\n")
            f.write(f"```\n{' '.join(cmd)}\n```\n\n")
            
            f.write("## Standard Output\n\n")
            f.write("```\n")
            f.write(result.stdout)
            f.write("\n```\n\n")
            
            if result.stderr:
                f.write("## Standard Error\n\n")
                f.write("```\n")
                f.write(result.stderr)
                f.write("\n```\n\n")
        
        print(f"Report written successfully!")
        
        # Verify the report exists
        if os.path.exists(report_filename):
            file_size = os.path.getsize(report_filename)
            print(f"Verified report file exists: {report_filename}")
            print(f"File size: {file_size} bytes")
            
            # List the contents of the reports directory
            print(f"\nContents of {args.reports_dir}:")
            for item in os.listdir(args.reports_dir):
                item_path = os.path.join(args.reports_dir, item)
                if os.path.isfile(item_path):
                    print(f"  - {item} ({os.path.getsize(item_path)} bytes)")
        else:
            print(f"ERROR: Report file does not exist after writing!")
            return 1
    
    except Exception as e:
        print(f"Error writing report: {e}")
        traceback.print_exc()
        return 1
    
    return 0 if result.returncode == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 