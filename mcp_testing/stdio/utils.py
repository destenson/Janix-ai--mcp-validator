# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
STDIO Testing Utilities

Helper functions for testing MCP over STDIO transport.
"""

import os
import shlex
import subprocess
import time
from typing import List, Tuple

def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in the system path.
    
    Args:
        command: The command to check
        
    Returns:
        True if the command exists, False otherwise
    """
    # Get the first part of the command (the executable)
    executable = shlex.split(command)[0]
    
    # Check if the command exists
    try:
        result = subprocess.run(
            ["which", executable],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False

def run_process_with_timeout(command: str, args: List[str] = None, timeout: int = 5) -> Tuple[bool, str, str]:
    """
    Run a process with a timeout and return stdout/stderr.
    
    Args:
        command: The command to run
        args: Additional arguments for the command
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    args = args or []
    cmd = shlex.split(command) + args
    
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return process.returncode == 0, process.stdout, process.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Process timed out after {timeout} seconds"
    except Exception as e:
        return False, "", f"Error running process: {e}"

def verify_python_server(server_path: str, timeout: int = 2) -> bool:
    """
    Verify that a Python server file exists and is executable.
    
    Args:
        server_path: Path to the server Python file
        timeout: Timeout for verification in seconds
        
    Returns:
        True if the server exists and is a valid Python file, False otherwise
    """
    # Check if the file exists
    if not os.path.isfile(server_path):
        print(f"Server file not found: {server_path}")
        return False
    
    # Check if it's a Python file
    if not server_path.endswith('.py'):
        print(f"Server file does not have .py extension: {server_path}")
        return False
    
    # Try to syntax check the Python file
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            print(f"Python syntax check failed: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        print(f"Error verifying Python server: {e}")
        return False 