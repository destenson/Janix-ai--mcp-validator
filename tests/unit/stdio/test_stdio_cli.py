#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the STDIO CLI module
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from io import StringIO

# Mock the report import
sys.modules['mcp_testing.report'] = MagicMock()

from mcp_testing.stdio.cli import main, run_stdio_tester


class TestStdioCli(unittest.TestCase):
    """Tests for the STDIO CLI module."""

    @patch('mcp_testing.stdio.cli.check_command_exists')
    @patch('mcp_testing.stdio.cli.run_stdio_tester')
    def test_main_success(self, mock_run_tester, mock_check_command):
        """Test that main returns 0 when tests pass."""
        # Setup
        mock_check_command.return_value = True
        mock_run_tester.return_value = True
        
        # Redirect stdout for testing
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Run with test arguments
            with patch('sys.argv', ['cli.py', 'python', '--args', 'server.py']):
                result = main()
                
            # Verify
            self.assertEqual(result, 0)
            mock_check_command.assert_called_once_with('python')
            mock_run_tester.assert_called_once_with('python', ['server.py'], False, '2025-06-18')
            self.assertIn("All STDIO tests passed", sys.stdout.getvalue())
        finally:
            # Restore stdout
            sys.stdout = original_stdout

    @patch('mcp_testing.stdio.cli.check_command_exists')
    @patch('mcp_testing.stdio.cli.run_stdio_tester')
    def test_main_failure(self, mock_run_tester, mock_check_command):
        """Test that main returns 1 when tests fail."""
        # Setup
        mock_check_command.return_value = True
        mock_run_tester.return_value = False
        
        # Redirect stderr for testing
        original_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            # Run with test arguments
            with patch('sys.argv', ['cli.py', 'python']):
                result = main()
                
            # Verify
            self.assertEqual(result, 1)
            mock_check_command.assert_called_once()
            mock_run_tester.assert_called_once_with('python', [], False, '2025-06-18')
            self.assertIn("Some STDIO tests failed", sys.stderr.getvalue())
        finally:
            # Restore stderr
            sys.stderr = original_stderr

    @patch('mcp_testing.stdio.cli.check_command_exists')
    def test_main_command_not_found(self, mock_check_command):
        """Test that main returns 1 when server command is not found."""
        # Setup
        mock_check_command.return_value = False
        
        # Redirect stderr for testing
        original_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            # Run with test arguments
            with patch('sys.argv', ['cli.py', 'nonexistent_command']):
                result = main()
                
            # Verify
            self.assertEqual(result, 1)
            mock_check_command.assert_called_once_with('nonexistent_command')
            self.assertIn("Error: Command 'nonexistent_command' not found", sys.stderr.getvalue())
        finally:
            # Restore stderr
            sys.stderr = original_stderr

    @patch('mcp_testing.stdio.cli.os.makedirs')
    @patch('mcp_testing.stdio.cli.generate_report')
    @patch('mcp_testing.stdio.cli.check_command_exists')
    @patch('mcp_testing.stdio.cli.run_stdio_tester')
    def test_main_with_report(self, mock_run_tester, mock_check_command, mock_generate_report, mock_makedirs):
        """Test that main generates a report when output directory is specified."""
        # Setup
        mock_check_command.return_value = True
        mock_run_tester.return_value = True
        
        # Run with test arguments including output directory
        with patch('sys.argv', [
            'cli.py', 'python', '--args', 'server.py',
            '--output-dir', '/test/reports', 
            '--report-format', 'json'
        ]):
            result = main()
            
        # Verify
        self.assertEqual(result, 0)
        mock_check_command.assert_called_once_with('python')
        mock_run_tester.assert_called_once_with('python', ['server.py'], False, '2025-06-18')
        mock_makedirs.assert_called_once_with('/test/reports', exist_ok=True)
        mock_generate_report.assert_called_once()
        # Verify the report path and format
        args = mock_generate_report.call_args[0]
        self.assertEqual(args[1], '/test/reports/report.json')
        self.assertEqual(args[2], 'json')

    @patch('mcp_testing.stdio.cli.MCPStdioTester')
    def test_run_stdio_tester(self, mock_tester_class):
        """Test that run_stdio_tester creates a tester and runs all tests."""
        # Setup the mock
        mock_tester = MagicMock()
        mock_tester_class.return_value = mock_tester
        mock_tester.run_all_tests.return_value = True
        
        # Call the function
        result = run_stdio_tester("python", ["server.py", "--debug"], True, "2024-11-05")
        
        # Verify
        self.assertTrue(result)
        mock_tester_class.assert_called_once_with("python", ["server.py", "--debug"], True)
        self.assertEqual(mock_tester.protocol_version, "2024-11-05")
        mock_tester.run_all_tests.assert_called_once()

    @patch('mcp_testing.stdio.cli.MCPStdioTester')
    def test_run_stdio_tester_default_args(self, mock_tester_class):
        """Test that run_stdio_tester handles default None args."""
        # Setup the mock
        mock_tester = MagicMock()
        mock_tester_class.return_value = mock_tester
        mock_tester.run_all_tests.return_value = True
        
        # Call the function with default args
        result = run_stdio_tester("python")
        
        # Verify
        self.assertTrue(result)
        mock_tester_class.assert_called_once_with("python", [], False)
        self.assertEqual(mock_tester.protocol_version, "2025-06-18")
        mock_tester.run_all_tests.assert_called_once()


if __name__ == '__main__':
    unittest.main() 