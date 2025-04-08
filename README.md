# MCP Protocol Validator

A testing suite and reference implementation for the [Model Conversation Protocol (MCP)](https://github.com/microsoft/aimcp).

## Components

This repository contains:

1. **Minimal MCP Server**: A reference implementation of an MCP server using STDIO transport
2. **Minimal HTTP MCP Server**: A reference implementation of an MCP server using HTTP transport
3. **MCP Testing Framework**: A robust testing framework for verifying MCP server implementations against the protocol specifications

## Status

The current implementation is fully compliant with the latest MCP protocol specification (2025-03-26).

✅ All tests pass for the reference implementations!

## Minimal MCP Server (STDIO)

A simple reference implementation of an MCP server that uses STDIO for transport and supports all protocol features:

- Basic protocol operations (initialization, shutdown)
- Synchronous tool calls
- Asynchronous tool calls (for 2025-03-26)
- Utility tools for file system operations

### Running the STDIO Server

```bash
# Run the server
python ./minimal_mcp_server/minimal_mcp_server.py
```

### Supported Tools

The minimal server implements these tools:

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (useful for testing async operations)
- `list_directory`: List files in a directory
- `read_file`: Read a file
- `write_file`: Write a file

## Minimal HTTP MCP Server

A reference implementation of an MCP server that uses HTTP for transport and supports all protocol features:

- JSON-RPC 2.0 over HTTP implementation
- Support for both MCP protocol versions (2024-11-05 and 2025-03-26)
- Synchronous and asynchronous tool calls
- Resources capability (for 2025-03-26)
- Batch request support
- CORS support for browser clients

### Running the HTTP Server

```bash
# Run the server with default settings (localhost:8000)
python ./minimal_http_server/minimal_http_server.py

# Run with custom host and port
python ./minimal_http_server/minimal_http_server.py --host 0.0.0.0 --port 8080
```

### HTTP Testing Tools

The HTTP server includes testing utilities:

```bash
# Run a basic HTTP test suite
python ./minimal_http_server/test_http_server.py

# Run compliance tests against the HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26
```

See the [HTTP Server README](minimal_http_server/README.md) for more details.

## MCP Testing Framework

A flexible testing framework for verifying MCP server compliance with protocol specifications.

### Key Features

- Support for both the 2024-11-05 and 2025-03-26 protocol versions
- Support for both STDIO and HTTP transport protocols
- Dynamic tool testing that adapts to any server's capabilities
- Detailed compliance reporting
- Configurable test modes for targeted functionality testing
- Comprehensive specification requirement testing (MUST, SHOULD, MAY)

### Transport Support

The testing framework supports multiple transport layers:

#### STDIO Testing

For servers that use standard input/output as the transport mechanism:

```bash
# Test the minimal STDIO server against the 2025-03-26 specification
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26

# Run only specification requirement tests (MUST, SHOULD, MAY)
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --spec-coverage-only --protocol-version 2025-03-26
```

#### HTTP Testing

For servers that implement MCP over HTTP:

```bash
# Using the dedicated HTTP test script
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Using the executable script in the bin directory
./mcp_testing/bin/http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

The HTTP testing module provides specific tests for HTTP-related features like CORS support, session management through headers, and proper HTTP status codes.

### Test Customization Options

The framework can be customized for different servers:

```bash
# Test a server with dynamic adaptation to its capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only --protocol-version 2025-03-26

# Test a specialized server that doesn't implement standard tools or shutdown method
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/specialized/server" --args "/path/to/directory" --skip-shutdown --dynamic-only --protocol-version 2024-11-05
```

For HTTP testing, additional options include:

```bash
# Configure connection retries and intervals
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --max-retries 5 --retry-interval 3

# Enable debug output for detailed logging
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --debug
```

### Generating Compliance Reports

The framework generates detailed Markdown reports:

```bash
# Generate a compliance report for STDIO server
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"

# Generate a compliance report for HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir "./reports"
```

Reports include a section on specification coverage, showing how well the server implements all MUST, SHOULD, and MAY requirements from the official protocol specification.

### Programmatic Usage

You can also use the testing modules directly in your Python code:

```python
# For HTTP testing
from mcp_testing.http.tester import MCPHttpTester
from mcp_testing.http.utils import wait_for_server

if wait_for_server("http://localhost:8000/mcp"):
    tester = MCPHttpTester("http://localhost:8000/mcp", debug=True)
    success = tester.run_all_tests()
```

## Extensions and Customization

The framework is designed to be extended:

- Add new test cases for additional protocol features
- Support new protocol versions as they are released
- Create custom test adaptations for specialized server implementations
- Contribute tests for uncovered specification requirements

### Adding HTTP Tests

To add new tests to the HTTP test suite, edit the `mcp_testing/http/tester.py` file and add methods to the `MCPHttpTester` class. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your test method to the list in the `run_all_tests` method to include it in the full test suite.

See the following documentation for detailed information:
- [MCP Testing README](mcp_testing/README.md) for general testing framework details
- [HTTP Testing README](mcp_testing/http/README.md) for HTTP-specific testing information

## License
SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
