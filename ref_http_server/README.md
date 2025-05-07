# FastMCP HTTP Server with SSE Transport

A fully compliant MCP server implementation that uses HTTP with Server-Sent Events (SSE) for asynchronous communication.

## Overview

This server provides a robust, efficient implementation of the MCP 2025-03-26 protocol specification using HTTP with SSE transport. It demonstrates how to implement the MCP protocol using modern HTTP streaming capabilities as an alternative to WebSockets.

## Features

- **HTTP-based Transport**: Uses standard HTTP for all communication
- **Server-Sent Events**: Leverages SSE for efficient server-to-client streaming
- **Asynchronous Tool Execution**: Fully supports asynchronous tool calls
- **Robust Connection Management**: Implements keepalives and connection recovery
- **Advanced Session Handling**: Includes session tracking and stale session cleanup
- **Standard Compliance**: Fully compliant with MCP 2025-03-26 specification

## Architecture

The FastMCP server follows a modern HTTP architecture:

1. **Endpoint Structure**:
   - `/mcp`: Main endpoint for JSON-RPC requests
   - `/notifications`: SSE endpoint for asynchronous responses

2. **Communication Flow**:
   - Client establishes an SSE connection to `/notifications`
   - Client sends JSON-RPC requests to `/mcp`
   - Server responds to requests with HTTP 202 Accepted
   - Server sends actual results via the SSE connection

3. **Session Management**:
   - Session IDs are generated upon first SSE connection
   - Sessions track initialization status and last activity time
   - Multiple connections per session are supported
   - Stale sessions are automatically cleaned up

## Built-in Tools

The server comes with three built-in tools for testing and demonstration:

1. **Echo**: Simple tool that echoes back text
   ```json
   {"jsonrpc": "2.0", "method": "echo", "id": "1", "params": {"message": "Hello World!"}}
   ```

2. **Add**: Adds two numbers
   ```json
   {"jsonrpc": "2.0", "method": "add", "id": "2", "params": {"a": 42, "b": 27}}
   ```

3. **Sleep**: Asynchronous tool that sleeps for specified duration
   ```json
   {"jsonrpc": "2.0", "method": "sleep", "id": "3", "params": {"seconds": 2.5}}
   ```

## Key Improvements

The FastMCP server includes several improvements for robustness:

1. **Keepalive Mechanism**: 
   - Sends keepalive messages every 30 seconds
   - Prevents connection timeouts from proxies or browsers

2. **Standardized Session ID Format**:
   - Uses the standard `Connected to session <id>` format
   - Compatible with standard MCP clients

3. **Comprehensive Error Handling**:
   - Detailed error messages with JSON-RPC error codes
   - Connection failure detection and reporting
   - Request validation with informative errors

4. **Session Lifecycle Management**:
   - Tracks session creation and last activity times
   - Cleans up sessions inactive for 30+ minutes
   - Supports reconnection to existing sessions

## Usage

### Running the Server

```bash
# Basic usage (localhost:8085)
python fastmcp_server.py

# With debug logging
python fastmcp_server.py --debug

# Custom host and port
python fastmcp_server.py --host 0.0.0.0 --port 8080
```

### Testing with Curl

1. Establish an SSE connection:
```bash
curl -N http://localhost:8085/notifications
```

This returns a session ID:
```
data: Connected to session d8a41c6f-e89a-4a32-b6c5-7dcd9f3abcde
```

2. Send a request:
```bash
curl -X POST http://localhost:8085/mcp?session_id=d8a41c6f-e89a-4a32-b6c5-7dcd9f3abcde \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "id": "init-1", "params": {"protocol_version": "2025-03-26", "client_info": {"name": "curl-test"}}}'
```

3. Watch the SSE connection for the response:
```
data: {"jsonrpc": "2.0", "id": "init-1", "result": {"capabilities": {"tools": true, "async": true}, "server_info": {"name": "FastMCP HTTP Server", "version": "1.0.0"}}}
```

### Automated Testing

Use the provided test script to run a comprehensive test suite:

```bash
# Run automated tests
../test_improved_fastmcp.sh

# View the generated report
cat ../reports/improved_fastmcp_compliance_report.md
```

## Implementation Notes

### SSE vs WebSockets

This implementation demonstrates the advantages of SSE over WebSockets for certain MCP use cases:

- **Simplicity**: SSE is simpler to implement than WebSockets
- **HTTP Native**: Works with standard HTTP infrastructure
- **Firewall Friendly**: Uses standard HTTP ports and connections
- **Auto-Reconnect**: Browsers automatically reconnect SSE connections
- **One-Way**: Efficient for server-to-client streaming (most MCP traffic)

### Performance Considerations

The FastMCP server is designed for reliability and simplicity, with several performance optimizations:

- **Connection Pooling**: Supports multiple clients per session
- **Efficient Message Delivery**: Uses asyncio queues for message passing
- **Minimal Dependencies**: Built on standard Python libraries with FastAPI

## Extending the Server

To add new tools to the server:

1. Define a tool handler function:
```python
def my_tool_handler(params):
    # Process params and return result
    return {"processed": params}
```

2. Register the tool with appropriate metadata:
```python
register_tool(
    "my_tool",
    "Description of what my tool does",
    {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param1"]
    },
    my_tool_handler
)
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**:
   - Problem: SSE connection closes unexpectedly
   - Solution: Ensure no proxy is timing out idle connections

2. **CORS Issues**:
   - Problem: Browser clients can't connect due to CORS
   - Solution: Configure CORS in the middleware with appropriate origins

3. **Session Handling**:
   - Problem: Session ID not being recognized
   - Solution: Ensure session ID is passed in all requests (via query param or header) 