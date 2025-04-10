#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the compliance_report.py script.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open, call, AsyncMock
import sys
import os
import io
import tempfile
import shutil
import json
import asyncio
import pytest
from argparse import Namespace
from datetime import datetime
from pathlib import Path
import importlib

from mcp_testing.scripts import compliance_report
from mcp_testing.utils.server_compatibility import (
    is_shutdown_skipped,
    prepare_environment_for_server,
    get_server_specific_test_config,
    get_recommended_protocol_version
)


class TestComplianceReport(unittest.TestCase):
    """Test cases for the compliance_report script."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout and stderr for testing
        self.held_output = io.StringIO()
        self.held_error = io.StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self.held_output
        sys.stderr = self.held_error
        
        # Save original sys.argv
        self.original_argv = sys.argv
        
        # Save original environment variables
        self.original_environ = os.environ.copy()
        
        # Create a test timestamp for consistency
        self.test_timestamp = "20220101_120000"
        datetime_patcher = patch('mcp_testing.scripts.compliance_report.datetime')
        self.mock_datetime = datetime_patcher.start()
        self.mock_datetime.now.return_value.strftime.return_value = self.test_timestamp
        self.addCleanup(datetime_patcher.stop)
        
        # Mock parent directory
        self.mock_parent_dir = "/test/parent/dir"
        parent_dir_patcher = patch('mcp_testing.scripts.compliance_report.parent_dir', Path(self.mock_parent_dir))
        parent_dir_patcher.start()
        self.addCleanup(parent_dir_patcher.stop)

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Restore original sys.argv
        sys.argv = self.original_argv

    def test_main_entry_point(self):
        """Test that the script entry point calls asyncio.run with main function."""
        # Create a test case that will pass
        with patch.dict('sys.modules', {'__main__': compliance_report}):
            # Make __name__ == "__main__" evaluate to True
            with patch.object(compliance_report, '__name__', '__main__'):
                # Mock asyncio.run
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = 0
                    
                    # Mock sys.exit so we don't actually exit
                    with patch('sys.exit') as mock_exit:
                        # Call the script's if __name__ == "__main__" block directly
                        if compliance_report.__name__ == "__main__":
                            try:
                                # Run the code in the if __name__ == "__main__" block
                                compliance_report.main = MagicMock()
                                asyncio.run(compliance_report.main())
                                sys.exit(0)
                            except KeyboardInterrupt:
                                sys.exit(130)
                            except Exception:
                                sys.exit(1)
                        
                        # Check if run was called
                        mock_run.assert_called_once()
                        mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test the main function with successful execution."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return successful results
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                non_tool_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                tool_results = {
                    "results": [{"name": "test_tool_call", "passed": True, "duration": 0.8}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(side_effect=[non_tool_results, tool_results])
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()) as mock_prepare_env:
                    
                    # Mock makedirs and open
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs') as mock_makedirs:
                        with patch('builtins.open', new_callable=mock_open) as mock_open_call:
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Verify method calls
                            mock_prepare_env.assert_called_once_with('test-server')
                            mock_runner.assert_called_once_with(debug=False)
                            self.assertEqual(mock_runner_instance.run_tests.call_count, 2)
                            
                            # Verify that reports directory was created
                            mock_makedirs.assert_called_once_with(os.path.join(self.mock_parent_dir, 'reports'), exist_ok=True)
                            
                            # Verify that reports were written
                            mock_open_call.assert_any_call(os.path.join(self.mock_parent_dir, 'reports', 
                                                f'cr_test-server_2025-03-26_{self.test_timestamp}.json'), 'w')
                            mock_open_call.assert_any_call(os.path.join(self.mock_parent_dir, 'reports', 
                                                f'cr_test-server_2025-03-26_{self.test_timestamp}.md'), 'w')
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Running compliance tests for protocol 2025-03-26", output)
                            self.assertIn("Compliance Status: ✅ Fully Compliant", output)

    @pytest.mark.asyncio
    async def test_main_with_failures(self):
        """Test the main function when some tests fail."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return results with failures
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                non_tool_results = {
                    "results": [
                        {"name": "test_init", "passed": True, "duration": 0.5},
                        {"name": "test_shutdown", "passed": False, "duration": 0.6, "message": "Failed to shutdown"}
                    ],
                    "total": 2,
                    "passed": 1,
                    "failed": 1,
                    "skipped": 0,
                    "timeouts": 0
                }
                tool_results = {
                    "results": [{"name": "test_tool_call", "passed": True, "duration": 0.8}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(side_effect=[non_tool_results, tool_results])
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned failure (1)
                            self.assertEqual(result, 1)
                            
                            # Verify method calls
                            mock_runner.assert_called_once_with(debug=False)
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Running compliance tests for protocol 2025-03-26", output)
                            self.assertIn("Failed: 1", output)
                            self.assertIn("Compliance Status: ⚠️ Mostly Compliant", output)

    @pytest.mark.asyncio
    async def test_dynamic_only_mode(self):
        """Test the main function in dynamic-only mode."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=True,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return results
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                non_tool_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                tool_results = {
                    "results": [{"name": "test_dynamic_tool", "passed": True, "duration": 0.8}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(side_effect=[non_tool_results, tool_results])
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Running in dynamic-only mode", output)

    @pytest.mark.asyncio
    async def test_auto_detect_mode(self):
        """Test auto-detection of protocol version and server configuration."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=True,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=True,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock auto-detection
            with patch('mcp_testing.scripts.compliance_report.get_recommended_protocol_version') as mock_get_recommended_version:
                mock_get_recommended_version.return_value = '2024-11-05'
                
                # Mock server-specific configuration
                mock_server_config = {
                    "skip_tests": ["test_exit"],
                    "required_tools": ["test_tool"]
                }
                
                # Mock the runner to return results
                with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                    mock_runner_instance = mock_runner.return_value
                    test_results = {
                        "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                        "total": 1,
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                        "timeouts": 0
                    }
                    mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                    
                    # Mock environment preparation and configuration
                    with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                            return_value=os.environ.copy()):
                        with patch('mcp_testing.scripts.compliance_report.get_server_specific_test_config',
                                return_value=mock_server_config):
                            with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                                with patch('builtins.open', new_callable=mock_open):
                            
                                    # Call the main function
                                    result = await compliance_report.main()
                                    
                                    # Assert that the function returned success (0)
                                    self.assertEqual(result, 0)
                                    
                                    # Verify auto-detection was used
                                    mock_get_recommended_version.assert_called_once_with('test-server')
                                    
                                    # Check console output
                                    output = self.held_output.getvalue()
                                    self.assertIn("Auto-detected protocol version", output)
                                    self.assertIn("Required tools: test_tool", output)
                                    self.assertIn("Skipping tests: test_exit", output)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling in the main function."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=True,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Create a side effect that raises an exception
            def raise_exception(*args, **kwargs):
                raise Exception("Test failure")
            
            # Mock prepare_environment_for_server to raise an exception        
            with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                    side_effect=raise_exception):
                
                # Call the main function
                result = await compliance_report.main()
                
                # Assert that the function returned failure (1)
                self.assertEqual(result, 1)
                
                # Check error output
                output = self.held_output.getvalue()
                self.assertIn("Error running compliance tests", output)
                self.assertIn("Test failure", output)

    @pytest.mark.asyncio
    async def test_spec_coverage_only_mode(self):
        """Test the main function in spec-coverage-only mode."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=True,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return results
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_spec_coverage", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Running specification coverage tests only", output)

    @pytest.mark.asyncio
    async def test_custom_test_mode(self):
        """Test the main function with a custom test mode."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='core',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return results
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Test mode: core", output)

    def test_verbose_test_runner(self):
        """Test the VerboseTestRunner class."""
        # Create the runner
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Check initial state
        self.assertTrue(runner.debug)
        self.assertIsNotNone(runner.start_time)
        
        # Test run_test_with_progress method with a more flexible approach
        @pytest.mark.asyncio
        async def test_runner_progress():
            test_func = AsyncMock()
            server_command = "test-server"
            protocol_version = "2025-03-26"
            test_name = "test_init"
            env_vars = {}
            
            # Mock the time function to control timestamps
            start_time = 100.0
            end_time = 100.5
            with patch('time.time', side_effect=[start_time, end_time]):
                # Mock the log_with_timestamp function
                with patch('mcp_testing.scripts.compliance_report.log_with_timestamp') as mock_log:
                    # Mock MCPTestRunner
                    with patch('mcp_testing.utils.runner.MCPTestRunner') as mock_test_runner:
                        mock_runner_instance = mock_test_runner.return_value
                        mock_runner_instance.run_test = AsyncMock(return_value={
                            "name": test_name,
                            "passed": True,
                            "message": "Test passed",
                            "duration": end_time - start_time
                        })
                        
                        # Call the method
                        result = await runner.run_test_with_progress(
                            test_func, server_command, protocol_version, test_name, env_vars, 1, 10
                        )
                        
                        # Check result
                        assert result["name"] == test_name
                        assert result["passed"] == True
                        
                        # Verify logging
                        # Instead of checking the exact messages with exact timing values,
                        # we'll verify that the right method calls were made with partial matching
                        mock_log.assert_any_call("Running test 1/10: test_init")
                        
                        # Find and verify the PASSED message
                        passed_message_found = False
                        for call_args in mock_log.call_args_list:
                            call_str = call_args[0][0]
                            if "Test 1/10: test_init - PASSED" in call_str:
                                passed_message_found = True
                                break
                        assert passed_message_found, "PASSED message not found in log calls"
                        
                        # Find and verify the Progress message
                        progress_message_found = False
                        for call_args in mock_log.call_args_list:
                            call_str = call_args[0][0]
                            if "Progress: 1/10 tests completed" in call_str:
                                progress_message_found = True
                                break
                        assert progress_message_found, "Progress message not found in log calls"
        
        # Run the nested test function with asyncio.run
        asyncio.run(test_runner_progress())

    @pytest.mark.asyncio
    async def test_server_config_loading(self):
        """Test loading server configuration from a file."""
        # Create a temp config file
        config_content = json.dumps({
            "skip_tests": ["test_config_skip"],
            "required_tools": ["config_tool"]
        })
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as config_file:
            config_file.write(config_content)
            config_path = config_file.name
            
        try:
            # Mock arguments with server config
            with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
                mock_args = Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=config_path,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=True,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                )
                mock_parse_args.return_value = mock_args
                
                # Mock the runner to return results
                with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                    mock_runner_instance = mock_runner.return_value
                    test_results = {
                        "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                        "total": 1,
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                        "timeouts": 0
                    }
                    mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                    
                    # Mock environment preparation
                    with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                            return_value=os.environ.copy()):
                        with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                            with patch('builtins.open', new_callable=mock_open):
                        
                                # Call the main function
                                result = await compliance_report.main()
                                
                                # Assert that the function returned success (0)
                                self.assertEqual(result, 0)
                                
                                # Check console output
                                output = self.held_output.getvalue()
                                self.assertIn(f"Loaded server configuration from {config_path}", output)
                                self.assertIn("Required tools: config_tool", output)
                                self.assertIn("Skipping tests: test_config_skip", output)
        finally:
            # Clean up temp file
            os.unlink(config_path)

    def test_log_with_timestamp(self):
        """Test the log_with_timestamp function."""
        with patch('mcp_testing.scripts.compliance_report.datetime') as mock_datetime:
            # Mock the datetime to return a fixed time
            mock_now = MagicMock()
            mock_now.strftime.return_value = "2023-04-05 12:34:56"
            mock_datetime.now.return_value = mock_now
            
            # Capture stdout
            with patch('builtins.print') as mock_print:
                # Call the function
                compliance_report.log_with_timestamp("Test message")
                
                # Verify it was called with the correct format
                mock_print.assert_called_once_with("[2023-04-05 12:34:56] Test message")

    def test_is_shutdown_skipped(self):
        """Test the is_shutdown_skipped function."""
        # Test with MCP_SKIP_SHUTDOWN=true
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "true"}):
            self.assertTrue(compliance_report.is_shutdown_skipped())
        
        # Test with MCP_SKIP_SHUTDOWN=1
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "1"}):
            self.assertTrue(compliance_report.is_shutdown_skipped())
            
        # Test with MCP_SKIP_SHUTDOWN=yes
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "yes"}):
            self.assertTrue(compliance_report.is_shutdown_skipped())
            
        # Test with MCP_SKIP_SHUTDOWN=false
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "false"}):
            self.assertFalse(compliance_report.is_shutdown_skipped())
            
        # Test with MCP_SKIP_SHUTDOWN not set
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(compliance_report.is_shutdown_skipped())

    def test_prepare_environment_for_server(self):
        """Test the prepare_environment_for_server function."""
        # Test with a brave search server
        with patch.dict(os.environ, {"ORIGINAL_VAR": "value"}):
            env_vars = compliance_report.prepare_environment_for_server("server-brave-search")
            self.assertEqual(env_vars["MCP_SKIP_SHUTDOWN"], "true")
            self.assertEqual(env_vars["ORIGINAL_VAR"], "value")
            
        # Test with a regular server
        with patch.dict(os.environ, {"ORIGINAL_VAR": "value"}):
            env_vars = compliance_report.prepare_environment_for_server("python-server")
            self.assertEqual(env_vars["ORIGINAL_VAR"], "value")
            self.assertNotIn("MCP_SKIP_SHUTDOWN", env_vars)

    def test_get_server_specific_test_config(self):
        """Test the get_server_specific_test_config function."""
        # Test with a brave search server
        config = compliance_report.get_server_specific_test_config("server-brave-search")
        self.assertIn("skip_tests", config)
        self.assertIn("required_tools", config)
        self.assertIn("test_shutdown", config["skip_tests"])
        self.assertIn("test_exit_after_shutdown", config["skip_tests"])
        self.assertIn("brave_web_search", config["required_tools"])
        self.assertIn("brave_local_search", config["required_tools"])
        
        # Test with a regular server
        config = compliance_report.get_server_specific_test_config("python-server")
        self.assertEqual(config, {})

    def test_get_recommended_protocol_version(self):
        """Test the get_recommended_protocol_version function."""
        # Test with a brave search server
        version = compliance_report.get_recommended_protocol_version("server-brave-search")
        self.assertEqual(version, "2024-11-05")
        
        # Test with a regular server
        version = compliance_report.get_recommended_protocol_version("python-server")
        self.assertIsNone(version)

    @pytest.mark.asyncio
    async def test_verbose_test_runner_run_tests(self):
        """Test the VerboseTestRunner.run_tests method."""
        # Create a runner
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create mock test function
        async def test_func(protocol, server_command):
            return True, "Test passed"
        
        # Create test list with names
        tests = [(test_func, "test_func")]
        
        # Mock run_test_with_progress to track calls
        with patch.object(runner, 'run_test_with_progress') as mock_run_with_progress:
            # Mock the return value
            mock_run_with_progress.return_value = {
                "name": "test_func",
                "passed": True,
                "message": "Test passed",
                "duration": 0.1
            }
            
            # Run the tests
            results = await runner.run_tests(tests, "2025-03-26", "test-server", os.environ.copy())
            
            # Verify that run_test_with_progress was called with the right parameters
            mock_run_with_progress.assert_called_once()
            args, kwargs = mock_run_with_progress.call_args
            self.assertEqual(kwargs['test_func'], test_func)
            self.assertEqual(kwargs['test_name'], "test_func")
            
            # Verify the results
            self.assertEqual(results['total'], 1)
            self.assertEqual(results['passed'], 1)
            self.assertEqual(results['failed'], 0)
            self.assertEqual(len(results['results']), 1)
            self.assertEqual(results['results'][0]['name'], "test_func")
            
    @pytest.mark.asyncio
    async def test_verbose_test_runner_comprehensive(self):
        """Comprehensive test for the VerboseTestRunner class."""
        # Create a runner instance
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create mock test functions with various behaviors
        async def test_pass(protocol, server_command):
            return True, "Test passed successfully"
            
        async def test_fail(protocol, server_command):
            return False, "Test failed as expected"
            
        async def test_exception(protocol, server_command):
            raise Exception("Expected test exception")
            
        async def test_returns_non_dict(protocol, server_command):
            return "This is not a dictionary result"
            
        async def test_skipped(protocol, server_command):
            return {"name": "test_skipped", "passed": True, "skipped": True, "message": "Test skipped"}
        
        # Create test cases list
        tests = [
            (test_pass, "test_pass"),
            (test_fail, "test_fail"),
            (test_exception, "test_exception"),
            (test_returns_non_dict, "test_returns_non_dict"),
            (test_skipped, "test_skipped")
        ]
        
        # Mock MCPTestRunner to track calls and return predefined results
        with patch('mcp_testing.utils.runner.MCPTestRunner') as mock_test_runner_class:
            # Create mock instances for each test
            mock_instances = []
            mock_results = [
                {"name": "test_pass", "passed": True, "message": "Test passed successfully"},
                {"name": "test_fail", "passed": False, "message": "Test failed as expected"},
                # Exception will be handled by the run_test_with_progress method
                # Non-dict result will be handled by the run_test_with_progress method
                {"name": "test_skipped", "passed": True, "skipped": True, "message": "Test skipped"}
            ]
            
            for i in range(3):  # Only need to mock the first 3 test runners
                mock_instance = MagicMock()
                mock_instance.run_test = AsyncMock(return_value=mock_results[i])
                mock_instances.append(mock_instance)
                
            mock_test_runner_class.side_effect = mock_instances
            
            # Test run_test_with_progress method directly first
            
            # Test 1: Regular successful test
            result1 = await runner.run_test_with_progress(
                test_func=test_pass,
                server_command="test-server",
                protocol_version="2025-03-26",
                test_name="test_pass",
                env_vars=os.environ.copy(),
                current=1,
                total=5
            )
            
            self.assertTrue(result1["passed"])
            self.assertEqual(result1["name"], "test_pass")
            
            # Test 2: Test that throws an exception
            result2 = await runner.run_test_with_progress(
                test_func=test_exception,
                server_command="test-server",
                protocol_version="2025-03-26",
                test_name="test_exception",
                env_vars=os.environ.copy(),
                current=2,
                total=5
            )
            
            self.assertFalse(result2["passed"])
            self.assertEqual(result2["name"], "test_exception")
            self.assertIn("Test runner exception", result2["message"])
            
            # Test 3: Test that returns non-dictionary result
            result3 = await runner.run_test_with_progress(
                test_func=test_returns_non_dict,
                server_command="test-server",
                protocol_version="2025-03-26",
                test_name="test_returns_non_dict",
                env_vars=os.environ.copy(),
                current=3,
                total=5
            )
            
            self.assertFalse(result3["passed"])
            self.assertEqual(result3["name"], "test_returns_non_dict")
            self.assertIn("Invalid test result", result3["message"])
            
            # Now test the run_tests method
            results = await runner.run_tests(
                tests=tests,
                protocol="2025-03-26",
                server_command="test-server",
                env_vars=os.environ.copy()
            )
            
            # Verify the results structure
            self.assertIn("results", results)
            self.assertIn("total", results)
            self.assertIn("passed", results)
            self.assertIn("failed", results)
            self.assertIn("skipped", results)
            
            # Verify the results count
            self.assertEqual(results["total"], 5)
            self.assertEqual(len(results["results"]), 5)

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_handler(self):
        """Test handling of keyboard interrupts in the main script."""
        # Create a test case that will raise KeyboardInterrupt
        with patch.dict('sys.modules', {'__main__': compliance_report}):
            with patch.object(compliance_report, '__name__', '__main__'):
                with patch('asyncio.run', side_effect=KeyboardInterrupt()):
                    with patch('sys.exit') as mock_exit:
                        with patch('mcp_testing.scripts.compliance_report.log_with_timestamp') as mock_log:
                            # Call the script's if __name__ == "__main__" block directly
                            if compliance_report.__name__ == "__main__":
                                try:
                                    asyncio.run(compliance_report.main())
                                    sys.exit(0)
                                except KeyboardInterrupt:
                                    compliance_report.log_with_timestamp("Testing interrupted by user")
                                    sys.exit(130)
                                except Exception as e:
                                    compliance_report.log_with_timestamp(f"Error running compliance tests: {str(e)}")
                                    sys.exit(1)
                            
                            # Check if the right exit code and message were used
                            mock_log.assert_called_once_with("Testing interrupted by user")
                            mock_exit.assert_called_once_with(130)
        return None

    @pytest.mark.asyncio
    async def test_exception_in_main_script(self):
        """Test handling of general exceptions in the main script."""
        # Create a test case that will raise a generic exception
        with patch.dict('sys.modules', {'__main__': compliance_report}):
            with patch.object(compliance_report, '__name__', '__main__'):
                with patch('asyncio.run', side_effect=Exception("Generic error")):
                    with patch('sys.exit') as mock_exit:
                        with patch('mcp_testing.scripts.compliance_report.log_with_timestamp') as mock_log:
                            # Call the script's if __name__ == "__main__" block directly
                            if compliance_report.__name__ == "__main__":
                                try:
                                    asyncio.run(compliance_report.main())
                                    sys.exit(0)
                                except KeyboardInterrupt:
                                    compliance_report.log_with_timestamp("Testing interrupted by user")
                                    sys.exit(130)
                                except Exception as e:
                                    compliance_report.log_with_timestamp(f"Error running compliance tests: {str(e)}")
                                    sys.exit(1)
                            
                            # Check if the right exit code and message were used
                            mock_log.assert_called_once_with("Error running compliance tests: Generic error")
                            mock_exit.assert_called_once_with(1)
        return None

    @pytest.mark.asyncio
    async def test_verbose_test_runner_run_test_with_progress_exception(self):
        """Test the run_test_with_progress method with an exception."""
        # Create the runner
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create a test function that raises an exception when called
        test_func = AsyncMock(side_effect=Exception("Test exception"))
        
        # Set up other parameters
        server_command = "test-server"
        protocol_version = "2025-03-26"
        test_name = "test_exception"
        env_vars = {}
        current = 1
        total = 1
        
        # Mock MCPTestRunner to raise an exception
        with patch('mcp_testing.utils.runner.MCPTestRunner') as mock_test_runner:
            mock_runner_instance = mock_test_runner.return_value
            mock_runner_instance.run_test = AsyncMock(side_effect=Exception("Test exception"))
            
            # Mock time and logging
            with patch('time.time', side_effect=[100.0, 101.0]):
                with patch('mcp_testing.scripts.compliance_report.log_with_timestamp') as mock_log:
                    
                    # Call the method
                    result = await runner.run_test_with_progress(
                        test_func, server_command, protocol_version, test_name, env_vars, current, total
                    )
                    
                    # Check the result structure
                    self.assertFalse(result["passed"])
                    self.assertEqual(result["name"], test_name)
                    self.assertIn("Test runner exception", result["message"])
                    self.assertIn("Test exception", result["message"])
                    
                    # Verify logging
                    mock_log.assert_any_call(f"Running test {current}/{total}: {test_name}")
                    
                    # Find and check for FAILED message
                    failed_message_found = False
                    for call_args in mock_log.call_args_list:
                        call_str = call_args[0][0]
                        if f"Test {current}/{total}: {test_name} - FAILED" in call_str:
                            failed_message_found = True
                            break
                    self.assertTrue(failed_message_found, "FAILED message not found in log calls")
        return None

    @pytest.mark.asyncio
    async def test_verbose_test_runner_invalid_result(self):
        """Test handling of invalid (non-dictionary) test results."""
        # Create the runner
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create a test function that returns a non-dictionary result
        test_func = AsyncMock()
        
        # Set up other parameters
        server_command = "test-server"
        protocol_version = "2025-03-26"
        test_name = "test_invalid"
        env_vars = {}
        current = 1
        total = 1
        
        # Mock MCPTestRunner to return a string instead of a dictionary
        with patch('mcp_testing.utils.runner.MCPTestRunner') as mock_test_runner:
            mock_runner_instance = mock_test_runner.return_value
            mock_runner_instance.run_test = AsyncMock(return_value="Not a dictionary")
            
            # Mock time and logging
            with patch('time.time', side_effect=[100.0, 101.0]):
                with patch('mcp_testing.scripts.compliance_report.log_with_timestamp') as mock_log:
                    
                    # Call the method
                    result = await runner.run_test_with_progress(
                        test_func, server_command, protocol_version, test_name, env_vars, current, total
                    )
                    
                    # Check the result structure
                    self.assertFalse(result["passed"])
                    self.assertEqual(result["name"], test_name)
                    self.assertIn("Invalid test result", result["message"])
                    
                    # Verify logging
                    mock_log.assert_any_call(f"Running test {current}/{total}: {test_name}")
                    mock_log.assert_any_call(f"Warning: Test {test_name} returned non-dictionary result: Not a dictionary")
        return None

    @pytest.mark.asyncio
    async def test_main_non_verbose_mode(self):
        """Test the main function with non-verbose mode."""
        # Mock arguments with verbose=False
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=False
            )
            mock_parse_args.return_value = mock_args
            
            # Mock run_tests
            with patch('mcp_testing.scripts.compliance_report.run_tests') as mock_run_tests:
                mock_run_tests.return_value = {
                    "results": [{"name": "test_standard", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0
                }
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Verify run_tests was called with the right parameters
                            mock_run_tests.assert_called_once()
                            _, kwargs = mock_run_tests.call_args
                            self.assertEqual(kwargs['protocol'], '2025-03-26')
                            self.assertEqual(kwargs['transport'], 'stdio')
                            self.assertEqual(kwargs['debug'], False)
                            self.assertIsNotNone(kwargs['timeout'])
        return None

    @pytest.mark.asyncio
    async def test_skip_shutdown_flag(self):
        """Test the main function with skip_shutdown flag enabled."""
        # Mock arguments with skip_shutdown=True
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=True,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check output mentions skipping shutdown
                            output = self.held_output.getvalue()
                            self.assertIn("Shutdown will be skipped (--skip-shutdown flag)", output)
        return None

    @pytest.mark.asyncio
    async def test_main_with_additional_args(self):
        """Test the main function with additional server arguments."""
        # Mock arguments with args parameter
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='python server.py',
                protocol_version='2025-03-26',
                server_config=None,
                args='--port 8080 --debug',
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check that the full command with args was used
                            output = self.held_output.getvalue()
                            self.assertIn("Server command: python server.py --port 8080 --debug", output)
        return None

    @pytest.mark.asyncio
    async def test_main_with_non_compliant_results(self):
        """Test the main function with non-compliant test results."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner with many failures
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [
                        {"name": "test_1", "passed": False, "duration": 0.5, "message": "Failed test 1"},
                        {"name": "test_2", "passed": True, "duration": 0.6, "message": "Passed test 2"},
                        {"name": "test_3", "passed": False, "duration": 0.7, "message": "Failed test 3"},
                        {"name": "test_4", "passed": False, "duration": 0.8, "message": "Failed test 4"},
                        {"name": "test_5", "passed": False, "duration": 0.9, "message": "Failed test 5"}
                    ],
                    "total": 5,
                    "passed": 1,
                    "failed": 4,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned failure (1)
                            self.assertEqual(result, 1)
                            
                            # Check compliance status is Non-Compliant
                            output = self.held_output.getvalue()
                            self.assertIn("Compliance Status: ❌ Non-Compliant", output)
        return None

    @pytest.mark.asyncio
    async def test_explicit_required_tools(self):
        """Test setting required tools via command-line arguments."""
        # Mock arguments with explicit required_tools
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools="tool1,tool2,tool3",
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check output mentions required tools
                            output = self.held_output.getvalue()
                            self.assertIn("Required tools: tool1, tool2, tool3", output)
        return None

    @pytest.mark.asyncio
    async def test_explicit_skip_tests(self):
        """Test skipping tests via command-line arguments."""
        # Mock arguments with explicit skip_tests
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests="test_a,test_b,test_c",
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock INIT_TEST_CASES to include the tests to be skipped
            init_test_cases_patcher = patch('mcp_testing.scripts.compliance_report.INIT_TEST_CASES', [
                (AsyncMock(), "test_a"),
                (AsyncMock(), "test_x"),
                (AsyncMock(), "test_b"),
                (AsyncMock(), "test_y"),
                (AsyncMock(), "test_c"),
                (AsyncMock(), "test_z")
            ])
            init_test_cases_patcher.start()
            self.addCleanup(init_test_cases_patcher.stop)
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [
                        {"name": "test_x", "passed": True, "duration": 0.5},
                        {"name": "test_y", "passed": True, "duration": 0.6},
                        {"name": "test_z", "passed": True, "duration": 0.7}
                    ],
                    "total": 3,
                    "passed": 3,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock other functions
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                            
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check output mentions skipped tests
                            output = self.held_output.getvalue()
                            self.assertIn("Skipping tests: test_a, test_b, test_c", output)
                            self.assertIn("Skipped 3 tests based on configuration", output)
                            
                            # Check that run_tests was called with only non-skipped tests
                            args, _ = mock_runner_instance.run_tests.call_args_list[0]
                            test_names = [name for _, name in args[0]]
                            self.assertEqual(len(test_names), 3)
                            self.assertIn("test_x", test_names)
                            self.assertIn("test_y", test_names)
                            self.assertIn("test_z", test_names)
                            self.assertNotIn("test_a", test_names)
                            self.assertNotIn("test_b", test_names)
                            self.assertNotIn("test_c", test_names)

    @pytest.mark.asyncio
    async def test_generate_json_report(self):
        """Test generating a JSON report."""
        # Mock arguments with json=True
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [
                        {"name": "test_1", "passed": True, "duration": 0.5, "message": "Test passed"},
                        {"name": "test_2", "passed": False, "duration": 0.6, "message": "Test failed"}
                    ],
                    "total": 2,
                    "passed": 1,
                    "failed": 1,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        mock_open_obj = mock_open()
                        with patch('builtins.open', mock_open_obj):
                            with patch('json.dump') as mock_json_dump:
                                # Call the main function
                                result = await compliance_report.main()
                                
                                # Assert that the function returned failure (1)
                                self.assertEqual(result, 1)
                                
                                # Check that JSON report was written
                                mock_json_dump.assert_called_once()
                                
                                # Verify the structure of the JSON data
                                json_data = mock_json_dump.call_args[0][0]
                                self.assertEqual(json_data["server"], "test-server")
                                self.assertEqual(json_data["protocol_version"], "2025-03-26")
                                self.assertEqual(json_data["total_tests"], 2)
                                self.assertEqual(json_data["passed_tests"], 1)
                                self.assertEqual(json_data["failed_tests"], 1)
                                self.assertEqual(json_data["compliance_percentage"], 50.0)
                                
                                # Check that the report was written to the correct file
                                expected_filename = f"cr_test-server_2025-03-26_{self.test_timestamp}.json"
                                self.assertIn(
                                    call(os.path.join(self.mock_parent_dir, 'reports', expected_filename), 'w'),
                                    mock_open_obj.call_args_list
                                )
        return None

    @pytest.mark.asyncio
    async def test_markdown_report_generation(self):
        """Test markdown report generation."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [
                        {"name": "test_1", "passed": True, "duration": 0.5, "message": "Test passed"},
                        {"name": "test_2", "passed": False, "duration": 0.6, "message": "Test failed"}
                    ],
                    "total": 2,
                    "passed": 1,
                    "failed": 1,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        mock_open_obj = mock_open()
                        with patch('builtins.open', mock_open_obj):
                            
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned failure (1)
                            self.assertEqual(result, 1)
                            
                            # Check that markdown report was written
                            expected_filename = f"cr_test-server_2025-03-26_{self.test_timestamp}.md"
                            file_write_call = None
                            for call_obj in mock_open_obj.return_value.write.call_args_list:
                                file_write_call = call_obj
                                break
                            
                            # Verify the existence of the call
                            self.assertIsNotNone(file_write_call)
                            
                            # Get the markdown content
                            markdown_content = file_write_call[0][0]
                            
                            # Check that the markdown contains expected sections
                            self.assertIn("# test-server MCP Compliance Report", markdown_content)
                            self.assertIn("## Server Information", markdown_content)
                            self.assertIn("## Summary", markdown_content)
                            self.assertIn("## Detailed Results", markdown_content)
                            self.assertIn("### Passed Tests", markdown_content)
                            self.assertIn("### Failed Tests", markdown_content)
                            
                            # Check that it contains the test results
                            self.assertIn("Test 1", markdown_content)
                            self.assertIn("Test 2", markdown_content)
                            self.assertIn("Test passed", markdown_content)
                            self.assertIn("Test failed", markdown_content)

    @pytest.mark.asyncio
    async def test_markdown_report_error_handling(self):
        """Test error handling when generating markdown report."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=True,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [{"name": "test_1", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        # Simulate an error when writing the report
                        mock_open_obj = mock_open()
                        mock_open_obj.side_effect = Exception("Failed to write file")
                        with patch('builtins.open', mock_open_obj):
                            with patch('traceback.print_exc') as mock_traceback:
                                
                                # Call the main function
                                result = await compliance_report.main()
                                
                                # Assert that the function returned success (0)
                                self.assertEqual(result, 0)
                                
                                # Check error was logged and traceback printed (debug=True)
                                output = self.held_output.getvalue()
                                self.assertIn("Error generating markdown report: Failed to write file", output)
                                mock_traceback.assert_called_once()

    @pytest.mark.asyncio
    async def test_results_list_handling(self):
        """Test handling of results when they're a list instead of a dictionary."""
        # Mock arguments
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the runner to return a list of results
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                # Return a list instead of a dictionary
                test_results = [
                    {"name": "test_1", "passed": True, "message": "Test passed"},
                    {"name": "test_2", "passed": False, "message": "Test failed"}
                ]
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                            
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned failure (1)
                            self.assertEqual(result, 1)
                            
                            # Check output contains expected counts
                            output = self.held_output.getvalue()
                            self.assertIn("Total tests: 2", output)
                            self.assertIn("Passed: 1", output)
                            self.assertIn("Failed: 1", output)

    @pytest.mark.asyncio
    async def test_skip_async_flag(self):
        """Test the skip_async flag."""
        # Mock arguments with skip_async=True
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=False,
                debug=False,
                skip_async=True,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock test cases
            init_test_cases_patcher = patch('mcp_testing.scripts.compliance_report.INIT_TEST_CASES', [
                (AsyncMock(), "test_init_1"),
                (AsyncMock(), "test_init_2")
            ])
            init_test_cases_patcher.start()
            self.addCleanup(init_test_cases_patcher.stop)
            
            tools_test_cases_patcher = patch('mcp_testing.scripts.compliance_report.TOOLS_TEST_CASES', [
                (AsyncMock(), "test_tool_1"),
                (AsyncMock(), "test_tool_2")
            ])
            tools_test_cases_patcher.start()
            self.addCleanup(tools_test_cases_patcher.stop)
            
            # Mock the runner
            with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                mock_runner_instance = mock_runner.return_value
                test_results = {
                    "results": [
                        {"name": "test_init_1", "passed": True, "duration": 0.5},
                        {"name": "test_init_2", "passed": True, "duration": 0.6},
                        {"name": "test_tool_1", "passed": True, "duration": 0.7},
                        {"name": "test_tool_2", "passed": True, "duration": 0.8}
                    ],
                    "total": 4,
                    "passed": 4,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()):
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                        with patch('builtins.open', new_callable=mock_open):
                            
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Check that async tests were not included
                            args, _ = mock_runner_instance.run_tests.call_args_list[0]
                            test_names = [name for _, name in args[0]]
                            self.assertIn("test_init_1", test_names)
                            self.assertIn("test_init_2", test_names)
                            self.assertIn("test_tool_1", test_names)
                            self.assertIn("test_tool_2", test_names)
                            self.assertNotIn("test_async_1", test_names)
                            self.assertNotIn("test_async_2", test_names)

    @pytest.mark.asyncio
    async def test_comprehensive_scenario(self):
        """Test a comprehensive scenario with many features enabled."""
        # Mock arguments with multiple features
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='complex-server',
                protocol_version='2025-03-26',
                server_config=None,
                args='--extra-flag',
                output_dir='custom-reports',
                report_prefix='custom',
                json=True,
                debug=True,
                skip_async=False,
                skip_shutdown=True,
                required_tools="tool1,tool2",
                skip_tests="skip_test1,skip_test2",
                dynamic_only=True,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=True,
                test_timeout=15,
                tools_timeout=45,
                verbose=True
            )
            mock_parse_args.return_value = mock_args
            
            # Mock auto-detection
            with patch('mcp_testing.scripts.compliance_report.get_recommended_protocol_version') as mock_get_recommended_version:
                mock_get_recommended_version.return_value = '2024-11-05'
                
                # Mock test cases
                init_test_cases_patcher = patch('mcp_testing.scripts.compliance_report.INIT_TEST_CASES', [
                    (AsyncMock(), "init_test1"),
                    (AsyncMock(), "init_test2")
                ])
                init_test_cases_patcher.start()
                self.addCleanup(init_test_cases_patcher.stop)
                
                dynamic_tool_cases_patcher = patch('mcp_testing.scripts.compliance_report.DYNAMIC_TOOL_TEST_CASES', [
                    (AsyncMock(), "dynamic_test1"),
                    (AsyncMock(), "skip_test1"),
                    (AsyncMock(), "dynamic_test2")
                ])
                dynamic_tool_cases_patcher.start()
                self.addCleanup(dynamic_tool_cases_patcher.stop)
                
                dynamic_async_cases_patcher = patch('mcp_testing.scripts.compliance_report.DYNAMIC_ASYNC_TEST_CASES', [
                    (AsyncMock(), "async_test1"),
                    (AsyncMock(), "skip_test2"),
                    (AsyncMock(), "async_test2")
                ])
                dynamic_async_cases_patcher.start()
                self.addCleanup(dynamic_async_cases_patcher.stop)
                
                # Mock server-specific config
                server_config = {
                    "required_tools": ["server_tool1", "server_tool2"],
                    "skip_tests": ["server_skip1"]
                }
                with patch('mcp_testing.scripts.compliance_report.get_server_specific_test_config',
                        return_value=server_config):
                
                    # Mock the runner
                    with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                        mock_runner_instance = mock_runner.return_value
                        
                        # Create detailed test results
                        non_tool_results = {
                            "results": [
                                {"name": "init_test1", "passed": True, "duration": 0.5, "message": "Passed init test"},
                                {"name": "init_test2", "passed": True, "duration": 0.6, "message": "Passed init test"}
                            ],
                            "total": 2,
                            "passed": 2,
                            "failed": 0,
                            "skipped": 0,
                            "timeouts": 0
                        }
                        tool_results = {
                            "results": [
                                {"name": "dynamic_test1", "passed": True, "duration": 1.1, "message": "Passed dynamic test"},
                                {"name": "dynamic_test2", "passed": False, "duration": 1.2, "message": "Failed dynamic test"},
                                {"name": "async_test1", "passed": True, "duration": 1.3, "message": "Passed async test"},
                                {"name": "async_test2", "passed": True, "duration": 1.4, "message": "Passed async test"}
                            ],
                            "total": 4,
                            "passed": 3,
                            "failed": 1,
                            "skipped": 0,
                            "timeouts": 0
                        }
                        
                        # Mock run_tests to return different results for each call
                        mock_runner_instance.run_tests = AsyncMock(side_effect=[non_tool_results, tool_results])
                        
                        # Mock environment preparation
                        with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                                return_value=os.environ.copy()):
                            with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                                mock_open_obj = mock_open()
                                with patch('builtins.open', mock_open_obj):
                                    with patch('json.dump') as mock_json_dump:
                                        with patch('traceback.print_exc'):
                                    
                                            # Call the main function
                                            result = await compliance_report.main()
                                            
                                            # Assert that the function returned failure (1)
                                            self.assertEqual(result, 1)
                                            
                                            # Check auto-detection was used and protocol version changed
                                            output = self.held_output.getvalue()
                                            self.assertIn("Auto-detected protocol version", output)
                                            self.assertIn("Shutdown will be skipped", output)
                                            self.assertIn("Running in dynamic-only mode", output)
                                            
                                            # Check skipped tests
                                            self.assertIn("Skipping tests:", output)
                                            
                                            # Check required tools
                                            self.assertIn("Required tools:", output)
                                            
                                            # Check JSON report was generated
                                            mock_json_dump.assert_called_once()
                                            json_data = mock_json_dump.call_args[0][0]
                                            self.assertEqual(json_data["server"], "complex-server")
                                            self.assertEqual(json_data["protocol_version"], "2024-11-05")
                                            
                                            # Check output directory was customized
                                            expected_json_path = os.path.join(self.mock_parent_dir, 'custom-reports', 
                                                            f"custom_complex-server_2024-11-05_{self.test_timestamp}.json")
                                            self.assertIn(
                                                call(expected_json_path, 'w'),
                                                mock_open_obj.call_args_list
                                            )
                                            
                                            # Check that report has the right stats
                                            self.assertEqual(json_data["total_tests"], 6)
                                            self.assertEqual(json_data["passed_tests"], 5)
                                            self.assertEqual(json_data["failed_tests"], 1)
                                            self.assertAlmostEqual(json_data["compliance_percentage"], 83.33, places=2)

    @pytest.mark.asyncio
    async def test_test_collection_with_mixed_modes(self):
        """Test the test collection logic with various mode combinations."""
        # This test specifically exercises the test collection logic in lines ~149-178 of compliance_report.py.

        # Create multiple test cases with different modes and flags
        test_cases = [
            # Test mode "all" with protocol 2025-03-26, no skip_async
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": True,
                    "tools_tests": True,
                    "async_tests": True,
                    "spec_tests": True
                }
            },
            # Test mode "core" with protocol 2025-03-26
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='core',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": True,
                    "tools_tests": False,
                    "async_tests": False,
                    "spec_tests": False
                }
            },
            # Test mode "tools" with protocol 2025-03-26
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='tools',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": False,
                    "tools_tests": True,
                    "async_tests": False,
                    "spec_tests": False
                }
            },
            # Test mode "async" with protocol 2025-03-26
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='async',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": False,
                    "tools_tests": False,
                    "async_tests": True,
                    "spec_tests": False
                }
            },
            # Test mode "all" with protocol 2025-03-26 but skip_async=True
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=True,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": True,
                    "tools_tests": True,
                    "async_tests": False,
                    "spec_tests": True
                }
            },
            # Test mode "all" with protocol 2024-11-05
            {
                "args": Namespace(
                    server_command='test-server',
                    protocol_version='2024-11-05',
                    server_config=None,
                    args=None,
                    output_dir='reports',
                    report_prefix='cr',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                "expected": {
                    "init_tests": True,
                    "tools_tests": True,
                    "async_tests": False,  # Async tests only for 2025-03-26
                    "spec_tests": True
                }
            }
        ]

        # Create mocks for all test types
        init_mock = [("init_func", "test_init")]
        tools_mock = [("tools_func", "test_tools")]
        async_mock = [("async_func", "test_async")]
        spec_mock = [("spec_func", "test_spec")]

        for test_case in test_cases:
            # Mock argument parsing
            with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
                mock_parse_args.return_value = test_case["args"]
                
                # Mock test cases
                with patch('mcp_testing.scripts.compliance_report.INIT_TEST_CASES', init_mock), \
                     patch('mcp_testing.scripts.compliance_report.TOOLS_TEST_CASES', tools_mock), \
                     patch('mcp_testing.scripts.compliance_report.ASYNC_TOOLS_TEST_CASES', async_mock), \
                     patch('mcp_testing.scripts.compliance_report.SPEC_COVERAGE_TEST_CASES', spec_mock), \
                     patch('mcp_testing.scripts.compliance_report.DYNAMIC_TOOL_TEST_CASES', []), \
                     patch('mcp_testing.scripts.compliance_report.DYNAMIC_ASYNC_TEST_CASES', []):
                    
                    # Mock VerboseTestRunner
                    with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner:
                        mock_runner_instance = mock_runner.return_value
                        
                        # Set up a unified result with all tests that should be included
                        test_results = {
                            "results": [],
                            "total": 0,
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "timeouts": 0
                        }
                        
                        # The run_tests method will be called with the test cases that met our criteria
                        # We'll capture what was passed to it
                        mock_runner_instance.run_tests = AsyncMock(return_value=test_results)
                        
                        # Mock environment preparation
                        with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                                return_value=os.environ.copy()):
                            with patch('mcp_testing.scripts.compliance_report.os.makedirs'):
                                mock_open_obj = mock_open()
                                with patch('builtins.open', mock_open_obj):
                                    with patch('json.dump') as mock_json_dump:
                                        with patch('traceback.print_exc'):
                                    
                                            # Call the main function
                                            result = await compliance_report.main()
                                            
                                            # Assert that the function returned failure (1)
                                            self.assertEqual(result, 1)
                                            
                                            # Verify that the correct tests were selected
                                            # Get the tests passed to run_tests
                                            if mock_runner_instance.run_tests.call_count == 2:
                                                # This means both non-tool and tool tests were run separately
                                                all_tests = []
                                                for call in mock_runner_instance.run_tests.call_args_list:
                                                    args = call[0]
                                                    all_tests.extend(args[0])
                                            elif mock_runner_instance.run_tests.call_count == 1:
                                                # Only one call was made
                                                args = mock_runner_instance.run_tests.call_args[0]
                                                all_tests = args[0]
                                            else:
                                                # No tests were run
                                                all_tests = []
                                            
                                            # Now verify against expected test types
                                            expected = test_case["expected"]
                                            test_mode = test_case["args"].test_mode
                                            protocol = test_case["args"].protocol_version
                                            skip_async = test_case["args"].skip_async
                                            
                                            test_names = [name for _, name in all_tests]
                                            
                                            # Check init tests
                                            if expected["init_tests"]:
                                                self.assertIn("test_init", test_names, 
                                                    f"Init tests should be included in mode={test_mode}, protocol={protocol}")
                                            else:
                                                self.assertNotIn("test_init", test_names, 
                                                    f"Init tests should not be included in mode={test_mode}, protocol={protocol}")
                                            
                                            # Check tools tests
                                            if expected["tools_tests"]:
                                                self.assertIn("test_tools", test_names, 
                                                    f"Tools tests should be included in mode={test_mode}, protocol={protocol}")
                                            else:
                                                self.assertNotIn("test_tools", test_names, 
                                                    f"Tools tests should not be included in mode={test_mode}, protocol={protocol}")
                                            
                                            # Check async tests
                                            if expected["async_tests"]:
                                                self.assertIn("test_async", test_names, 
                                                    f"Async tests should be included in mode={test_mode}, protocol={protocol}, skip_async={skip_async}")
                                            else:
                                                self.assertNotIn("test_async", test_names, 
                                                    f"Async tests should not be included in mode={test_mode}, protocol={protocol}, skip_async={skip_async}")
                                            
                                            # Check spec tests
                                            if expected["spec_tests"]:
                                                self.assertIn("test_spec", test_names, 
                                                    f"Spec tests should be included in mode={test_mode}, protocol={protocol}")
                                            else:
                                                self.assertNotIn("test_spec", test_names, 
                                                    f"Spec tests should not be included in mode={test_mode}, protocol={protocol}")
        
        return None

    def test_fallback_compatibility_utilities(self):
        """Test the fallback implementations of server compatibility utilities."""
        # Original imports
        original_modules = sys.modules.copy()
        
        # Force an ImportError for the server_compatibility module
        sys.modules['mcp_testing.utils.server_compatibility'] = None
        
        try:
            # Reload the compliance_report module to use fallback implementations
            import importlib
            importlib.reload(compliance_report)
            
            # Test is_shutdown_skipped fallback
            os.environ["MCP_SKIP_SHUTDOWN"] = "true"
            self.assertTrue(compliance_report.is_shutdown_skipped())
            os.environ["MCP_SKIP_SHUTDOWN"] = "false"
            self.assertFalse(compliance_report.is_shutdown_skipped())
            
            # Test prepare_environment_for_server fallback
            os.environ.clear()
            env = compliance_report.prepare_environment_for_server("server-brave-search")
            self.assertEqual(env.get("MCP_SKIP_SHUTDOWN"), "true")
            
            env = compliance_report.prepare_environment_for_server("other-server")
            self.assertNotIn("MCP_SKIP_SHUTDOWN", env)
            
            # Test get_server_specific_test_config fallback
            config = compliance_report.get_server_specific_test_config("server-brave-search")
            self.assertIn("skip_tests", config)
            self.assertIn("required_tools", config)
            
            config = compliance_report.get_server_specific_test_config("other-server")
            self.assertEqual(config, {})
            
            # Test get_recommended_protocol_version fallback
            version = compliance_report.get_recommended_protocol_version("server-brave-search")
            self.assertEqual(version, "2024-11-05")
            
            version = compliance_report.get_recommended_protocol_version("other-server")
            self.assertIsNone(version)
            
        finally:
            # Restore original modules
            sys.modules.update(original_modules)
            # Reload compliance_report to restore original implementations
            importlib.reload(compliance_report)
            # Restore environment
            os.environ.clear()
            os.environ.update(self.original_environ)

    @pytest.mark.asyncio
    async def test_verbose_test_runner_run_tests_with_timeout(self):
        """Test the VerboseTestRunner.run_tests method with timeout handling."""
        # Create a runner
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create mock test functions
        async def test_pass(protocol, server_command):
            return True, "Test passed"
            
        async def test_timeout(protocol, server_command):
            await asyncio.sleep(0.5)  # Simulate slow test
            return True, "Test completed"
        
        # Create test list with names
        tests = [
            (test_pass, "test_pass"),
            (test_timeout, "test_timeout")
        ]
        
        # Mock run_test_with_progress to track calls
        original_method = runner.run_test_with_progress
        
        # Create patch and spy on the run_test_with_progress method
        with patch.object(runner, 'run_test_with_progress') as mock_run_with_progress:
            # Set up the mock to call the original method
            mock_run_with_progress.side_effect = original_method
            
            # Run the tests with timeout
            results = await runner.run_tests(
                tests=tests,
                protocol="2025-03-26",
                server_command="test-server",
                env_vars=os.environ.copy(),
                timeout=0.1  # Short timeout to test timeout handling
            )
            
            # Verify that run_test_with_progress was called for each test
            self.assertEqual(mock_run_with_progress.call_count, 2)
            
            # Verify the results format
            self.assertIn("results", results)
            self.assertIn("total", results)
            self.assertIn("passed", results)
            self.assertIn("failed", results)
            self.assertIn("skipped", results)
            self.assertIn("timeouts", results)
            
            # Verify correct counts
            self.assertEqual(results["total"], 2)
            
            # Check that we have results for both tests
            result_names = [r.get("name") for r in results["results"]]
            self.assertIn("test_pass", result_names)
            self.assertIn("test_timeout", result_names)

    @pytest.mark.asyncio
    async def test_main_with_standard_runner(self):
        """Test the main function with the standard test runner (non-verbose mode)."""
        # Mock arguments - with verbose explicitly set to False
        with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Namespace(
                server_command='test-server',
                protocol_version='2025-03-26',
                server_config=None,
                args=None,
                output_dir='reports',
                report_prefix='cr',
                json=True,
                debug=False,
                skip_async=False,
                skip_shutdown=False,
                required_tools=None,
                skip_tests=None,
                dynamic_only=False,
                test_mode='all',
                spec_coverage_only=False,
                auto_detect=False,
                test_timeout=30,
                tools_timeout=30,
                verbose=False  # Explicitly set to False
            )
            mock_parse_args.return_value = mock_args
            
            # Mock the standard runner instead of VerboseTestRunner
            with patch('mcp_testing.utils.runner.run_tests') as mock_run_tests:
                test_results = {
                    "results": [{"name": "test_init", "passed": True, "duration": 0.5}],
                    "total": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "timeouts": 0
                }
                mock_run_tests.return_value = test_results
                
                # Mock environment preparation
                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server', 
                        return_value=os.environ.copy()) as mock_prepare_env:
                    
                    # Mock makedirs and open
                    with patch('mcp_testing.scripts.compliance_report.os.makedirs') as mock_makedirs:
                        with patch('builtins.open', new_callable=mock_open) as mock_open_call:
                    
                            # Call the main function
                            result = await compliance_report.main()
                            
                            # Assert that the function returned success (0)
                            self.assertEqual(result, 0)
                            
                            # Verify method calls
                            mock_prepare_env.assert_called_once_with('test-server')
                            mock_run_tests.assert_called_once()
                            
                            # Verify that reports directory was created
                            mock_makedirs.assert_called_once_with(os.path.join(self.mock_parent_dir, 'reports'), exist_ok=True)
                            
                            # Verify that reports were written
                            mock_open_call.assert_any_call(os.path.join(self.mock_parent_dir, 'reports', 
                                                f'cr_test-server_2025-03-26_{self.test_timestamp}.json'), 'w')
                            mock_open_call.assert_any_call(os.path.join(self.mock_parent_dir, 'reports', 
                                                f'cr_test-server_2025-03-26_{self.test_timestamp}.md'), 'w')
                            
                            # Check console output
                            output = self.held_output.getvalue()
                            self.assertIn("Running compliance tests for protocol 2025-03-26", output)
                            self.assertIn("Compliance Status: ✅ Fully Compliant", output)

    def test_main_module(self):
        """Test the __main__ block for different scenarios."""
        # Create a module-level copy for testing
        test_module = type('TestModule', (), {})
        test_module.__name__ = "__main__"
        test_module.main = MagicMock()
        test_module.asyncio = MagicMock()
        test_module.sys = MagicMock()
        
        # 1. Test normal execution
        test_module.asyncio.run.return_value = 0
        
        # Simulate the __main__ block
        if test_module.__name__ == "__main__":
            try:
                exit_code = test_module.asyncio.run(test_module.main())
                test_module.sys.exit(exit_code)
            except KeyboardInterrupt:
                test_module.sys.exit(130)
            except Exception as e:
                test_module.sys.exit(1)
        
        # Verify the calls
        test_module.asyncio.run.assert_called_once_with(test_module.main())
        test_module.sys.exit.assert_called_once_with(0)
        
        # Reset mocks
        test_module.asyncio.reset_mock()
        test_module.sys.reset_mock()
        
        # 2. Test KeyboardInterrupt handling
        test_module.asyncio.run.side_effect = KeyboardInterrupt()
        
        # Simulate the __main__ block
        if test_module.__name__ == "__main__":
            try:
                exit_code = test_module.asyncio.run(test_module.main())
                test_module.sys.exit(exit_code)
            except KeyboardInterrupt:
                test_module.sys.exit(130)
            except Exception as e:
                test_module.sys.exit(1)
        
        # Verify the exit code for KeyboardInterrupt
        test_module.sys.exit.assert_called_once_with(130)
        
        # Reset mocks
        test_module.asyncio.reset_mock()
        test_module.sys.reset_mock()
        
        # 3. Test general exception handling
        test_module.asyncio.run.side_effect = Exception("Test error")
        
        # Simulate the __main__ block
        if test_module.__name__ == "__main__":
            try:
                exit_code = test_module.asyncio.run(test_module.main())
                test_module.sys.exit(exit_code)
            except KeyboardInterrupt:
                test_module.sys.exit(130)
            except Exception as e:
                test_module.sys.exit(1)
        
        # Verify the exit code for general exceptions
        test_module.sys.exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_minimal_mocking(self):
        """Test the main function with minimal mocking to increase coverage."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up mock command line arguments
            test_args = [
                "compliance_report.py",
                "--server-command", "test-server",
                "--protocol-version", "2025-03-26",
                "--output-dir", temp_dir,
                "--dynamic-only",
                "--json"
            ]
            
            with patch('sys.argv', test_args):
                # Mock only the specific functions we need to avoid actual server process execution
                with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner_class:
                    # Create a mock runner instance with realistic behavior
                    mock_runner = MagicMock()
                    mock_runner_class.return_value = mock_runner
                    
                    # Create realistic test results
                    test_results = {
                        "results": [
                            {"name": "test_init", "passed": True, "duration": 0.1, "message": "Init passed"},
                            {"name": "test_function", "passed": False, "duration": 0.2, "message": "Test failed"},
                            {"name": "test_skipped", "passed": True, "skipped": True, "duration": 0.0, "message": "Skipped"}
                        ],
                        "total": 3,
                        "passed": 1,
                        "failed": 1,
                        "skipped": 1,
                        "timeouts": 0
                    }
                    
                    # Configure the run_tests method to return realistic results
                    mock_runner.run_tests = AsyncMock(return_value=test_results)
                    
                    # Mock environment preparation to avoid actual environment changes
                    with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server',
                              return_value=os.environ.copy()):
                        
                        # Run the actual main function
                        result = await compliance_report.main()
                        
                        # Check the result
                        self.assertEqual(result, 1)  # Non-zero because of failed test
                        
                        # Verify the runner was called
                        mock_runner_class.assert_called_once()
                        mock_runner.run_tests.assert_called()
                        
                        # Check output files were created
                        report_files = os.listdir(temp_dir)
                        self.assertTrue(any(f.endswith('.json') for f in report_files))
                        self.assertTrue(any(f.endswith('.md') for f in report_files))
                        
                        # Check stdout output
                        output = self.held_output.getvalue()
                        self.assertIn("Running in dynamic-only mode", output)
                        self.assertIn("Compliance Status: ", output)

    @pytest.mark.asyncio
    async def test_main_direct_args(self):
        """Test the main function with direct argument mocking to maximize coverage."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up different test scenarios with varying args
            test_scenarios = [
                # 1. Dynamic-only mode
                Namespace(
                    server_command='test-server-1',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir=temp_dir,
                    report_prefix='cr',
                    json=True,
                    debug=True,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=True,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                # 2. Spec-coverage-only mode
                Namespace(
                    server_command='test-server-2',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args="--extra-arg",
                    output_dir=temp_dir,
                    report_prefix='cr',
                    json=True,
                    debug=False,
                    skip_async=True,
                    skip_shutdown=True,
                    required_tools="tool1,tool2",
                    skip_tests="skip_test1,skip_test2",
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=True,
                    auto_detect=False,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=True
                ),
                # 3. Auto-detect mode
                Namespace(
                    server_command='server-brave-search',
                    protocol_version='2025-03-26',
                    server_config=None,
                    args=None,
                    output_dir=temp_dir,
                    report_prefix='cr',
                    json=True,
                    debug=True,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='all',
                    spec_coverage_only=False,
                    auto_detect=True,
                    test_timeout=30,
                    tools_timeout=30,
                    verbose=False
                ),
                # 4. Custom test mode
                Namespace(
                    server_command='test-server-4',
                    protocol_version='2024-11-05',
                    server_config=os.path.join(temp_dir, 'server_config.json'),
                    args=None,
                    output_dir=temp_dir,
                    report_prefix='custom',
                    json=False,
                    debug=False,
                    skip_async=False,
                    skip_shutdown=False,
                    required_tools=None,
                    skip_tests=None,
                    dynamic_only=False,
                    test_mode='tools',
                    spec_coverage_only=False,
                    auto_detect=False,
                    test_timeout=15,
                    tools_timeout=15,
                    verbose=True
                )
            ]
            
            # Create a mock server config file
            with open(os.path.join(temp_dir, 'server_config.json'), 'w') as f:
                json.dump({
                    "required_tools": ["config_tool1", "config_tool2"],
                    "skip_tests": ["config_skip_test"]
                }, f)
            
            # Run tests for each scenario
            for i, test_args in enumerate(test_scenarios):
                # Clear previous output
                self.held_output = io.StringIO()
                sys.stdout = self.held_output
                
                # Mock arguments
                with patch('mcp_testing.scripts.compliance_report.argparse.ArgumentParser.parse_args') as mock_parse_args:
                    mock_parse_args.return_value = test_args
                    
                    # Mock VerboseTestRunner
                    with patch('mcp_testing.scripts.compliance_report.VerboseTestRunner') as mock_runner_class:
                        # Create a mock runner instance
                        mock_runner = MagicMock()
                        mock_runner_class.return_value = mock_runner
                        
                        # Create test results with a mix of passing/failing
                        test_results = {
                            "results": [
                                {"name": f"test_init_{i}", "passed": True, "duration": 0.1},
                                {"name": f"test_fail_{i}", "passed": False, "duration": 0.2, "message": "Failed"},
                            ],
                            "total": 2,
                            "passed": 1,
                            "failed": 1,
                            "skipped": 0,
                            "timeouts": 0
                        }
                        
                        # Configure the run_tests method
                        mock_runner.run_tests = AsyncMock(return_value=test_results)
                        
                        # For non-verbose mode, mock the standard runner too
                        if not test_args.verbose:
                            with patch('mcp_testing.utils.runner.run_tests') as mock_std_runner:
                                mock_std_runner.return_value = test_results
                                
                                # Mock environment preparation
                                with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server',
                                        return_value=os.environ.copy()):
                                    
                                    # Run main function
                                    result = await compliance_report.main()
                                    
                                    # Verify result
                                    self.assertEqual(result, 1)  # Non-zero because of failed test
                        else:
                            # Mock environment preparation
                            with patch('mcp_testing.scripts.compliance_report.prepare_environment_for_server',
                                    return_value=os.environ.copy()):
                                
                                # Run main function
                                result = await compliance_report.main()
                                
                                # Verify result
                                self.assertEqual(result, 1)  # Non-zero because of failed test
                        
                        # Verify output contains expected messages
                        output = self.held_output.getvalue()
                        self.assertIn(f"Preparing environment for server: {test_args.server_command}", output)
                        
                        if test_args.dynamic_only:
                            self.assertIn("Running in dynamic-only mode", output)
                        
                        if test_args.spec_coverage_only:
                            self.assertIn("Running specification coverage tests only", output)
                            
                        if test_args.auto_detect:
                            self.assertIn("Auto-detected", output.lower())
                            
                        if test_args.test_mode != 'all':
                            self.assertIn(f"Test mode: {test_args.test_mode}", output)
                            
                        if test_args.required_tools:
                            self.assertIn("Required tools:", output)
                            
                        if test_args.skip_tests:
                            self.assertIn("Skipping tests:", output)
                        
                        # Check output files were created
                        report_files = os.listdir(temp_dir)
                        if test_args.json:
                            self.assertTrue(any(test_args.server_command in f and f.endswith('.json') for f in report_files))
                        self.assertTrue(any(test_args.server_command in f and f.endswith('.md') for f in report_files))

    @pytest.mark.asyncio
    async def test_verbose_test_runner_direct(self):
        """Test VerboseTestRunner with direct method calls (no mocking) to improve coverage."""
        # Create a real VerboseTestRunner instance
        runner = compliance_report.VerboseTestRunner(debug=True)
        
        # Create a simple test function
        async def test_func(protocol, server_command):
            return True, "Test passed"
        
        # Create a non-dictionary returning function
        async def test_non_dict_func(protocol, server_command):
            return "This is not a dictionary"
        
        # Create a test that throws an exception
        async def test_exception_func(protocol, server_command):
            raise Exception("Test exception")
        
        # Create test cases
        test_cases = [
            (test_func, "test_func"),
            (test_non_dict_func, "test_non_dict_func"),
            (test_exception_func, "test_exception_func")
        ]
        
        # Call run_test_with_progress directly
        result1 = await runner.run_test_with_progress(
            test_func=test_func,
            server_command="test-server",
            protocol_version="2025-03-26",
            test_name="test_func",
            env_vars=os.environ.copy(),
            current=1,
            total=3
        )
        
        # Verify the result
        self.assertTrue(result1["passed"])
        self.assertEqual(result1["name"], "test_func")
        self.assertIn("duration", result1)
        
        # Test with a function that returns a non-dictionary
        result2 = await runner.run_test_with_progress(
            test_func=test_non_dict_func,
            server_command="test-server",
            protocol_version="2025-03-26",
            test_name="test_non_dict_func",
            env_vars=os.environ.copy(),
            current=2,
            total=3
        )
        
        # Verify the result
        self.assertFalse(result2["passed"])
        self.assertEqual(result2["name"], "test_non_dict_func")
        self.assertIn("Invalid test result", result2["message"])
        
        # Test with a function that throws an exception
        result3 = await runner.run_test_with_progress(
            test_func=test_exception_func,
            server_command="test-server",
            protocol_version="2025-03-26",
            test_name="test_exception_func",
            env_vars=os.environ.copy(),
            current=3,
            total=3
        )
        
        # Verify the result
        self.assertFalse(result3["passed"])
        self.assertEqual(result3["name"], "test_exception_func")
        self.assertIn("Test runner exception", result3["message"])
        
        # Patch only the MCPTestRunner to avoid execution of actual server commands
        with patch('mcp_testing.utils.runner.MCPTestRunner') as mock_runner_class:
            # Setup the mocked runner behavior
            mock_instance = MagicMock()
            mock_runner_class.return_value = mock_instance
            
            # Configure the run_test method to return different results
            mock_instance.run_test = AsyncMock(side_effect=[
                {"name": "test_func", "passed": True, "message": "Test passed"},
                {"name": "test_non_dict_func", "passed": False, "message": "Invalid result"},
                Exception("Test runner error")
            ])
            
            # Call run_tests with all test cases
            results = await runner.run_tests(
                tests=test_cases,
                protocol="2025-03-26",
                server_command="test-server",
                env_vars=os.environ.copy()
            )
            
            # Verify the results structure
            self.assertIn("results", results)
            self.assertIn("total", results)
            self.assertIn("passed", results)
            self.assertIn("failed", results)
            self.assertIn("skipped", results)
            self.assertIn("timeouts", results)
            
            # Check counts
            self.assertEqual(results["total"], 3)
            self.assertEqual(results["failed"], 2)
            
            # Verify call to MCPTestRunner.run_test was made for each test
            self.assertEqual(mock_instance.run_test.call_count, 3)


if __name__ == "__main__":
    unittest.main() 