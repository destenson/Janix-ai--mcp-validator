# MCP Protocol Validator

A testing suite and reference implementation for the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol).

## Summary

The MCP Protocol Validator provides a comprehensive environment for testing and validating MCP server implementations. With reference implementations for both STDIO and HTTP transports, along with an extensive testing framework, it ensures developers can verify their servers comply with the MCP specification. The modular architecture supports various server configurations, transport methods, and provides detailed compliance reporting, making it an essential tool for MCP server development and validation.

## Overview

This repository contains:

1. **STDIO Reference Implementations**:
   - 2024-11-05 protocol version
   - 2025-03-26 protocol version
2. **HTTP Reference Implementation**:
   - HTTP transport with WebSockets for bidirectional communication
3. **FastMCP HTTP SSE Implementation**:
   - HTTP transport with SSE for efficient one-way streaming
4. **MCP Testing Framework**: A comprehensive testing framework for verifying MCP server implementations

All implementations have been thoroughly tested against the MCP protocol specifications.

## Compliance Testing Results

## Reference Implementations

### STDIO Reference Implementations

Two reference implementations using STDIO for transport:

#### 2024-11-05 Protocol Version

A simple reference implementation that supports:

- Basic protocol operations (initialization, shutdown)
- Synchronous tool calls

```bash
# Run the server
python ./ref_stdio_server/stdio_server_2024_11_05.py
```

#### 2025-03-26 Protocol Version

An enhanced implementation with additional features:

- Support for asynchronous tool calls
- Resources capability

```bash
# Run the server
python ./ref_stdio_server/stdio_server_2025_03_26.py
```

#### Supported Tools

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (2025-03-26 version only)

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

### FastMCP HTTP Server with SSE Transport

A reference implementation using HTTP with Server-Sent Events (SSE) for asynchronous communication:

- HTTP-based JSON-RPC 2.0 with SSE transport
- Full compliance with MCP 2025-03-26 specification
- Robust session and connection management
- Support for asynchronous tool calls

```bash
# Run the server with default settings (localhost:8085)
python ./ref_http_server/fastmcp_server.py --debug

# Run compliance tests
./test_improved_fastmcp.sh
```

#### Key Features

- **SSE Transport**: Efficient one-way streaming from server to client
- **Connection Management**: Keepalives, reconnection support, error handling
- **Session Management**: Activity tracking, stale session cleanup
- **HTTP Integration**: Works with standard proxies, CORS support

#### Supported Tools

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (demonstrates async capabilities)

#### Implementation Details

The server follows best practices for HTTP-based MCP:

- Client sends JSON-RPC requests to `/mcp` endpoint
- Server responds with 202 Accepted for async processing
- Results are sent via SSE connection at `/notifications`
- Client correlates responses using request IDs

#### Testing the FastMCP Server

The `test_improved_fastmcp.sh` script automates testing:
- Starts the server
- Runs compliance tests
- Generates a detailed report
- Cleans up server processes

```bash
# Run the full test suite
./test_improved_fastmcp.sh
```

This implementation provides a lightweight alternative to WebSockets while maintaining full protocol compliance.

### HTTP Reference Implementation

A reference implementation using HTTP transport with:

- JSON-RPC 2.0 over HTTP implementation
- Support for protocol version 2025-03-26
- Synchronous and asynchronous tool calls
- Batch request support
- CORS support for browser clients

```bash
# Start the reference HTTP server (runs on port 8088)
python ref_http_server/reference_mcp_server.py

# Run compliance tests and generate a detailed report
python ref_http_server/http_compliance_test.py --output-dir reports
```

The compliance test will:
- Run a comprehensive test suite
- Generate a detailed markdown report in the reports directory
- Test core functionality including:
  - Protocol initialization
  - Tools functionality (echo, add, sleep)
  - Error handling
  - Batch requests
  - Session management
  - Protocol negotiation
  - Ping utility

See the [HTTP Server README](ref_http_server/README.md) for more details.

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
# Basic interaction test
python -m mcp_testing.scripts.basic_interaction --server-command "./minimal_mcp_server/minimal_mcp_server.py"

# Full compliance test
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26
```

#### For HTTP Servers:

```bash
# HTTP test
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

#### For HTTP with SSE Servers:

```bash
# FastMCP with SSE test
./test_improved_fastmcp.sh
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

#### Troubleshooting FastMCP SSE Transport

- **Connection issues**: Ensure no proxies or load balancers terminate idle connections
- **Session ID errors**: Client must parse session ID from `Connected to session xxx` format
- **Message delivery failures**: Verify the session ID is passed in all requests

See the [FastMCP Server README](ref_http_server/README.md) for more details.

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
```

**HTTP Testing:**

```bash
# Using the HTTP test script
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

**HTTP with SSE Transport Testing:**

```bash
# Using the FastMCP test script
./test_improved_fastmcp.sh
```

The SSE transport implementation demonstrates an efficient alternative to WebSockets for MCP servers, with better compatibility with standard HTTP infrastructure and simpler client handling.

#### Test Customization Options

```bash
# Skip async tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-async

# Test only tools
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-mode tools

# Skip specific tests
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --skip-tests "test_shutdown,test_exit_after_shutdown"

# Set custom timeouts
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --test-timeout 30 --tools-timeout 15
```

#### Generating Compliance Reports

```bash
# STDIO server report
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"

# HTTP server report
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir "./reports"

# FastMCP HTTP with SSE server report
./test_improved_fastmcp.sh
```

Reports include:
- Summary of test results
- Detailed listing of passed and failed tests
- Specification coverage metrics
- Server capabilities overview

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

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
