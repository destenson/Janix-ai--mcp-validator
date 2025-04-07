#!/usr/bin/env python3
"""
Run tests against an HTTP MCP server.

This script runs tests against an HTTP MCP server.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp_testing.tests.base_protocol.test_initialization import TEST_CASES as INIT_TEST_CASES
from mcp_testing.tests.features.test_tools import TEST_CASES as TOOLS_TEST_CASES
from mcp_testing.tests.features.test_async_tools import TEST_CASES as ASYNC_TOOLS_TEST_CASES
from mcp_testing.transports.http import HttpTransportAdapter
from mcp_testing.protocols.v2025_03_26 import MCP2025_03_26Adapter
from mcp_testing.protocols.v2024_11_05 import MCP2024_11_05Adapter


async def run_test(test_func, test_name, protocol_adapter, debug=False):
    """Run a single test case against the HTTP protocol adapter."""
    if debug:
        print(f"\nRunning test: {test_name}")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Run the test
        passed, message = await test_func(protocol_adapter)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Build the result
        result = {
            "name": test_name,
            "passed": passed,
            "message": message,
            "duration": duration
        }
        
        if debug:
            status = "PASSED" if passed else "FAILED"
            print(f"Test {test_name}: {status} ({duration:.2f}s)")
            if message:
                print(f"  {message}")
                
        return result
        
    except Exception as e:
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Build the error result
        result = {
            "name": test_name,
            "passed": False,
            "message": f"Test raised exception: {str(e)}",
            "duration": duration,
            "exception": str(e)
        }
        
        if debug:
            print(f"Test {test_name}: ERROR ({duration:.2f}s)")
            print(f"  Exception: {str(e)}")
            
        return result


async def run_http_tests(tests, server_url, protocol_version, debug=False):
    """
    Run tests against an HTTP server.
    
    Args:
        tests: A list of tuples containing (test_func, test_name)
        server_url: URL of the MCP HTTP server
        protocol_version: The protocol version to use
        debug: Whether to enable debug logging
        
    Returns:
        Dictionary with test results
    """
    # Create the HTTP transport adapter with the Accept header including both JSON and SSE
    transport = HttpTransportAdapter(
        server_url=server_url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        },
        debug=debug,
        timeout=10.0  # Shorter timeout for quicker feedback
    )
    
    print(f"Connecting to HTTP server at {server_url}...")
    
    # Test connection with a simple OPTIONS request first
    try:
        import requests
        response = requests.options(server_url, timeout=5.0)
        response.raise_for_status()
        print(f"Server connection verified! Status: {response.status_code}")
    except Exception as e:
        print(f"Warning: Initial connection test failed: {str(e)}")
        print("Continuing anyway as the transport might still work...")
    
    # Start the transport
    if not transport.start():
        print(f"Failed to start HTTP transport to {server_url}")
        return {
            "total": len(tests),
            "passed": 0,
            "failed": len(tests),
            "results": [
                {
                    "name": test_name,
                    "passed": False,
                    "message": f"Failed to connect to HTTP server at {server_url}",
                    "duration": 0
                }
                for _, test_name in tests
            ]
        }
    
    try:
        # Create the protocol adapter
        if protocol_version == "2024-11-05":
            protocol_adapter = MCP2024_11_05Adapter(
                transport=transport,
                debug=debug
            )
        elif protocol_version == "2025-03-26":
            protocol_adapter = MCP2025_03_26Adapter(
                transport=transport,
                debug=debug
            )
        else:
            raise ValueError(f"Unsupported protocol version: {protocol_version}")
        
        # Initialize the connection
        await protocol_adapter.initialize()
        
        # Run each test
        results = []
        for test_func, test_name in tests:
            result = await run_test(test_func, test_name, protocol_adapter, debug)
            results.append(result)
            
            # If a test failed, it might have left the server in a bad state
            # We should re-initialize for each test to ensure a clean state
            if not result["passed"]:
                # Create a fresh protocol adapter
                if protocol_version == "2024-11-05":
                    protocol_adapter = MCP2024_11_05Adapter(
                        transport=transport,
                        debug=debug
                    )
                elif protocol_version == "2025-03-26":
                    protocol_adapter = MCP2025_03_26Adapter(
                        transport=transport,
                        debug=debug
                    )
                
                # Attempt to re-initialize
                try:
                    await protocol_adapter.initialize()
                except Exception as e:
                    if debug:
                        print(f"Failed to re-initialize after test failure: {str(e)}")
                    # Stop running tests if we can't re-initialize
                    break
        
        # Try to shut down gracefully
        try:
            await protocol_adapter.shutdown()
            await protocol_adapter.exit()
        except Exception as e:
            if debug:
                print(f"Warning: Shutdown failed: {str(e)}")
        
        # Collect results
        passed = sum(1 for r in results if r["passed"])
        failed = len(results) - passed
        
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": results
        }
    
    finally:
        # Always stop the transport
        transport.stop()


async def main():
    """Run the tests using HTTP transport."""
    parser = argparse.ArgumentParser(description="Run tests against an HTTP MCP server")
    parser.add_argument("--server-url", 
                       default="http://localhost:9000/mcp",
                       help="URL of the MCP HTTP server (default: http://localhost:9000/mcp)")
    parser.add_argument("--protocol-version", 
                       choices=["2024-11-05", "2025-03-26"], 
                       default="2025-03-26", 
                       help="Protocol version to use (default: 2025-03-26)")
    parser.add_argument("--test-modules", 
                       default="base_protocol tools",
                       help="Space-separated list of test modules to run")
    parser.add_argument("--debug", 
                       action="store_true", 
                       help="Enable debug logging")
    parser.add_argument("--output-file", 
                       help="File to write results to (in JSON format)")
    parser.add_argument("--markdown", 
                       action="store_true", 
                       help="Generate a Markdown compliance report")
    parser.add_argument("--markdown-file", 
                       help="Filename for the Markdown report (default: auto-generated)")
    
    args = parser.parse_args()
    
    # Collect test cases based on modules specified
    test_modules = args.test_modules.split()
    all_tests = []
    
    if "base_protocol" in test_modules:
        print("Including base protocol tests")
        all_tests.extend(INIT_TEST_CASES)
    
    if "tools" in test_modules:
        print("Including tools tests")
        all_tests.extend(TOOLS_TEST_CASES)
    
    # Include async tool tests only for 2025-03-26
    if "async" in test_modules and args.protocol_version == "2025-03-26":
        print("Including async tools tests")
        all_tests.extend(ASYNC_TOOLS_TEST_CASES)
    
    print(f"Running {len(all_tests)} tests against {args.server_url}")
    
    # Run the tests
    results = await run_http_tests(
        tests=all_tests,
        server_url=args.server_url,
        protocol_version=args.protocol_version,
        debug=args.debug
    )
    
    # Print results
    print(f"\nTest Results:")
    print(f"Total tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    # Write results to file if requested
    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(results, f, indent=2)
            print(f"\nResults written to {args.output_file}")
    
    # Generate Markdown report if requested
    if args.markdown or args.markdown_file:
        from mcp_testing.utils.reporter import results_to_markdown
        report_path = results_to_markdown(
            results=results,
            server_command=f"HTTP Server at {args.server_url}",
            protocol_version=args.protocol_version,
            output_file=args.markdown_file
        )
        print(f"\nMarkdown compliance report generated: {report_path}")
    
    # Return non-zero exit code if any tests failed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 