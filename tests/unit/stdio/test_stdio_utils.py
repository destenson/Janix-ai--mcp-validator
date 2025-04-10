#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the stdio/utils.py module.
"""

import unittest
from unittest.mock import patch, Mock, mock_open
import os
import subprocess
import time
import shlex
from typing import List, Tuple

from mcp_testing.stdio.utils import (
    check_command_exists,
    run_process_with_timeout,
    verify_python_server
)


class TestStdioUtils(unittest.TestCase):
    """Test cases for the stdio utils module."""

    @patch('subprocess.run')
    def test_check_command_exists_true(self, mock_run):
        """Test check_command_exists when command exists."""
        # Mock subprocess.run to return success
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Test simple command
        result = check_command_exists("python")
        self.assertTrue(result)
        mock_run.assert_called_with(
            ["which", "python"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Test command with arguments
        result = check_command_exists("python script.py --arg1 val1")
        self.assertTrue(result)
        mock_run.assert_called_with(
            ["which", "python"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

    @patch('subprocess.run')
    def test_check_command_exists_false(self, mock_run):
        """Test check_command_exists when command doesn't exist."""
        # Mock subprocess.run to return failure
        mock_process = Mock()
        mock_process.returncode = 1
        mock_run.return_value = mock_process
        
        # Test nonexistent command
        result = check_command_exists("nonexistent_command")
        self.assertFalse(result)
        mock_run.assert_called_with(
            ["which", "nonexistent_command"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

    @patch('subprocess.run')
    def test_check_command_exists_exception(self, mock_run):
        """Test check_command_exists when an exception occurs."""
        # Mock subprocess.run to raise an exception
        mock_run.side_effect = Exception("Test exception")
        
        # Check that it returns False gracefully
        result = check_command_exists("python")
        self.assertFalse(result)
        mock_run.assert_called_with(
            ["which", "python"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

    @patch('subprocess.run')
    def test_run_process_with_timeout_success(self, mock_run):
        """Test run_process_with_timeout with successful execution."""
        # Mock subprocess.run to return success
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "test output"
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        
        # Test simple command
        success, stdout, stderr = run_process_with_timeout("echo", ["hello"])
        self.assertTrue(success)
        self.assertEqual(stdout, "test output")
        self.assertEqual(stderr, "")
        mock_run.assert_called_with(
            ["echo", "hello"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        # Test with different timeout
        success, stdout, stderr = run_process_with_timeout("echo", ["hello"], timeout=10)
        self.assertTrue(success)
        mock_run.assert_called_with(
            ["echo", "hello"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        # Test with no args
        success, stdout, stderr = run_process_with_timeout("echo")
        self.assertTrue(success)
        mock_run.assert_called_with(
            ["echo"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

    @patch('subprocess.run')
    def test_run_process_with_timeout_failure(self, mock_run):
        """Test run_process_with_timeout with failed execution."""
        # Mock subprocess.run to return failure
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "error message"
        mock_run.return_value = mock_process
        
        # Test command failure
        success, stdout, stderr = run_process_with_timeout("false")
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "error message")

    @patch('subprocess.run')
    def test_run_process_with_timeout_timeout(self, mock_run):
        """Test run_process_with_timeout when process times out."""
        # Mock subprocess.run to raise TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)
        
        # Check timeout handling
        success, stdout, stderr = run_process_with_timeout("sleep", ["10"])
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertIn("timed out", stderr)

    @patch('subprocess.run')
    def test_run_process_with_timeout_exception(self, mock_run):
        """Test run_process_with_timeout when an exception occurs."""
        # Mock subprocess.run to raise an exception
        mock_run.side_effect = Exception("Test exception")
        
        # Check exception handling
        success, stdout, stderr = run_process_with_timeout("invalid_command")
        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertIn("Error running process", stderr)
        self.assertIn("Test exception", stderr)

    @patch('os.path.isfile')
    @patch('subprocess.run')
    def test_verify_python_server_success(self, mock_run, mock_isfile):
        """Test verify_python_server with a valid Python file."""
        # Mock os.path.isfile to return True
        mock_isfile.return_value = True
        
        # Mock subprocess.run to return success
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Test verification
        result = verify_python_server("server.py")
        self.assertTrue(result)
        mock_isfile.assert_called_with("server.py")
        mock_run.assert_called_with(
            ["python", "-m", "py_compile", "server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        
        # Test with different timeout
        result = verify_python_server("server.py", timeout=5)
        self.assertTrue(result)
        mock_run.assert_called_with(
            ["python", "-m", "py_compile", "server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

    @patch('os.path.isfile')
    def test_verify_python_server_file_not_found(self, mock_isfile):
        """Test verify_python_server when file doesn't exist."""
        # Mock os.path.isfile to return False
        mock_isfile.return_value = False
        
        # Test verification of nonexistent file
        with patch('builtins.print') as mock_print:
            result = verify_python_server("nonexistent.py")
            self.assertFalse(result)
            mock_isfile.assert_called_with("nonexistent.py")
            mock_print.assert_called_with("Server file not found: nonexistent.py")

    @patch('os.path.isfile')
    def test_verify_python_server_not_python_file(self, mock_isfile):
        """Test verify_python_server with a non-Python file."""
        # Mock os.path.isfile to return True
        mock_isfile.return_value = True
        
        # Test verification of non-Python file
        with patch('builtins.print') as mock_print:
            result = verify_python_server("server.txt")
            self.assertFalse(result)
            mock_isfile.assert_called_with("server.txt")
            mock_print.assert_called_with("Server file does not have .py extension: server.txt")

    @patch('os.path.isfile')
    @patch('subprocess.run')
    def test_verify_python_server_syntax_error(self, mock_run, mock_isfile):
        """Test verify_python_server with a Python file containing syntax errors."""
        # Mock os.path.isfile to return True
        mock_isfile.return_value = True
        
        # Mock subprocess.run to return failure
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stderr = "SyntaxError: invalid syntax"
        mock_run.return_value = mock_process
        
        # Test verification
        with patch('builtins.print') as mock_print:
            result = verify_python_server("invalid.py")
            self.assertFalse(result)
            mock_isfile.assert_called_with("invalid.py")
            mock_run.assert_called_with(
                ["python", "-m", "py_compile", "invalid.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )
            mock_print.assert_called_with("Python syntax check failed: SyntaxError: invalid syntax")

    @patch('os.path.isfile')
    @patch('subprocess.run')
    def test_verify_python_server_exception(self, mock_run, mock_isfile):
        """Test verify_python_server when an exception occurs."""
        # Mock os.path.isfile to return True
        mock_isfile.return_value = True
        
        # Mock subprocess.run to raise an exception
        mock_run.side_effect = Exception("Test exception")
        
        # Test verification
        with patch('builtins.print') as mock_print:
            result = verify_python_server("server.py")
            self.assertFalse(result)
            mock_isfile.assert_called_with("server.py")
            mock_run.assert_called_with(
                ["python", "-m", "py_compile", "server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )
            mock_print.assert_called_with("Error verifying Python server: Test exception")


if __name__ == "__main__":
    unittest.main() 