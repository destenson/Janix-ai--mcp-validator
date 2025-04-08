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

## Repository Organization

The repository is organized as follows:

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

## Testing Pip-Installed MCP Servers

The testing framework supports testing MCP servers that are installed via pip (like `mcp-server-fetch`). To successfully test such servers:

1. **Install the server in the same environment as the testing framework:**

```bash
# Ensure you're in the correct virtual environment where the testing framework is installed
source .venv/bin/activate  # Or activate your virtual environment

# Install the server package and its dependencies
pip install mcp-server-fetch sseclient-py==1.7.2  # For the fetch server example
```

2. **Run the tests specifying the module-style command:**

```bash
# Run basic interaction test (simplest test)
python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05

# Run compliance tests with tools-only mode
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-mode tools

# Run complete compliance tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
```

### Troubleshooting Pip-Installed Servers

If you encounter issues when testing pip-installed servers:

- **"Failed to start transport" error**: Ensure the server is installed in the same environment as the testing framework
- **Module not found errors**: Verify the module is installed with `python -c "import module_name"`
- **Dependency issues**: Make sure all required dependencies are installed

For more details, see the [Pip-Installed Servers Plan](plan_pip.md).

## MCP Testing Framework

A flexible testing framework for verifying MCP server compliance with protocol specifications.

### Key Features

- Support for both the 2024-11-05 and 2025-03-26 protocol versions
- Support for both STDIO and HTTP transport protocols
- Dynamic tool testing that adapts to any server's capabilities
- Detailed compliance reporting
- Configurable test modes for targeted functionality testing
- Comprehensive specification requirement testing (MUST, SHOULD, MAY)
- Server configuration system for testing diverse implementations

### Server Configuration System

The testing framework includes a flexible configuration system for working with different server implementations:

- **JSON Configuration Files**: Add server-specific configurations in `mcp_testing/server_configs/`
- **Auto-Detection**: The system can identify servers based on command patterns
- **Environment Management**: Automatically manages required environment variables for each server
- **Extensible**: Support for new servers without modifying code

Example usage with server-specific configuration:

```bash
# Server requiring API keys can be tested with direct environment variables
API_KEY="your_key" python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server"

# Or using default values pattern
MCP_DEFAULT_API_KEY="default_key" python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server"
```

For more details, see the [Server Configurations README](mcp_testing/server_configs/README.md).

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
# Skip async tests for older servers
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-async

# Test only dynamic tool capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only

# Use a specific subset of tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-mode tools

# Skip specific tests that are known to fail
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-tests "test_shutdown,test_exit_after_shutdown"

# Auto-detect server capabilities and protocol version
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --auto-detect
```

For HTTP testing, additional options include:

```bash
# Enable debug output to see detailed request/response information
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --debug
```

### Generating Compliance Reports

The testing framework can generate detailed compliance reports:

```bash
# Generate a compliance report for STDIO server
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"

# Generate a compliance report for HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir "./reports"
```

The generated reports include:
- Summary of test results
- Detailed listing of passed and failed tests
- Specification coverage metrics
- Server capabilities overview
- Compliance status and score

### Running the Test Suite

```bash
# Run the entire test suite
pytest

# Run specific test modules
pytest mcp_testing/tests/base_protocol/
```

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
