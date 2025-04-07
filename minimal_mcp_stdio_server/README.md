# Minimal MCP STDIO Server

A minimal implementation of the MCP (Model Control Protocol) server using STDIO transport.

## Overview

This server implements the MCP protocol over STDIO (Standard Input/Output) and provides a minimal set of functionality to pass validation tests. It supports both the `2024-11-05` and `2025-03-26` protocol versions.

## Features

- Full compliance with MCP protocol specification
- Support for both protocol versions:
  - `2024-11-05`
  - `2025-03-26`
- Implements core protocol methods:
  - `initialize`/`initialized`
  - `shutdown`/`exit`
- Tools support with sample tools:
  - Echo
  - Add
  - File system operations
- Resources management (for protocol version `2025-03-26`)
- Prompt completion capabilities
- Proper batch request handling
- Protocol version negotiation
- Comprehensive error handling

## Usage

### Running the server directly

```bash
./minimal_mcp_stdio_server.py
```

### Using with the MCP Protocol Validator

```bash
export MCP_PROTOCOL_VERSION=2024-11-05
export MCP_TRANSPORT_TYPE=stdio
export MCP_SERVER_COMMAND="./minimal_mcp_stdio_server/minimal_mcp_stdio_server.py"

# Run a specific test
./run_validator.py --transport stdio \
  --server-command "./minimal_mcp_stdio_server/minimal_mcp_stdio_server.py" \
  --protocol-version 2024-11-05 \
  --test-module test_base_protocol \
  --test-class TestBasicSTDIO \
  --test-method test_initialization
```

### Testing Tools

The repository includes several testing scripts:

- `debug_server.py`: Simple debug script for basic interaction
- `debug_complete_test.py`: Comprehensive test of all core functionality
- `validate_minimal_server.py`: Run the validator tests against this server

## Protocol Support

| Feature | 2024-11-05 | 2025-03-26 |
|---------|------------|------------|
| Core Protocol | ✅ | ✅ |
| Tools | ✅ | ✅ |
| Resources | ✅ | ✅ |
| Prompt | ✅ | ✅ |
| Utilities | ✅ | ✅ |
| Batch Requests | ✅ | ✅ |

## License

This server is provided as a reference implementation for educational purposes. 