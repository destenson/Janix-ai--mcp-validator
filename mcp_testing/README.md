# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP Testing Framework

A comprehensive testing framework for validating servers that implement the [Model Conversation Protocol (MCP)](https://github.com/microsoft/aimcp).

## Framework Architecture

The testing framework is organized into several key components:

### 1. Protocol Modules

Located in `./protocols/`:

- **base.py**: Base protocol testing functionality
- **v2024_11_05.py**: Tests for the 2024-11-05 protocol version
- **v2025_03_26.py**: Tests for the 2025-03-26 protocol version

### 2. Transport Modules

Located in `./transports/`:

- **base.py**: Base transport layer functionality
- **stdio.py**: Implementation for STDIO transport
- **http.py**: Implementation for HTTP transport

### 3. Specialized Testing Modules

- **./http/**: Comprehensive HTTP testing module
- **./stdio/**: Comprehensive STDIO testing module
- **./utils/**: Shared utility functions
- **./bin/**: Executable test scripts
- **./scripts/**: Command-line testing tools

## Usage Examples

### Using STDIO Testing

```python
from mcp_testing.stdio.tester import MCPStdioTester

# Create a tester instance
tester = MCPStdioTester("python /path/to/server.py", debug=True)

# Run all tests
success = tester.run_all_tests()

# Or run specific tests
tester.start_server()
tester.initialize()
tester.list_tools()
tester.test_echo_tool()
tester.stop_server()
```

### Using HTTP Testing

```python
from mcp_testing.http.tester import MCPHttpTester
from mcp_testing.http.utils import wait_for_server

# Wait for server to be accessible
if wait_for_server("http://localhost:9000/mcp"):
    # Create a tester instance
    tester = MCPHttpTester("http://localhost:9000/mcp", debug=True)
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Or run specific tests
    tester.initialize()
    tester.list_tools()
    tester.test_echo_tool()
```

### Using the Transport Layer Directly

```python
from mcp_testing.transports.http import HTTPTransport
from mcp_testing.transports.stdio import STDIOTransport

# Create a transport instance
http_transport = HTTPTransport("http://localhost:9000/mcp")
stdio_transport = STDIOTransport("python /path/to/server.py")

# Use the transport
http_transport.initialize()
stdio_transport.initialize()
```

## Adding New Tests

To add new tests to the framework:

1. Identify the appropriate component (protocol version, transport layer, etc.)
2. Add new test methods following the established patterns
3. Update the `run_all_tests` method to include your new tests
4. Add documentation about the new tests

## Directory Structure

```
mcp_testing/
├── __init__.py
├── bin/               # Executable scripts
├── http/              # HTTP testing module
├── protocols/         # Protocol version tests
├── scripts/           # Command-line tools
├── stdio/             # STDIO testing module
├── transports/        # Transport layer implementations
└── utils/             # Shared utilities
```

See the subdirectory README files for more detailed information about each component.

## Overview

This framework provides a set of tools and utilities for testing MCP servers against the protocol specifications. It supports both STDIO and HTTP transports, and can test implementations of both the 2024-11-05 and 2025-03-26 protocol versions.

The framework is designed to be flexible and adapt to any MCP server implementation, regardless of what specific tools or capabilities it provides.

## Status

**✅ All tests now pass for the reference implementation!**

The framework includes comprehensive test coverage for all protocol features, including:
- Basic protocol operations (initialization, shutdown, etc.)
- Synchronous tool calls
- Asynchronous tool calls (for 2025-03-26)
- Resources management
- Prompt/completion functionality
- Specification compliance (MUST, SHOULD, MAY requirements)

## Components

### Transports

The `transports` module provides adapters for different communication mechanisms:

- `stdio.py`: Communication via standard input/output
- `http.py`: Communication via HTTP protocol (for HTTP-based MCP servers)
- `base.py`: Base class defining the transport adapter interface

### Protocols

The `protocols` module provides adapters for different protocol versions:

- `v2024_11_05.py`: Implementation for the 2024-11-05 protocol
- `v2025_03_26.py`: Implementation for the 2025-03-26 protocol (with async tool support)
- `base.py`: Base class defining the protocol adapter interface

### Tests

The `tests` module contains test cases for various protocol features:

- `base_protocol/`: Tests for basic protocol functionality
- `features/`: Tests for specific protocol features
  - `test_tools.py`: Standard tests for synchronous tool calls
  - `test_async_tools.py`: Standard tests for asynchronous tool calls
  - `dynamic_tool_tester.py`: Dynamic tests that adapt to any server's tool capabilities
  - `dynamic_async_tools.py`: Dynamic tests for async tool functionality
- `specification_coverage.py`: Tests that verify compliance with MUST, SHOULD, and MAY requirements from the specification

### Utils

The `utils` module provides utility classes and functions:

- `runner.py`: Test runner for executing test cases
- `reporter.py`: Utilities for generating compliance reports

### Scripts

The `scripts` module provides command-line scripts for running tests:

- `compliance_report.py`: Comprehensive script to test any MCP server and generate reports

### HTTP Testing

The `http` module provides specific functionality for testing HTTP-based MCP servers:

- `tester.py`: Core testing class for HTTP servers
- `utils.py`: Utilities for server connectivity and networking
- `cli.py`: Command-line interface for HTTP testing

#### Testing HTTP Servers

You can test HTTP-based MCP servers using the dedicated tools:

```bash
# Using the bin script
./bin/http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Using the Python module
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

#### HTTP Testing Options

- `--server-url`: URL of the HTTP MCP server (required)
- `--protocol-version`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--debug`: Enable debug output
- `--max-retries`: Maximum number of connection retries
- `--retry-interval`: Seconds to wait between connection retries
- `--output-dir`: Directory to store report files (http_test.py only)

#### HTTP-Specific Tests

The HTTP tester includes additional tests specific to the HTTP transport:

- OPTIONS request handling (CORS headers)
- Proper HTTP status codes
- Session management via headers
- Content type validation
- HTTP-specific error handling

See the [HTTP Testing README](http/README.md) for more details.

## Usage

### Testing Any MCP Server

Our testing framework is designed to work with any MCP server implementation:

```bash
# Basic testing with default settings
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --protocol-version 2025-03-26

# Testing with dynamic adaptation to server capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only --protocol-version 2025-03-26

# Testing a server that doesn't implement the shutdown method
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-shutdown --protocol-version 2025-03-26

# Testing a specific subset of functionality
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-mode tools --protocol-version 2025-03-26

# Passing additional arguments to the server
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --args "/path/to/directory" --protocol-version 2025-03-26

# Running only specification compliance tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --spec-coverage-only --protocol-version 2025-03-26
```

#### Options for Compliance Testing

- `--server-command`: Command to start the server (required)
- `--protocol-version`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--args`: Additional arguments to pass to the server command
- `--dynamic-only`: Only run tests that adapt to the server's capabilities
- `--skip-shutdown`: Skip the shutdown method (for servers that don't implement it)
- `--skip-async`: Skip async tool tests (for 2025-03-26)
- `--skip-tests`: Comma-separated list of test names to skip
- `--test-mode`: Testing mode (all, core, tools, async, spec)
- `--spec-coverage-only`: Only run specification coverage tests
- `--debug`: Enable debug output
- `--json`: Generate a JSON report in addition to Markdown
- `--output-dir`: Directory to store the report files
- `--report-prefix`: Prefix for report filenames

### Testing Specialized Servers

For specialized servers such as file system servers that may not implement standard reference tools like "echo" and "add":

```bash
# Test a filesystem server with dynamic adaptation (will only test tools the server actually provides)
python -m mcp_testing.scripts.compliance_report \
    --server-command "/path/to/filesystem/server" \
    --args "/target/directory" \
    --protocol-version 2024-11-05 \
    --skip-shutdown \
    --dynamic-only
```

### Protocol Specification Coverage

The testing framework now includes specific tests for the MUST, SHOULD, and MAY requirements from the MCP specification. This provides a comprehensive check of a server's compliance with the official protocol requirements.

```bash
# Run all tests including specification coverage
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --protocol-version 2025-03-26

# Run only specification coverage tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --spec-coverage-only --protocol-version 2025-03-26

# Run a subset of tests plus specification coverage
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-mode spec --protocol-version 2025-03-26
```

The generated compliance report will include a section showing how well the server meets the specification requirements, broken down by MUST, SHOULD, and MAY categories:

```
## Specification Coverage

This report includes tests for requirements from the 2025-03-26 protocol specification.

| Requirement Type | Tested | Total | Coverage |
|-----------------|--------|-------|----------|
| **MUST** | 35 | 65 | 53.8% |
| **SHOULD** | 8 | 16 | 50.0% |
| **MAY** | 6 | 21 | 28.6% |
| **TOTAL** | 49 | 102 | 48.0% |
```

## Known Issues

The framework currently has two tests that are temporarily disabled due to implementation challenges:

### 1. Parallel Requests Test (`test_parallel_requests`)

**Issue**: This test attempts to verify that servers can handle multiple concurrent requests, but it's currently disabled due to implementation issues with asynchronous execution in the test framework.

**Details**: 
- The test tries to send multiple requests simultaneously and verify that responses match their corresponding requests.
- Current implementation challenges involve the synchronous nature of the `transport.send_request` method which doesn't work well with Python's async execution model.
- A more robust implementation would require modifications to the transport layer to properly support concurrent operations.

**Workaround**: 
- For now, this test is commented out in the `TEST_CASES` list in `specification_coverage.py`.
- Servers should still be designed to handle concurrent requests even though this test is currently disabled.

### 2. Shutdown Sequence Test (`test_shutdown_sequence`)

**Issue**: This test is temporarily disabled due to incompatibility with the test runner.

**Details**:
- The test attempts to verify that servers correctly handle the shutdown sequence.
- When the server shuts down during the test, it terminates the connection, which causes issues with the test runner's expectation of continuous communication.
- This makes it difficult to verify the server's behavior after a shutdown command is sent.

**Workaround**:
- The test is commented out in the `TEST_CASES` list in `specification_coverage.py`.
- Use the `--skip-shutdown` flag when running compliance tests against servers that don't handle the shutdown method or when you want to avoid this issue.
- In real-world scenarios, proper shutdown sequence handling should still be implemented.

### Future Improvements

We plan to address these issues in future updates by:
1. Refactoring the transport layer to better support concurrent operations.
2. Modifying the test runner to handle server disconnections more gracefully.
3. Implementing a more robust approach to testing shutdown sequences without disrupting the test runner.

Contributions to fix these issues are welcome!

## Extending the Framework

### Adding New Tests

1. Create a new test module in the appropriate directory
2. Define test functions with the signature:
   ```python
   async def test_feature(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
       # Test implementation
       return True, "Test passed"
   ```
3. Add the test to the `TEST_CASES` list at the end of the file

### Adding Specification Coverage Tests

1. Identify requirements from the specification (MUST, SHOULD, MAY statements)
2. Implement a test for each requirement following the pattern in `specification_coverage.py`
3. Update the `get_specification_coverage` function with accurate counts of tested requirements

### Supporting New Protocol Versions

1. Create a new protocol adapter that extends `BaseMCPProtocolAdapter`
2. Implement all required methods from the base class
3. Add the new adapter to the protocol version mapping in the test runner

## License

MIT License 