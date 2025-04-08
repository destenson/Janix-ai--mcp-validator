# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP HTTP Testing Module

This module provides tools for testing MCP servers that use HTTP as the transport layer.

## Components

- **tester.py**: Core `MCPHttpTester` class that implements the test suite
- **utils.py**: Helper utilities for server connectivity checks and other common tasks
- **cli.py**: Command-line interface for running tests

## Usage

### From the Command Line

The HTTP testing module can be run directly from the command line:

```bash
# Using the bin script
./bin/http_test --server-url http://localhost:9000/mcp

# Using Python module import
python -m mcp_testing.http.cli --server-url http://localhost:9000/mcp
```

### From Python Code

You can also use the module programmatically:

```python
from mcp_testing.http.tester import MCPHttpTester
from mcp_testing.http.utils import wait_for_server

# Wait for server to be accessible
if wait_for_server("http://localhost:9000/mcp"):
    # Create tester
    tester = MCPHttpTester("http://localhost:9000/mcp", debug=True)
    
    # Run all tests
    tester.run_all_tests()
    
    # Or run specific tests
    tester.initialize()
    tester.list_tools()
    tester.test_echo_tool()
```

## Test Coverage

The HTTP testing module currently tests:

1. **CORS Support**: Verifies that the server properly handles OPTIONS requests and returns CORS headers
2. **Initialization**: Tests the server's ability to initialize and return a session ID
3. **Tools Listing**: Verifies that the server can list available tools
4. **Tool Execution**: Tests basic tool execution (echo, add)
5. **Async Tools**: Tests async tool execution with the sleep tool

## Adding New Tests

To add new tests, add methods to the `MCPHttpTester` class in `tester.py`. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your new test method to the list in the `run_all_tests` method to include it in the full test suite. 