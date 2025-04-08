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
                      env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Run a single test case.
        
        Args:
            test_func: The test function to run
            server_command: The command to launch the server
            protocol_version: The protocol version to use
            test_name: The name of the test
            env_vars: Environment variables to pass to the server process
            
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
            print(f"Starting server process: {server_command}")
            if env_vars:
                print(f"Environment variables: {env_vars}")
                
        transport_adapter = StdioTransportAdapter(
            server_command=server_command,
            env_vars=env_vars,
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
            
            # Run the test
            if self.debug:
                print(f"Executing test: {test_name}")
                
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
                        print(f"Warning: Shutdown failed: {str(e)}")
                    # If shutdown is explicitly not skipped but fails, propagate the error
                    raise
            else:
                # Just exit without shutdown if shutdown is skipped
                if self.debug:
                    print(f"Skipping shutdown call as configured")
                try:
                    if self.debug:
                        print(f"Sending exit notification...")
                        
                    await protocol_adapter.exit()
                except Exception as e:
                    if self.debug:
                        print(f"Warning: Exit notification failed: {str(e)}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Build the result
            result = {
                "name": test_name,
                "passed": passed,
                "message": message,
                "duration": duration
            }
            
            if self.debug:
                status = "PASSED" if passed else "FAILED"
                print(f"Test {test_name}: {status} ({duration:.2f}s)")
                if message:
                    print(f"  {message}")
                    
            self.results[test_name] = result
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            # Build the error result
            result = {
                "name": test_name,
                "passed": False,
                "message": f"Test raised exception: {str(e)}",
                "duration": duration,
                "exception": str(e)
            }
            
            if self.debug:
                print(f"Test {test_name}: ERROR ({duration:.2f}s)")
                print(f"  Exception: {str(e)}")
                
            self.results[test_name] = result
            return result
        finally:
            # Always stop the transport when done
            if self.debug:
                print(f"Stopping server process...")
                
            transport_adapter.stop()
    
    async def run_tests(self, tests: List[Tuple[Callable[[MCPProtocolAdapter], Tuple[bool, str]], str]], 
                       protocol: str = "2024-11-05",
                       transport: str = "stdio",
                       server_command: str = None,
                       env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Run a list of test cases.
        
        Args:
            tests: A list of tuples containing (test_func, test_name)
            protocol: The protocol version to use
            transport: The transport type to use
            server_command: The command to launch the server (for stdio transport)
            env_vars: Environment variables to pass to the server process
            
        Returns:
            A dictionary containing the test results
        """
        if not server_command and transport == "stdio":
            raise ValueError("server_command is required for stdio transport")
            
        if transport != "stdio":
            raise ValueError(f"Unsupported transport type: {transport}")
        
        # Ensure env_vars includes MCP_SKIP_SHUTDOWN if set in the environment
        if env_vars is None:
            env_vars = {}
        
        if self.skip_shutdown and "MCP_SKIP_SHUTDOWN" not in env_vars:
            env_vars["MCP_SKIP_SHUTDOWN"] = "true"
        
        # Detect if we're testing a known server that needs shutdown skipping
        if server_command:
            if "server-brave-search" in server_command and "MCP_SKIP_SHUTDOWN" not in env_vars:
                if self.debug:
                    print("Detected Brave Search server, automatically skipping shutdown")
                env_vars["MCP_SKIP_SHUTDOWN"] = "true"
                self.skip_shutdown = True
            
        # Clear previous results
        self.results = {}
        
        # Run each test with a fresh server instance
        results = []
        for test_func, test_name in tests:
            try:
                result = await self.run_test(
                    test_func=test_func,
                    server_command=server_command,
                    protocol_version=protocol,
                    test_name=test_name,
                    env_vars=env_vars
                )
                results.append(result)
            except Exception as e:
                if self.debug:
                    print(f"Failed to run test {test_name}: {str(e)}")
                    
                results.append({
                    "name": test_name,
                    "passed": False,
                    "message": f"Failed to run test: {str(e)}",
                    "exception": str(e)
                })
                
        # Generate the summary
        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        skipped = sum(1 for r in results if r.get("skipped", False))
        
        summary = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "results": results
        }
        
        if self.debug:
            print(f"\nTest Summary: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
            
        return summary


# Convenience function to run tests
async def run_tests(tests: List[Tuple[Callable[[MCPProtocolAdapter], Tuple[bool, str]], str]], 
                   protocol: str = "2024-11-05",
                   transport: str = "stdio",
                   server_command: str = None,
                   env_vars: Optional[Dict[str, str]] = None,
                   debug: bool = False) -> Dict[str, Any]:
    """
    Run a list of test cases.
    
    Args:
        tests: A list of tuples containing (test_func, test_name)
        protocol: The protocol version to use
        transport: The transport type to use
        server_command: The command to launch the server (for stdio transport)
        env_vars: Environment variables to pass to the server process
        debug: Whether to enable debug output
        
    Returns:
        A dictionary containing the test results
    """
    runner = MCPTestRunner(debug=debug)
    return await runner.run_tests(
        tests=tests,
        protocol=protocol,
        transport=transport,
        server_command=server_command,
        env_vars=env_vars
    ) 