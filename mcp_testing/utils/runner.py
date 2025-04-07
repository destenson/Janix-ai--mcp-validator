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
        if self.debug:
            print(f"\nRunning test: {test_name}")
        
        # Create a fresh transport adapter for each test
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
            await protocol_adapter.initialize()
            await protocol_adapter.send_initialized()
            
            # Run the test
            passed, message = await test_func(protocol_adapter)
            
            # Shutdown the connection
            await protocol_adapter.shutdown()
            await protocol_adapter.exit()
            
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
        
        summary = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": results
        }
        
        if self.debug:
            print(f"\nTest Summary: {passed}/{len(results)} passed ({failed} failed)")
            
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