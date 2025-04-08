# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP HTTP Testing Module

This module provides tools for testing MCP servers that use HTTP as the transport layer.

## Components

- **tester.py**: Core `MCPHttpTester` class that implements the test suite
- **session_validator.py**: `MCPSessionValidator` class for testing server session handling
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

# Session validation testing
python mcp_testing/scripts/session_test.py --server-url http://localhost:8888/mcp
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

### Testing Session Handling

The module provides a dedicated validator for testing session management:

```python
from mcp_testing.http.session_validator import MCPSessionValidator
from mcp_testing.http.utils import wait_for_server

# Wait for server to be accessible
if wait_for_server("http://localhost:8888/mcp"):
    # Create session validator
    validator = MCPSessionValidator("http://localhost:8888/mcp", debug=True)
    
    # Run all session tests
    validator.run_all_tests()
    
    # Or run specific session tests
    session_id = validator.initialize_and_get_session()
    validator.test_valid_session_id(session_id)
    validator.test_tools_list_with_session(session_id)
```

## Test Coverage

The HTTP testing module currently tests:

1. **CORS Support**: Verifies that the server properly handles OPTIONS requests and returns CORS headers
2. **Initialization**: Tests the server's ability to initialize and return a session ID
3. **Tools Listing**: Verifies that the server can list available tools
4. **Tool Execution**: Tests basic tool execution (echo, add)
5. **Async Tools**: Tests async tool execution with the sleep tool
6. **Session Handling**: Tests server's ability to maintain and validate sessions via the `Mcp-Session-Id` header

### Session Test Coverage

The session validator specifically tests:

1. **Session Creation**: Tests that the server generates a valid session ID during initialization
2. **Session Validation**: Tests that the server properly accepts or rejects requests based on session ID validity
3. **Session Persistence**: Tests that the server maintains state across multiple requests with the same session ID
4. **Missing Session**: Tests server behavior when session ID is not provided
5. **Invalid Session**: Tests server behavior when an invalid session ID is provided

## Adding New Tests

To add new tests, add methods to the `MCPHttpTester` class in `tester.py` or the `MCPSessionValidator` class in `session_validator.py`. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your new test method to the list in the `run_all_tests` method to include it in the full test suite. 