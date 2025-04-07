# MCP Testing Framework

A modular and extensible testing framework for verifying MCP (Model Conversation Protocol) server implementations.

## Overview

This framework provides a set of tools and utilities for testing MCP servers against the protocol specifications. It supports both STDIO and HTTP transports, and can test implementations of both the 2024-11-05 and 2025-03-26 protocol versions.

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
  - `test_tools.py`: Tests for synchronous tool calls
  - `test_async_tools.py`: Tests for asynchronous tool calls

### Utils

The `utils` module provides utility classes and functions:

- `runner.py`: Test runner for executing test cases

### Scripts

The `scripts` module provides command-line scripts for running tests:

- `run_stdio_tests.py`: Run tests against an STDIO MCP server

## Usage

### Running Tests

To run tests against an STDIO MCP server:

```bash
python -m mcp_testing.scripts.run_stdio_tests --server-command "/path/to/server" --protocol-version 2025-03-26 --debug
```

Options:
- `--server-command`: Command to start the server
- `--protocol-version`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--debug`: Enable debug output
- `--output-file`: File to write results to (JSON format)

### Testing Async Tools

For testing async tool functionality (2025-03-26 protocol), the framework includes:

1. `test_async_tool_support`: Verifies that the server advertises async tool support
2. `test_async_echo_tool`: Tests basic async tool execution
3. `test_async_long_running_tool`: Tests a long-running async operation with status polling
4. `test_async_tool_cancellation`: Tests cancellation of in-progress async operations

Example:
```bash
# Test async functionality in the minimal_mcp_server
python -m mcp_testing.scripts.run_stdio_tests --server-command "../minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --debug
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