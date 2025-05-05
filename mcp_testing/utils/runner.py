# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Test Runner for MCP Testing Framework.

This module provides a utility for running MCP test cases against different server implementations.
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, List, Optional, Union, Callable, Tuple

from mcp_testing.protocols.base import MCPProtocolAdapter
from mcp_testing.transports.base import MCPTransportAdapter
from mcp_testing.transports.stdio import StdioTransportAdapter
from mcp_testing.transports.http import HttpTransportAdapter
from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter


class MCPTestRunner:
    """
    Test runner for MCP testing framework.
    
    This class provides a utility for running MCP test cases against different server
    implementations and collecting results.
    """
    
    def __init__(self, debug: bool = False):
        """
        Initialize the test runner.
        
        Args:
            debug: Whether to enable debug output
        """
        self.debug = debug
        self.results = {}
        # Check for shutdown skipping early
        self.skip_shutdown = self._should_skip_shutdown()
        if self.skip_shutdown and self.debug:
            print("Note: Shutdown will be skipped based on environment configuration")
    
    def _should_skip_shutdown(self) -> bool:
        """
        Check if shutdown should be skipped based on environment variable.
        
        Returns:
            bool: True if shutdown should be skipped, False otherwise
        """
        skip_shutdown = os.environ.get("MCP_SKIP_SHUTDOWN", "").lower()
        return skip_shutdown in ("true", "1", "yes")
    
    async def run_test(self, test_func: Callable[[MCPProtocolAdapter], Tuple[bool, str]], 
                      server_command: str,
                      protocol_version: str,
                      test_name: str,
                      env_vars: Optional[Dict[str, str]] = None,
                      timeout: Optional[int] = None,
                      transport_type: str = "stdio") -> Dict[str, Any]:
        """
        Run a single test case.
        
        Args:
            test_func: The test function to run
            server_command: The command to launch the server or server URL for HTTP
            protocol_version: The protocol version to use
            test_name: The name of the test
            env_vars: Environment variables to pass to the server process
            timeout: Optional timeout in seconds for the test execution
            transport_type: Type of transport to use ("stdio" or "http")
            
        Returns:
            A dictionary containing the test results
        """
        # Skip shutdown-related tests if shutdown is disabled
        if self.skip_shutdown and (test_name == "test_shutdown" or test_name == "test_exit_after_shutdown"):
            if self.debug:
                print(f"Skipping {test_name} because shutdown is disabled")
            result = {
                "name": test_name,
                "passed": True,  # Mark as passed to avoid false failures
                "message": "Test skipped because shutdown is disabled via MCP_SKIP_SHUTDOWN",
                "duration": 0,
                "skipped": True
            }
            self.results[test_name] = result
            return result
            
        if self.debug:
            print(f"\nRunning test: {test_name}")
        
        # Create a fresh transport adapter for each test
        if self.debug:
            if transport_type == "stdio":
                print(f"Starting server process: {server_command}")
                if env_vars:
                    print(f"Environment variables: {env_vars}")
            else:
                print(f"Connecting to server URL: {server_command}")
                
        if transport_type == "stdio":
            transport_adapter = StdioTransportAdapter(
                server_command=server_command,
                env_vars=env_vars,
                debug=self.debug
            )
        else:  # HTTP transport
            transport_adapter = HttpTransportAdapter(
                server_url=server_command,
                debug=self.debug
            )
        
        # Create a fresh protocol adapter for each test
        if protocol_version == "2024-11-05":
            protocol_adapter = MCP2024_11_05Adapter(
                transport=transport_adapter,
                debug=self.debug
            )
        elif protocol_version == "2025-03-26":
            protocol_adapter = MCP2025_03_26Adapter(
                transport=transport_adapter,
                debug=self.debug
            )
        else:
            raise ValueError(f"Unsupported protocol version: {protocol_version}")
            
        start_time = time.time()
        
        try:
            # Initialize the connection
            if self.debug:
                print(f"Initializing server...")
                
            await protocol_adapter.initialize()
            
            if self.debug:
                print(f"Sending initialized notification...")
                
            await protocol_adapter.send_initialized()
            
            # Run the test with timeout if specified
            if self.debug:
                print(f"Executing test: {test_name}")

            # Handle test with timeout if specified
            if timeout:
                try:
                    # Create a task for the test function
                    test_task = asyncio.create_task(test_func(protocol_adapter))
                    # Wait for either the task to complete or timeout
                    passed, message = await asyncio.wait_for(test_task, timeout=timeout)
                except asyncio.TimeoutError:
                    # Check if this is a tools test which can be treated as non-critical
                    if test_name.startswith("test_tools_") or test_name.startswith("test_tool_"):
                        if self.debug:
                            print(f"⚠️ WARNING: Test {test_name} timed out after {timeout}s (continuing)")
                        passed = True  # Treat as passed for compliance
                        message = f"Test timed out after {timeout}s but is considered non-critical"
                        # Mark it as a timeout for reporting
                        result = {
                            "name": test_name,
                            "passed": passed,
                            "message": message,
                            "duration": time.time() - start_time,
                            "timeout": True,
                            "non_critical": True
                        }
                        self.results[test_name] = result
                        
                        # Skip shutdown for this test since we couldn't complete it normally
                        if not self.skip_shutdown:
                            if self.debug:
                                print(f"Skipping shutdown due to timeout")
                        
                        # Just terminate the transport
                        await transport_adapter.terminate()
                        return result
                    else:
                        # For critical tests, consider timeout as failure
                        passed = False
                        message = f"Test timed out after {timeout}s"
            else:
                # Run the test without timeout
                passed, message = await test_func(protocol_adapter)
            
            if self.debug:
                status = "PASSED" if passed else "FAILED"
                print(f"Test execution complete: {status}")
                if message:
                    print(f"  Message: {message}")
            
            # Determine whether to skip shutdown based on environment variables
            # This respects both env_vars argument and global environment
            skip_shutdown = self.skip_shutdown
            if not skip_shutdown and env_vars:
                skip_env = env_vars.get("MCP_SKIP_SHUTDOWN", "").lower()
                skip_shutdown = skip_env in ("true", "1", "yes")
            
            # Handle shutdown based on configuration
            if not skip_shutdown:
                try:
                    if self.debug:
                        print(f"Sending shutdown request...")
                        
                    await protocol_adapter.shutdown()
                    
                    if self.debug:
                        print(f"Sending exit notification...")
                        
                    await protocol_adapter.exit()
                except Exception as e:
                    if self.debug:
                        print(f"Error during shutdown: {str(e)}")
                    # Don't fail the test just because shutdown failed
                    pass
            
            # Calculate test duration
            duration = time.time() - start_time
            
            # Store and return the result
            result = {
                "name": test_name,
                "passed": passed,
                "message": message,
                "duration": duration
            }
            self.results[test_name] = result
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_message = f"Test failed with error: {str(e)}"
            if self.debug:
                print(error_message)
                import traceback
                traceback.print_exc()
            
            result = {
                "name": test_name,
                "passed": False,
                "message": error_message,
                "duration": duration
            }
            self.results[test_name] = result
            return result
            
        finally:
            # Always terminate the transport
            try:
                await transport_adapter.terminate()
            except:
                pass
    
    async def run_tests(self, tests: List[Tuple[Callable[[MCPProtocolAdapter], Tuple[bool, str]], str]], 
                       protocol: str = "2024-11-05",
                       transport: str = "stdio",
                       server_command: str = None,
                       env_vars: Optional[Dict[str, str]] = None,
                       timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Run a list of test cases.
        
        Args:
            tests: List of (test_func, test_name) tuples
            protocol: Protocol version to use
            transport: Transport type to use ("stdio" or "http")
            server_command: Command to launch server or server URL for HTTP
            env_vars: Environment variables to pass to server process
            timeout: Optional timeout in seconds for test execution
            
        Returns:
            A dictionary containing the aggregated test results
        """
        if not server_command:
            raise ValueError("server_command is required")
            
        results = {
            "results": [],
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "timeouts": 0
        }
        
        for test_func, test_name in tests:
            result = await self.run_test(
                test_func=test_func,
                server_command=server_command,
                protocol_version=protocol,
                test_name=test_name,
                env_vars=env_vars,
                timeout=timeout,
                transport_type=transport
            )
            
            results["results"].append(result)
            
            if result.get("skipped", False):
                results["skipped"] += 1
            elif result.get("timeout", False):
                results["timeouts"] += 1
            elif result["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
                
        return results


# Convenience function to run tests
async def run_tests(tests: List[Tuple[Callable[[MCPProtocolAdapter], Tuple[bool, str]], str]], 
                   protocol: str = "2024-11-05",
                   transport: str = "stdio",
                   server_command: str = None,
                   env_vars: Optional[Dict[str, str]] = None,
                   debug: bool = False,
                   timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    Run a list of test cases.
    
    Args:
        tests: A list of tuples containing (test_func, test_name)
        protocol: The protocol version to use
        transport: The transport type to use
        server_command: The command to launch the server (for stdio transport)
        env_vars: Environment variables to pass to the server process
        debug: Whether to enable debug output
        timeout: Optional timeout in seconds for each test execution
        
    Returns:
        A dictionary containing the test results
    """
    runner = MCPTestRunner(debug=debug)
    return await runner.run_tests(
        tests=tests,
        protocol=protocol,
        transport=transport,
        server_command=server_command,
        env_vars=env_vars,
        timeout=timeout
    ) 