# Minimal MCP Server

A reference implementation of a minimal MCP (Model Conversation Protocol) server that supports both HTTP and STDIO transports.

## Overview

This server implements the MCP protocol and provides a minimal yet complete set of functionality to pass all validation tests. It supports both the `2024-11-05` and `2025-03-26` protocol versions.

## Status Update

**✅ All tests now pass successfully!**

Recent improvements include:
- Complete implementation of async tool functionality for the 2025-03-26 protocol
- Fixed method names to match the protocol specification (`tools/result` instead of `tools/get-result`)
- Proper advertising of async capabilities during server initialization
- Correct status reporting (running, completed, cancelled) for async operations
- Full test suite validation with the MCP Testing Framework

## Features

- Full compliance with MCP protocol specification
- Support for both protocol versions:
  - `2024-11-05`
  - `2025-03-26`
- Implements all core protocol methods:
  - `initialize`/`initialized`
  - `shutdown`/`exit`
  - `tools/list` and `tools/call`
  - `tools/call-async`, `tools/result`, and `tools/cancel` (for 2025-03-26)
  - `resources/list`, `resources/get`, and `resources/create`
  - `prompt/completion`, `prompt/models`
  - `server/info`
- Tools support with sample implementations:
  - Echo - Simple text echo
  - Add - Basic arithmetic
  - Sleep - Long-running operation for testing async functionality
  - File system operations (list_directory, read_file, write_file)
- Asynchronous tool execution (for protocol version `2025-03-26`)
  - Long-running operations with status tracking
  - Cancellation support
  - Result polling
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

For testing async functionality, use the 2025-03-26 protocol:

```bash
MCP_PROTOCOL_VERSION=2025-03-26 ./minimal_mcp_server.py
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

# Test with protocol version 2025-03-26 (including async functionality)
./test_minimal_server.py --protocol-version 2025-03-26 --full
```

### Using with the MCP Protocol Validator

The server can be tested with the official MCP Testing Framework:

```bash
# From the root directory
python -m mcp_testing.scripts.run_stdio_tests --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --debug
```

## Protocol Support Matrix

| Feature | 2024-11-05 | 2025-03-26 |
|---------|------------|------------|
| Core Protocol | ✅ | ✅ |
| Tools | ✅ | ✅ |
| Async Tools | ❌ | ✅ |
| Resources | ✅ | ✅ |
| Prompt | ✅ | ✅ |
| Utilities | ✅ | ✅ |
| Batch Requests | ✅ | ✅ |
| Streaming | 🔄 | 🔄 |

## Async Tools Implementation

The server implements the following methods for async tool support in the 2025-03-26 protocol:

1. **tools/call-async**: Initiates an asynchronous tool call and returns a call ID.
   ```json
   {"jsonrpc": "2.0", "id": "req1", "method": "tools/call-async", "params": {"name": "sleep", "arguments": {"duration": 10.0}}}
   ```

2. **tools/result**: Retrieves the current status or result of an async tool call.
   ```json
   {"jsonrpc": "2.0", "id": "req2", "method": "tools/result", "params": {"id": "call123"}}
   ```
   
   Possible status values:
   - "running": The tool call is still in progress
   - "completed": The tool call has completed successfully
   - "cancelled": The tool call was cancelled by the client

3. **tools/cancel**: Cancels an in-progress async tool call.
   ```json
   {"jsonrpc": "2.0", "id": "req3", "method": "tools/cancel", "params": {"id": "call123"}}
   ```

## Implementation Details

- The server is implemented in Python with no external dependencies
- Communication is via standard input/output (STDIO)
- Supports JSON-RPC 2.0 protocol for all communications
- Error handling follows the JSON-RPC 2.0 specification
- Async operations are managed through a simple task queue

## Files

- `minimal_mcp_server.py` - The main server implementation
- `test_minimal_server.py` - Test script to validate server functionality
- `README.md` - This documentation file

## License

AGPL-3.0-or-later

This server is provided as a reference implementation for educational purposes.