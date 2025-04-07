#!/usr/bin/env python3

"""
Simplified MCP Protocol Validator script
"""

import os
import sys
import pytest
from pathlib import Path

def main():
    """Run the tests."""
    # Set up the environment variables
    os.environ["MCP_TRANSPORT_TYPE"] = "stdio"
    os.environ["MCP_SERVER_COMMAND"] = "python minimal_mcp_server/minimal_mcp_server.py"
    os.environ["MCP_PROTOCOL_VERSION"] = "2024-11-05"
    os.environ["MCP_DEBUG"] = "1"
    
    # Build the pytest arguments
    pytest_args = ["-v", "tests/test_base_protocol.py"]
    
    # Create the reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Run the tests
    print(f"Running tests with pytest arguments: {pytest_args}")
    return pytest.main(pytest_args)

if __name__ == "__main__":
    # Make sure PYTHONPATH includes the current directory
    if "." not in sys.path:
        sys.path.insert(0, ".")
    
    # Run the tests
    exit_code = main()
    sys.exit(exit_code) 