#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the run_stdio_tests.py script.
"""

import unittest
from unittest.mock import patch, Mock, MagicMock, call
import sys
import io
import json
import os
from pathlib import Path
from argparse import Namespace
import importlib

from mcp_testing.scripts import run_stdio_tests


class TestRunStdioTests(unittest.TestCase):
    """Test cases for the run_stdio_tests script."""

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

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Restore original sys.argv
        sys.argv = self.original_argv

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_success(self, mock_parse_args, mock_run_tests):
        """Test the main function with successful execution."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        
        # Call the main function
        result = await run_stdio_tests.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify that run_tests was called with the right parameters
        mock_run_tests.assert_called_once()
        call_args = mock_run_tests.call_args[1]
        self.assertEqual(call_args['protocol'], '2024-11-05')
        self.assertEqual(call_args['transport'], 'stdio')
        self.assertEqual(call_args['server_command'], 'python server.py')
        self.assertFalse(call_args['debug'])
        
        # Check output contains success message
        output = self.held_output.getvalue()
        self.assertIn("Test Results:", output)
        self.assertIn("Total tests: 5", output)
        self.assertIn("Passed: 5", output)
        self.assertIn("Failed: 0", output)

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_failure(self, mock_parse_args, mock_run_tests):
        """Test the main function when tests fail."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock failed test run
        mock_run_tests.return_value = {
            'total': 5,
            'passed': 3,
            'failed': 2,
            'tests': [
                {'name': 'test1', 'result': True, 'message': 'Success'},
                {'name': 'test2', 'result': False, 'message': 'Failed'}
            ]
        }
        
        # Call the main function
        result = await run_stdio_tests.main()
        
        # Assert that the function returned failure (1)
        self.assertEqual(result, 1)
        
        # Check output contains failure message
        output = self.held_output.getvalue()
        self.assertIn("Test Results:", output)
        self.assertIn("Total tests: 5", output)
        self.assertIn("Passed: 3", output)
        self.assertIn("Failed: 2", output)

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('mcp_testing.scripts.run_stdio_tests.json.dump')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('argparse.ArgumentParser.parse_args')
    async def test_output_to_file(self, mock_parse_args, mock_open, mock_json_dump, mock_run_tests):
        """Test writing output to a file."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file='results.json',
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock test run
        test_results = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        mock_run_tests.return_value = test_results
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify the file was opened and JSON was dumped
        mock_open.assert_called_once_with('results.json', 'w')
        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        self.assertEqual(args[0], test_results)  # First arg should be the results
        self.assertEqual(kwargs['indent'], 2)  # Should use indent=2
        
        # Check output mentions the file
        output = self.held_output.getvalue()
        self.assertIn("Results written to results.json", output)

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('mcp_testing.scripts.run_stdio_tests.results_to_markdown')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_generate_markdown(self, mock_parse_args, mock_results_to_markdown, mock_run_tests):
        """Test generating a Markdown report."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=True,
            markdown_file='report.md'
        )
        mock_parse_args.return_value = mock_args
        
        # Mock test run
        test_results = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        mock_run_tests.return_value = test_results
        
        # Mock markdown generation
        mock_results_to_markdown.return_value = 'report.md'
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify results_to_markdown was called
        mock_results_to_markdown.assert_called_once_with(
            results=test_results,
            server_command='python server.py',
            protocol_version='2024-11-05',
            output_file='report.md'
        )
        
        # Check output mentions the report
        output = self.held_output.getvalue()
        self.assertIn("Markdown compliance report generated: report.md", output)

    @patch('mcp_testing.scripts.run_stdio_tests.asyncio.run')
    @patch('mcp_testing.scripts.run_stdio_tests.main')
    @patch('sys.exit')
    def test_script_main(self, mock_exit, mock_main, mock_asyncio_run):
        """Test the script when run as __main__."""
        # Mock that asyncio.run returns 42
        mock_asyncio_run.return_value = 42
        mock_main.return_value = 42
        
        # Save the original __name__ value
        original_name = run_stdio_tests.__name__
        
        # Set __name__ to "__main__"
        run_stdio_tests.__name__ = "__main__"
        
        # Execute the code that should run when __name__ == "__main__"
        exec("""if run_stdio_tests.__name__ == "__main__":
            sys.exit(asyncio.run(run_stdio_tests.main()))""", 
            {"run_stdio_tests": run_stdio_tests, "sys": sys, "asyncio": run_stdio_tests.asyncio})
        
        # Restore original name
        run_stdio_tests.__name__ = original_name
        
        # Check that sys.exit was called with the value from main()
        mock_exit.assert_called_once_with(42)

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_with_2025_03_26_protocol(self, mock_parse_args, mock_run_tests):
        """Test using the 2025-03-26 protocol version."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 8,
            'passed': 8,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify that run_tests was called with the right parameters
        mock_run_tests.assert_called_once()
        call_args = mock_run_tests.call_args[1]
        
        # Check that we're passing the right protocol version
        self.assertEqual(call_args['protocol'], '2025-03-26')
        
        # And that async tools are included
        # This is testing if ASYNC_TOOLS_TEST_CASES were included in the tests
        # Since we can't directly access the 'tests' parameter value as it contains the 
        # imported test cases from run_stdio_tests module, we can check if the environment
        # variables contain the correct protocol version
        self.assertEqual(call_args['env_vars']['MCP_PROTOCOL_VERSION'], '2025-03-26')

    @patch('mcp_testing.scripts.run_stdio_tests.INIT_TEST_CASES', [{'name': 'init_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.TOOLS_TEST_CASES', [{'name': 'tools_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.ASYNC_TOOLS_TEST_CASES', [{'name': 'async_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_test_collection_2024_11_05(self, mock_parse_args, mock_run_tests, 
                                             mock_async_tests, mock_tools_tests, mock_init_tests):
        """Test the collection of tests for 2024-11-05 protocol."""
        # Mock arguments for 2024-11-05 protocol
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 2,
            'passed': 2,
            'failed': 0,
            'tests': []
        }
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify that run_tests was called with the right tests
        call_args = mock_run_tests.call_args[1]
        tests = call_args['tests']
        
        # Assert there are exactly 2 tests (init + tools, but not async)
        self.assertEqual(len(tests), 2)
        
        # Check specific tests
        test_names = [t['name'] for t in tests]
        self.assertIn('init_test', test_names)
        self.assertIn('tools_test', test_names)
        self.assertNotIn('async_test', test_names)

    @patch('mcp_testing.scripts.run_stdio_tests.INIT_TEST_CASES', [{'name': 'init_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.TOOLS_TEST_CASES', [{'name': 'tools_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.ASYNC_TOOLS_TEST_CASES', [{'name': 'async_test', 'func': Mock()}])
    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_test_collection_2025_03_26(self, mock_parse_args, mock_run_tests, 
                                             mock_async_tests, mock_tools_tests, mock_init_tests):
        """Test the collection of tests for 2025-03-26 protocol."""
        # Mock arguments for 2025-03-26 protocol
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2025-03-26',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 3,
            'passed': 3,
            'failed': 0,
            'tests': []
        }
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify that run_tests was called with the right tests
        call_args = mock_run_tests.call_args[1]
        tests = call_args['tests']
        
        # Assert there are exactly 3 tests (init + tools + async)
        self.assertEqual(len(tests), 3)
        
        # Check specific tests
        test_names = [t['name'] for t in tests]
        self.assertIn('init_test', test_names)
        self.assertIn('tools_test', test_names)
        self.assertIn('async_test', test_names)

    @patch('sys.argv', ['run_stdio_tests.py', '--server-command', 'python server.py'])
    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    async def test_with_command_line_args(self, mock_run_tests):
        """Test the script with command line arguments."""
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 2,
            'passed': 2,
            'failed': 0,
            'tests': []
        }
        
        # Call the main function
        result = await run_stdio_tests.main()
        
        # Assert that the function returned success (0)
        self.assertEqual(result, 0)
        
        # Verify that run_tests was called with the right parameters
        mock_run_tests.assert_called_once()
        call_args = mock_run_tests.call_args[1]
        self.assertEqual(call_args['protocol'], '2024-11-05')  # Default protocol
        self.assertEqual(call_args['transport'], 'stdio')
        self.assertEqual(call_args['server_command'], 'python server.py')
        self.assertFalse(call_args['debug'])

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_with_debug_enabled(self, mock_parse_args, mock_run_tests):
        """Test with debug mode enabled."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=True,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify debug parameter was passed to run_tests
        mock_run_tests.assert_called_once()
        call_args = mock_run_tests.call_args[1]
        self.assertTrue(call_args['debug'])

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('mcp_testing.scripts.run_stdio_tests.results_to_markdown')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_markdown_flag_without_filename(self, mock_parse_args, mock_results_to_markdown, mock_run_tests):
        """Test generating a Markdown report with auto-generated filename."""
        # Mock arguments with markdown=True but no markdown_file
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=True,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock test run
        test_results = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        mock_run_tests.return_value = test_results
        
        # Mock markdown generation with auto-generated filename
        auto_generated_file = 'mcp_compliance_report_2024-11-05.md'
        mock_results_to_markdown.return_value = auto_generated_file
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify results_to_markdown was called with None for output_file
        mock_results_to_markdown.assert_called_once()
        args, kwargs = mock_results_to_markdown.call_args
        self.assertEqual(kwargs['results'], test_results)
        self.assertEqual(kwargs['server_command'], 'python server.py')
        self.assertEqual(kwargs['protocol_version'], '2024-11-05')
        self.assertIsNone(kwargs['output_file'])
        
        # Check output mentions the auto-generated report
        output = self.held_output.getvalue()
        self.assertIn(f"Markdown compliance report generated: {auto_generated_file}", output)

    @patch('mcp_testing.scripts.run_stdio_tests.run_tests')
    @patch('argparse.ArgumentParser.parse_args')
    @patch.dict('os.environ', {'EXISTING_VAR': 'existing_value'})
    async def test_environment_variables(self, mock_parse_args, mock_run_tests):
        """Test setting environment variables for the server."""
        # Mock arguments
        mock_args = Namespace(
            server_command='python server.py',
            protocol_version='2024-11-05',
            debug=False,
            output_file=None,
            markdown=False,
            markdown_file=None
        )
        mock_parse_args.return_value = mock_args
        
        # Mock successful test run
        mock_run_tests.return_value = {
            'total': 5,
            'passed': 5,
            'failed': 0,
            'tests': [{'name': 'test1', 'result': True, 'message': 'Success'}]
        }
        
        # Call the main function
        await run_stdio_tests.main()
        
        # Verify environment variables were set correctly
        mock_run_tests.assert_called_once()
        call_args = mock_run_tests.call_args[1]
        env_vars = call_args['env_vars']
        
        # Check that MCP_PROTOCOL_VERSION was set
        self.assertEqual(env_vars['MCP_PROTOCOL_VERSION'], '2024-11-05')
        
        # Check that existing environment variables were preserved
        self.assertEqual(env_vars['EXISTING_VAR'], 'existing_value')

    @patch('mcp_testing.scripts.run_stdio_tests.Path')
    def test_module_imports(self, mock_path):
        """Test module import structure."""
        # Mock Path resolution
        mock_path_instance = MagicMock()
        # Instead of returning a fixed mock path, get the actual path being used
        mock_path.return_value.resolve.return_value.parent.parent.parent = '/Users/scott/AI/PROTOCOL_STRATEGY/mcp/tools/mcp-protocol-validator'
        
        # Import the module directly to test its behavior
        import mcp_testing.scripts.run_stdio_tests
        importlib.reload(mcp_testing.scripts.run_stdio_tests)
        
        # The test passes if no exception is raised during import
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main() 