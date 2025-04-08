# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP STDIO Testing Module

This module provides tools for testing MCP servers that use Standard Input/Output (STDIO) as the transport layer.

## Components

- **tester.py**: Core `MCPStdioTester` class that implements the test suite
- **utils.py**: Helper utilities for server process management and other common tasks
- **cli.py**: Command-line interface for running tests

## Usage

### From the Command Line

The STDIO testing module can be run directly from the command line:

```bash
# Using the bin script
./bin/stdio_test python /path/to/your/server.py

# Using Python module import
python -m mcp_testing.stdio.cli python /path/to/your/server.py
```

### From Python Code

You can also use the module programmatically:

```python
from mcp_testing.stdio.tester import MCPStdioTester

# Create tester with server command
tester = MCPStdioTester("python /path/to/your/server.py", debug=True)

# Run all tests
tester.run_all_tests()

# Or run specific tests
tester.start_server()
tester.initialize()
tester.list_tools()
tester.test_echo_tool()
tester.stop_server()
```

## Test Coverage

The STDIO testing module currently tests:

1. **Server Start**: Verifies that the server process starts successfully
2. **Initialization**: Tests the server's ability to initialize and return a session ID
3. **Tools Listing**: Verifies that the server can list available tools
4. **Tool Execution**: Tests basic tool execution (echo, add)
5. **Async Tools**: Tests async tool execution with the sleep tool

## Adding New Tests

To add new tests, add methods to the `MCPStdioTester` class in `tester.py`. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your new test method to the list in the `run_all_tests` method to include it in the full test suite. 