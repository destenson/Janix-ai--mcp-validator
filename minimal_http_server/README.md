# Minimal HTTP MCP Server

This directory contains a minimal implementation of the MCP (Model Conversation Protocol) server that uses HTTP as its transport layer. This implementation supports both the 2024-11-05 and 2025-03-26 protocol versions.

## Features

- JSON-RPC 2.0 over HTTP implementation
- Support for both MCP protocol versions (2024-11-05 and 2025-03-26)
- Basic tools: echo, add, sleep
- Support for synchronous and asynchronous tool calls
- Support for resources (2025-03-26 only)
- Error handling and validation
- CORS support for browser clients
- Batch request support

## Files

- `minimal_http_server.py`: The main HTTP server implementation
- `test_http_server.py`: A test script to verify server functionality

## Running the Server

To start the server:

```bash
# Start with default settings (localhost:8000)
python minimal_http_server.py

# Start with custom host and port
python minimal_http_server.py --host 0.0.0.0 --port 8080

# Enable debug logging
python minimal_http_server.py --debug
```

## Testing the Server

You can test the server using the included test script:

```bash
# Test with default settings
python test_http_server.py

# Test with custom server URL
python test_http_server.py --url http://localhost:8080

# Test with specific protocol version
python test_http_server.py --protocol-version 2024-11-05

# Enable debug logging
python test_http_server.py --debug
```

You can also run compliance tests against the server using the MCP testing framework:

```bash
# Run specification tests
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26

# Run capability tests
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26 --test-mode capability
```

## Manual Testing with curl

You can also test the server manually using curl:

```bash
# Initialize the server
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "curl", "version": "1.0.0"}, "capabilities": {"tools": true}}, "id": 1}'

# Get server info
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "server/info", "id": 2}'

# List available tools
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 3}'

# Call the echo tool
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "echo", "parameters": {"message": "Hello, MCP!"}}, "id": 4}'

# Call the add tool
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "add", "parameters": {"a": 5, "b": 7}}, "id": 5}'

# Make an async tool call (2025-03-26 only)
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call-async", "params": {"name": "sleep", "parameters": {"seconds": 2}}, "id": 6}'

# List resources (2025-03-26 only)
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "resources/list", "id": 7}'

# Send a batch request
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '[{"jsonrpc": "2.0", "method": "server/info", "id": 8}, {"jsonrpc": "2.0", "method": "echo", "params": {"message": "Batch message"}, "id": 9}]'

# Shutdown the server
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "shutdown", "id": 10}'
```

## Protocol Notes

### Version 2024-11-05
- Uses `inputSchema` for tool parameters
- Uses `arguments` for tool call parameters 
- Uses `mcp/tools` instead of `tools/list`
- Uses `mcp/tools/call` instead of `tools/call`

### Version 2025-03-26
- Uses `parameters` for tool parameters
- Uses `parameters` for tool call parameters
- Supports async tool calls via `tools/call-async`, `tools/result`, and `tools/cancel`
- Supports resources via `resources/list` and `resources/get` 