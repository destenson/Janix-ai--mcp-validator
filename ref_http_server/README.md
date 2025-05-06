# Reference HTTP MCP Server (v2)

This directory contains a reference implementation of the MCP (Model Conversation Protocol) server that uses HTTP as its transport layer. This implementation supports both the 2024-11-05 and 2025-03-26 protocol versions.

## Features

- JSON-RPC 2.0 over HTTP implementation
- Support for both MCP protocol versions (2024-11-05 and 2025-03-26)
- Basic tools: echo, add, sleep
- Support for synchronous and asynchronous tool calls
- Support for resources (2025-03-26 only)
- Error handling and validation
- CORS support for browser clients
- Batch request support
- **Session management** via the `Mcp-Session-Id` header

## Files

- `server.py`: The main HTTP server implementation
- `protocol_handler.py`: Protocol version-specific handlers
- `session_manager.py`: Session management implementation
- `base_transport.py`: Transport layer abstractions
- `test_client.py`: Test client implementation
- `run_server_v2.py`: Server launcher script
- `run_test_client_v2.py`: Test client launcher script

## Running the Server

To start the server:

```bash
# Start with auto port selection (recommended)
python run_server_v2.py --debug --auto-port

# Start with specific port
python run_server_v2.py --port 9000 --debug

# Start with custom host
python run_server_v2.py --host 0.0.0.0 --port 9000 --debug

# Start in test mode (ignores shutdown requests)
python run_server_v2.py --debug --auto-port --no-shutdown
```

## Testing the Server

You can test the server using the included test client:

```bash
# Test with specific URL
python run_test_client_v2.py --url http://localhost:9000/mcp --debug

# Test with specific protocol version
python run_test_client_v2.py --url http://localhost:9000/mcp --protocol-version 2024-11-05 --debug
```

The test client will:
- Initialize a session
- Test server info
- List available tools
- Test synchronous tool calls (echo, add, sleep)
- Test asynchronous tool calls
- Test cancellation
- Clean up the session

## Manual Testing with curl

You can also test the server manually using curl. **Important**: You must capture and include the session ID in all requests after initialization:

```bash
# Initialize the server and capture the session ID
SESSION_ID=$(curl -s -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "curl", "version": "1.0.0"}, "capabilities": {"tools": true}}, "id": 1}' \
  -i | grep -i "Mcp-Session-Id" | cut -d ' ' -f 2 | tr -d '\r')

echo "Session ID: $SESSION_ID"

# Get server info
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc": "2.0", "method": "server/info", "id": 2}'

# List available tools
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 3}'

# Call the echo tool
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "echo", "parameters": {"message": "Hello, MCP!"}}, "id": 4}'
```

## Protocol Notes

### Version 2024-11-05
- Uses `arguments` for tool call parameters 
- Uses `mcp/tools` instead of `tools/list`
- Uses `mcp/tools/call` instead of `tools/call`

### Version 2025-03-26
- Uses `parameters` for tool call parameters
- Supports async tool calls via `tools/call-async`, `tools/result`, and `tools/cancel`
- Supports resources via `resources/list` and `resources/get` 

## License

AGPL-3.0-or-later

This server is provided as a reference implementation for educational purposes.