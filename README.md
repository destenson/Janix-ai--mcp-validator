# MCP Protocol Validator

A testing suite and reference implementation for the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol).

## Overview

This repository contains:

1. **Minimal MCP Server**: A reference implementation using STDIO transport
2. **Minimal HTTP MCP Server**: A reference implementation using HTTP transport
3. **MCP Testing Framework**: A comprehensive testing framework for verifying MCP server implementations

The current implementation is fully compliant with the latest MCP protocol specification (2025-03-26).

✅ All tests pass for the reference implementations!

## Repository Organization

```
.
├── mcp_testing/                # Testing framework
│   ├── bin/                    # Executable scripts
│   ├── http/                   # HTTP testing module
│   ├── protocols/              # Protocol version tests
│   ├── scripts/                # Command-line tools
│   ├── server_configs/         # Server-specific configuration files
│   ├── stdio/                  # STDIO testing module
│   ├── transports/             # Transport layer implementations
│   └── utils/                  # Shared utilities
├── minimal_http_server/        # HTTP server reference implementation
├── minimal_mcp_server/         # STDIO server reference implementation
├── reports/                    # Generated test reports
├── schema/                     # JSON Schema definitions
└── specification/              # Protocol specifications
```

Each directory contains its own README with specific documentation.

---

## Reference Implementations

### Minimal MCP Server (STDIO)

A simple reference implementation that uses STDIO for transport and supports:

- Basic protocol operations (initialization, shutdown)
- Synchronous tool calls
- Asynchronous tool calls (for 2025-03-26)
- Utility tools for file system operations

```bash
# Run the server
python ./minimal_mcp_server/minimal_mcp_server.py
```

#### Supported Tools

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (useful for testing async operations)
- `list_directory`: List files in a directory
- `read_file`: Read a file
- `write_file`: Write a file

### Minimal HTTP MCP Server

A reference implementation using HTTP transport with:

- JSON-RPC 2.0 over HTTP implementation
- Support for both protocol versions (2024-11-05 and 2025-03-26)
- Synchronous and asynchronous tool calls
- Resources capability (for 2025-03-26)
- Batch request support
- CORS support for browser clients

```bash
# Run the server with default settings (localhost:8000)
python ./minimal_http_server/minimal_http_server.py

# Run with custom host and port
python ./minimal_http_server/minimal_http_server.py --host 0.0.0.0 --port 8080

# Run a basic HTTP test suite
python ./minimal_http_server/test_http_server.py

# Run compliance tests against the HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26
```

See the [HTTP Server README](minimal_http_server/README.md) for more details.

---

## MCP Testing Framework

A flexible framework for verifying MCP server compliance with protocol specifications.

### Key Features

- Support for both 2024-11-05 and 2025-03-26 protocol versions
- Support for both STDIO and HTTP transport protocols
- Dynamic tool testing that adapts to server capabilities
- Detailed compliance reporting
- Configurable test modes for targeted functionality testing
- Comprehensive specification requirement testing (MUST, SHOULD, MAY)
- Server configuration system for diverse implementations

### Quick Start

#### For STDIO Servers:

```bash
# Basic interaction - simplest test to verify server works
python -m mcp_testing.scripts.basic_interaction --server-command "./minimal_mcp_server/minimal_mcp_server.py"

# Run a full compliance test
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26
```

#### For HTTP Servers:

```bash
# Quick HTTP test
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Simple connectivity check
python minimal_http_server/check_server.py http://localhost:8000/mcp
```

### Testing Pip-Installed MCP Servers

To test MCP servers installed via pip (like `mcp-server-fetch`):

1. **Install in the same environment as the testing framework:**

```bash
# Ensure you're in the correct virtual environment
source .venv/bin/activate

# Install the server package and dependencies
pip install mcp-server-fetch sseclient-py==1.7.2  # For the fetch server example
```

2. **Run tests with module-style command:**

```bash
# Basic interaction test
python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05

# Compliance tests with tools-only mode
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-mode tools
```

3. **Handling timeout issues:**

```bash
# Set timeouts for tools tests vs. other tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-timeout 30 --tools-timeout 15
```

Tool-related tests that timeout are treated as non-critical, allowing testing to continue.

#### Troubleshooting Pip-Installed Servers

- **"Failed to start transport" error**: Ensure server is installed in the same environment
- **Module not found errors**: Verify module installation with `python -c "import module_name"`
- **Dependency issues**: Install all required dependencies
- **Hanging/timeout issues**: Use timeout parameters for appropriate values

### Advanced Testing Options

#### Server Configuration System

The framework includes a configuration system for different server implementations:

- **JSON Configuration Files**: Server-specific configurations in `mcp_testing/server_configs/`
- **Auto-Detection**: Identifies servers based on command patterns
- **Environment Management**: Manages required environment variables for each server

Example usage:

```bash
# Server requiring API keys
API_KEY="your_key" python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server"

# Using default values pattern
MCP_DEFAULT_API_KEY="default_key" python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server"
```

See [Server Configurations README](mcp_testing/server_configs/README.md) for details.

#### Transport-Specific Testing

**STDIO Testing:**

```bash
# Full compliance test
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26

# Specification requirement tests only
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --spec-coverage-only --protocol-version 2025-03-26
```

**HTTP Testing:**

```bash
# Using the HTTP test script
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Using the executable script
./mcp_testing/bin/http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

#### Test Customization Options

```bash
# Skip async tests for older servers
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-async

# Test only dynamic tool capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only

# Use specific subset of tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-mode tools

# Skip tests known to fail
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-tests "test_shutdown,test_exit_after_shutdown"

# Auto-detect server capabilities and protocol version
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --auto-detect

# Set custom timeouts
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-timeout 30 --tools-timeout 15

# HTTP debug output
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --debug
```

#### Generating Compliance Reports

```bash
# STDIO server report
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"

# HTTP server report
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir "./reports"
```

Reports include:
- Summary of test results
- Detailed listing of passed and failed tests
- Specification coverage metrics
- Server capabilities overview
- Compliance status and score

#### Basic Testing

For servers with potential issues:

```bash
# Verify server initialization and list tools
python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
```

This script:
- Starts the server
- Sends initialization request
- Verifies response
- Lists tools (if server responds correctly)
- Terminates gracefully

Useful for initial verification and troubleshooting.

### Running the Test Suite

```bash
# Run the entire test suite
pytest

# Run specific test modules
pytest mcp_testing/tests/base_protocol/
```

---

## Summary

The MCP Protocol Validator provides a comprehensive environment for testing and validating MCP server implementations. With reference implementations for both STDIO and HTTP transports, along with an extensive testing framework, it ensures developers can verify their servers comply with the MCP specification. The modular architecture supports various server configurations, transport methods, and provides detailed compliance reporting, making it an essential tool for MCP server development and validation.

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
