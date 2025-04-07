# MCP Testing Framework

A modular and extensible testing framework for verifying MCP (Model Conversation Protocol) server implementations.

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

## Components

### Transports

The `transports` module provides adapters for different communication mechanisms:

- `stdio.py`: Communication via standard input/output
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

### Utils

The `utils` module provides utility classes and functions:

- `runner.py`: Test runner for executing test cases
- `reporter.py`: Utilities for generating compliance reports

### Scripts

The `scripts` module provides command-line scripts for running tests:

- `compliance_report.py`: Comprehensive script to test any MCP server and generate reports

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
```

#### Options for Compliance Testing

- `--server-command`: Command to start the server (required)
- `--protocol-version`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--args`: Additional arguments to pass to the server command
- `--dynamic-only`: Only run tests that adapt to the server's capabilities
- `--skip-shutdown`: Skip the shutdown method (for servers that don't implement it)
- `--skip-async`: Skip async tool tests (for 2025-03-26)
- `--skip-tests`: Comma-separated list of test names to skip
- `--test-mode`: Testing mode (all, core, tools, async)
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

### Supporting New Protocol Versions

1. Create a new protocol adapter that extends `BaseMCPProtocolAdapter`
2. Implement all required methods from the base class
3. Add the new adapter to the protocol version mapping in the test runner

## License

MIT License 