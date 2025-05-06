# Reference MCP STDIO Server

A reference implementation of an MCP (Model Conversation Protocol) server that uses standard input/output (STDIO) as its transport layer. This server implements both the `2024-11-05` and `2025-03-26` protocol versions.

## Overview

This server implements the MCP protocol and provides a reference implementation that passes all validation tests for both the `2024-11-05` and `2025-03-26` protocol versions.

## Status Update

**✅ All tests now pass successfully for both protocol versions!**

The server has been validated with the MCP Testing Framework and passes all compliance tests for both protocol versions.

## Features

- Full compliance with MCP protocol specifications:
  - Version `2024-11-05`
  - Version `2025-03-26`
- Implements all core protocol methods:
  - `initialize`/`initialized`
  - `shutdown`/`exit`
  - `tools/list` and `tools/call`
  - `server/info`
- Tools support with sample implementations:
  - Echo - Simple text echo
  - Add - Basic arithmetic
  - Sleep - Long-running async operation
- Async tool support:
  - `tools/call-async`
  - `tools/result`
  - `tools/cancel`
- Proper error handling with JSON-RPC error codes
- Protocol version validation
- Comprehensive error handling
- Batch request support

## Usage

### Running the server directly

For 2024-11-05 protocol version:
```bash
./stdio_server_2024_11_05.py
```

For 2025-03-26 protocol version:
```bash
./stdio_server_2025_03_26.py
```

Debug mode can be enabled with the `MCP_DEBUG` environment variable:

```bash
MCP_DEBUG=true ./stdio_server_2024_11_05.py
# or
MCP_DEBUG=true ./stdio_server_2025_03_26.py
```

### Testing with the MCP Protocol Validator

The server can be tested with the official MCP Testing Framework:

For 2024-11-05:
```bash
python -m mcp_testing.scripts.run_stdio_tests --server-command "./ref_stdio_server/stdio_server_2024_11_05.py" --protocol-version 2024-11-05 --debug
```

For 2025-03-26:
```bash
python -m mcp_testing.scripts.run_stdio_tests --server-command "./ref_stdio_server/stdio_server_2025_03_26.py" --protocol-version 2025-03-26 --debug
```

## Protocol Support Matrix

| Feature | 2024-11-05 | 2025-03-26 |
|---------|------------|------------|
| Core Protocol | ✅ | ✅ |
| Tools | ✅ | ✅ |
| Async Tools | ❌ | ✅ |
| Resources | ❌ | ✅ |
| Prompt | ❌ | ❌ |
| Utilities | ❌ | ❌ |
| Batch Requests | ❌ | ✅ |
| Streaming | ❌ | ❌ |

## Implementation Details

- The server is implemented in Python with no external dependencies
- Communication is via standard input/output (STDIO)
- Supports JSON-RPC 2.0 protocol for all communications
- Error handling follows the JSON-RPC 2.0 specification
- Async tool support with proper cancellation handling
- Resource management capabilities

## Files

- `stdio_server_2024_11_05.py` - Server implementation for protocol version 2024-11-05
- `stdio_server_2025_03_26.py` - Server implementation for protocol version 2025-03-26
- `README.md` - This documentation file

## License

AGPL-3.0-or-later

This server is provided as a reference implementation for educational purposes.