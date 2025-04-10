"""
Unit tests for the runner module.
"""

import asyncio
import os
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock, call

from mcp_testing.utils.runner import MCPTestRunner
from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter


class TestMCPTestRunner:
    """Tests for the MCPTestRunner class."""

    def test_init(self):
        """Test initialization of MCPTestRunner."""
        # Default initialization
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=False) as mock_skip:
            runner = MCPTestRunner()
            assert runner.debug is False
            assert runner.skip_shutdown is False
            assert isinstance(runner.results, dict)
            mock_skip.assert_called_once()

        # With debug=True
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=False) as mock_skip:
            runner = MCPTestRunner(debug=True)
            assert runner.debug is True
            assert runner.skip_shutdown is False
            mock_skip.assert_called_once()

        # With shutdown skipping
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=True), \
             patch('builtins.print') as mock_print:
            runner = MCPTestRunner(debug=True)
            assert runner.skip_shutdown is True
            assert mock_print.call_count >= 1
            assert "shutdown will be skipped" in mock_print.call_args[0][0].lower()

    def test_should_skip_shutdown(self):
        """Test _should_skip_shutdown method."""
        runner = MCPTestRunner()

        # Test with MCP_SKIP_SHUTDOWN not set
        with patch.dict(os.environ, {}, clear=True):
            assert runner._should_skip_shutdown() is False

        # Test with MCP_SKIP_SHUTDOWN="true"
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "true"}):
            assert runner._should_skip_shutdown() is True

        # Test with MCP_SKIP_SHUTDOWN="1"
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "1"}):
            assert runner._should_skip_shutdown() is True

        # Test with MCP_SKIP_SHUTDOWN="yes"
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "yes"}):
            assert runner._should_skip_shutdown() is True

        # Test with MCP_SKIP_SHUTDOWN="false"
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "false"}):
            assert runner._should_skip_shutdown() is False

        # Test with MCP_SKIP_SHUTDOWN set to empty string
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": ""}):
            assert runner._should_skip_shutdown() is False

    @pytest.mark.asyncio
    async def test_run_test_skip_shutdown_tests(self):
        """Test run_test skipping shutdown tests when shutdown is disabled."""
        # Create runner with shutdown skipping enabled
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=True):
            runner = MCPTestRunner(debug=True)

        # Mock the print function to monitor output
        with patch('builtins.print'):
            # Test with test_shutdown
            result = await runner.run_test(
                test_func=AsyncMock(),
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_shutdown"
            )

            # Verify the test was skipped
            assert result["passed"] is True
            assert result["skipped"] is True
            assert "shutdown is disabled" in result["message"]
            assert result["duration"] == 0

            # Test with test_exit_after_shutdown
            result = await runner.run_test(
                test_func=AsyncMock(),
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_exit_after_shutdown"
            )

            # Verify the test was skipped
            assert result["passed"] is True
            assert result["skipped"] is True
            assert "shutdown is disabled" in result["message"]
            assert result["duration"] == 0

    @pytest.mark.asyncio
    async def test_run_test_normal_execution(self):
        """Test run_test with normal execution path."""
        # Create a runner
        runner = MCPTestRunner(debug=True)

        # Create a mock test function that always passes
        mock_test_func = AsyncMock(return_value=(True, "Test passed"))

        # Mock the dependencies
        mock_protocol = AsyncMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter') as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2024_11_05Adapter', return_value=mock_protocol) as mock_protocol_class, \
             patch('builtins.print'):
            
            # Run the test
            result = await runner.run_test(
                test_func=mock_test_func,
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_normal"
            )

            # Verify protocol was initialized and used correctly
            mock_transport_class.assert_called_once()
            mock_protocol_class.assert_called_once()
            mock_protocol.initialize.assert_called_once()
            mock_protocol.send_initialized.assert_called_once()
            mock_test_func.assert_called_once_with(mock_protocol)
            mock_protocol.shutdown.assert_called_once()

            # Verify test result
            assert result["name"] == "test_normal"
            assert result["passed"] is True
            assert result["message"] == "Test passed"
            assert "duration" in result

    @pytest.mark.asyncio
    async def test_run_test_with_protocol_version_2025_03_26(self):
        """Test run_test with protocol version 2025-03-26."""
        # Create a runner
        runner = MCPTestRunner(debug=False)

        # Create a mock test function
        mock_test_func = AsyncMock(return_value=(True, "Test passed"))

        # Mock the dependencies
        mock_protocol = AsyncMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter') as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2025_03_26Adapter', return_value=mock_protocol) as mock_protocol_class:
            
            # Run the test
            result = await runner.run_test(
                test_func=mock_test_func,
                server_command="test_command",
                protocol_version="2025-03-26",
                test_name="test_protocol_2025"
            )

            # Verify protocol class was used
            mock_protocol_class.assert_called_once()
            
            # Verify test result
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_run_test_with_invalid_protocol_version(self):
        """Test run_test with an invalid protocol version."""
        # Create a runner
        runner = MCPTestRunner()

        # Create a mock test function
        mock_test_func = AsyncMock()

        # Mock transport adapter
        with patch('mcp_testing.utils.runner.StdioTransportAdapter'):
            # Run the test with an invalid protocol version
            with pytest.raises(ValueError, match="Unsupported protocol version"):
                await runner.run_test(
                    test_func=mock_test_func,
                    server_command="test_command",
                    protocol_version="invalid-version",
                    test_name="test_invalid_protocol"
                )

    @pytest.mark.asyncio
    async def test_run_test_with_failure(self):
        """Test run_test with a test that fails."""
        # Create a runner
        runner = MCPTestRunner(debug=False)

        # Create a mock test function that fails
        mock_test_func = AsyncMock(return_value=(False, "Test failed"))

        # Mock the dependencies
        mock_protocol = AsyncMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter') as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2024_11_05Adapter', return_value=mock_protocol) as mock_protocol_class:
            
            # Run the test
            result = await runner.run_test(
                test_func=mock_test_func,
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_failure"
            )

            # Verify protocol was still shut down
            mock_protocol.shutdown.assert_called_once()
            
            # Verify test result
            assert result["name"] == "test_failure"
            assert result["passed"] is False
            assert result["message"] == "Test failed"
            assert "duration" in result

    @pytest.mark.asyncio
    async def test_run_test_with_timeout(self):
        """Test run_test with a test that times out."""
        # Create a runner
        runner = MCPTestRunner(debug=True)
    
        # Create a mock test function that takes too long
        async def slow_test(_):
            await asyncio.sleep(10)  # This should trigger the timeout
            return True, "This shouldn't be reached"
        
        # Mock the dependencies
        mock_protocol = AsyncMock()
        mock_transport = MagicMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter', return_value=mock_transport) as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2024_11_05Adapter', return_value=mock_protocol) as mock_protocol_class, \
             patch('builtins.print'), \
             patch('asyncio.create_task'), \
             patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            
            # Run the test with a timeout - critical test
            result = await runner.run_test(
                test_func=slow_test,
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_critical_timeout",
                timeout=1
            )
            
            # Verify test result for a critical test
            assert result["name"] == "test_critical_timeout"
            assert result["passed"] is False
            assert "timed out" in result["message"].lower() or "timeout" in result["message"].lower()
            assert "duration" in result
            
            # Reset mocks and patch with a different side effect for the second test case
            mock_protocol.reset_mock()
            mock_transport.reset_mock()
            
            # For the second test, we'll use a different approach
            # Instead of patching asyncio.wait_for with TimeoutError,
            # we'll let the run_test method handle a normal exception from the test function
            with patch('asyncio.wait_for', side_effect=Exception("Test timed out")):
                # Run test with tools prefix
                result = await runner.run_test(
                    test_func=slow_test,
                    server_command="test_command",
                    protocol_version="2024-11-05",
                    test_name="test_tools_timeout",
                    timeout=1
                )
                
                # Verify the result format
                assert result["name"] == "test_tools_timeout"
                assert result["passed"] is False
                # Instead of looking for specific timeout message, just check if it contains
                # the error information from our mocked exception
                assert "test timed out" in result["message"].lower() or "exception" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_run_test_with_shutdown_error(self):
        """Test run_test when the shutdown command fails."""
        # Create a runner with shutdown NOT skipped
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=False):
            runner = MCPTestRunner(debug=True)

        # Create a mock test function
        mock_test_func = AsyncMock(return_value=(True, "Test passed"))

        # Mock protocol with a failing shutdown
        mock_protocol = AsyncMock()
        mock_protocol.shutdown.side_effect = Exception("Shutdown failed")
        mock_transport = MagicMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter', return_value=mock_transport) as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2024_11_05Adapter', return_value=mock_protocol) as mock_protocol_class, \
             patch('builtins.print'):
            
            # When shutdown fails, the run_test method catches the error and returns a failed test result
            result = await runner.run_test(
                test_func=mock_test_func,
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_shutdown_error"
            )

            # Verify protocol shutdown was attempted
            mock_protocol.shutdown.assert_called_once()
            
            # Verify the test failed with the exception
            assert result["passed"] is False
            assert "exception" in result
            assert "Shutdown failed" in result["exception"]

    @pytest.mark.asyncio
    async def test_run_test_with_skip_shutdown_env_var(self):
        """Test run_test with skip shutdown in environment variables."""
        # Create a runner with shutdown not skipped globally
        with patch.object(MCPTestRunner, '_should_skip_shutdown', return_value=False):
            runner = MCPTestRunner(debug=True)

        # Create a mock test function
        mock_test_func = AsyncMock(return_value=(True, "Test passed"))

        # Mock the dependencies
        mock_protocol = AsyncMock()
        
        with patch('mcp_testing.utils.runner.StdioTransportAdapter') as mock_transport_class, \
             patch('mcp_testing.utils.runner.MCP2024_11_05Adapter', return_value=mock_protocol) as mock_protocol_class, \
             patch('builtins.print'):
            
            # Run the test with environment variable to skip shutdown
            result = await runner.run_test(
                test_func=mock_test_func,
                server_command="test_command",
                protocol_version="2024-11-05",
                test_name="test_with_env",
                env_vars={"MCP_SKIP_SHUTDOWN": "true"}
            )

            # Verify shutdown was skipped
            mock_protocol.shutdown.assert_not_called()
            
            # Verify test result
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_run_tests_multiple(self):
        """Test running multiple tests sequentially."""
        runner = MCPTestRunner()
        
        # Mock the run_test method to return predictable results
        original_run_test = runner.run_test
        
        test_specs = [
            (AsyncMock(), "test1"),
            (AsyncMock(), "test2"),
            (AsyncMock(), "test3")
        ]
        
        test_results = [
            {"name": "test1", "passed": True, "message": "Test 1 passed", "duration": 0.1},
            {"name": "test2", "passed": False, "message": "Test 2 failed", "duration": 0.2},
            {"name": "test3", "passed": True, "message": "Test 3 passed", "duration": 0.3}
        ]
        
        # Map test names to results
        result_map = {r["name"]: r for r in test_results}
        
        async def mock_run_test(test_func, server_command, protocol_version, test_name, **kwargs):
            # Return the corresponding result from our predefined results
            if test_name in result_map:
                runner.results[test_name] = result_map[test_name]
                return result_map[test_name]
            
            # If test not found, call the original method
            return await original_run_test(test_func, server_command, protocol_version, test_name, **kwargs)
        
        # Replace run_test with our mock version
        with patch.object(runner, 'run_test', side_effect=mock_run_test):
            # Run the tests
            all_results = await runner.run_tests(
                tests=test_specs,
                protocol="2024-11-05",
                transport="stdio",
                server_command="test_command"
            )
            
            # Verify results
            assert all_results["total"] == 3
            assert all_results["passed"] == 2
            assert all_results["failed"] == 1
            assert len(all_results["results"]) == 3 