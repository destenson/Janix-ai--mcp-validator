# Minimal MCP Server

A reference implementation of a minimal MCP (Model Conversation Protocol) server that supports both HTTP and STDIO transports.

## Overview

This server implements the MCP protocol and provides a minimal yet complete set of functionality to pass all validation tests. It supports both the `2024-11-05` and `2025-03-26` protocol versions.

## Features

- Full compliance with MCP protocol specification
- Support for both protocol versions:
  - `2024-11-05`
  - `2025-03-26`
- Implements all core protocol methods:
  - `initialize`/`initialized`
  - `shutdown`/`exit`
  - `tools/list` and `tools/call`
  - `resources/list`, `resources/get`, and `resources/create`
  - `prompt/completion`, `prompt/models`
  - `server/info`
- Tools support with sample implementations:
  - Echo - Simple text echo
  - Add - Basic arithmetic
  - File system operations (list_directory, read_file, write_file)
- Resources management (for protocol version `2025-03-26`)
- Prompt completion capabilities
- Proper batch request handling
- Protocol version negotiation
- Comprehensive error handling

## Usage

### Running the server directly

```bash
./minimal_mcp_server.py
```

The protocol version can be set via the `MCP_PROTOCOL_VERSION` environment variable:

```bash
MCP_PROTOCOL_VERSION=2024-11-05 ./minimal_mcp_server.py
```

Debug mode can be enabled with the `MCP_DEBUG` environment variable:

```bash
MCP_DEBUG=true ./minimal_mcp_server.py
```

### Testing the server

This repository includes a simple test script that validates the server's functionality:

```bash
# Run basic tests with protocol version 2024-11-05
./test_minimal_server.py

# Run full test suite with protocol version 2024-11-05
./test_minimal_server.py --full

# Test with protocol version 2025-03-26
./test_minimal_server.py --protocol-version 2025-03-26 --full
```

### Using with the MCP Protocol Validator

The server can be tested with the official MCP Protocol Validator:

```bash
# From the validator directory
./run_validator.py --transport stdio \
  --server-command "./minimal_mcp_server/minimal_mcp_server.py" \
  --protocol-version 2024-11-05
```

Or using environment variables:

```bash
export MCP_PROTOCOL_VERSION=2024-11-05
export MCP_TRANSPORT_TYPE=stdio
export MCP_SERVER_COMMAND="./minimal_mcp_server/minimal_mcp_server.py"

# Run a specific test
./run_validator.py --transport stdio \
  --server-command "./minimal_mcp_server/minimal_mcp_server.py" \
  --protocol-version 2024-11-05 \
  --test-module test_base_protocol \
  --test-class TestBasicSTDIO \
  --test-method test_initialization
```

### Additional Testing Tools

The repository includes several testing scripts:

- `test_minimal_server.py`: Dedicated test script included in this directory
- `debug_server.py`: Simple debug script for basic interaction
- `debug_complete_test.py`: Comprehensive test of all core functionality
- `validate_minimal_server.py`: Run the validator tests against this server
- `comprehensive_validator.py`: Run all validation tests with detailed reporting

## Protocol Support Matrix

| Feature | 2024-11-05 | 2025-03-26 |
|---------|------------|------------|
| Core Protocol | ✅ | ✅ |
| Tools | ✅ | ✅ |
| Resources | ✅ | ✅ |
| Prompt | ✅ | ✅ |
| Utilities | ✅ | ✅ |
| Batch Requests | ✅ | ✅ |
| Streaming | 🔄 | 🔄 |

## Implementation Details

- The server is implemented in Python with no external dependencies
- Communication is via standard input/output (STDIO)
- Supports JSON-RPC 2.0 protocol for all communications
- Error handling follows the JSON-RPC 2.0 specification

## Files

- `minimal_mcp_server.py` - The main server implementation
- `test_minimal_server.py` - Test script to validate server functionality
- `README.md` - This documentation file

## License

AGPL-3.0-or-later

This server is provided as a reference implementation for educational purposes.