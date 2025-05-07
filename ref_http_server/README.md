# FastMCP HTTP Server with SSE Transport

This is a reference implementation of an MCP server using HTTP with Server-Sent Events (SSE) transport. It implements the 2025-03-26 protocol version.

## Features

- HTTP transport with JSON-RPC
- Server-Sent Events (SSE) for asynchronous responses
- Session management with both header and query parameter support
- Full CORS support
- Asynchronous tool execution

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- Required Python packages (install with `pip install -r requirements.txt`)

## Running the Server

```bash
# From the project root
python ref_http_server/fastmcp_server.py --debug
```

Server options:
- `--host` - Host to bind to (default: localhost)
- `--port` - Port to listen on (default: 8085)
- `--debug` - Enable debug logging

Once running, the server will be available at:
- HTTP endpoint: http://localhost:8085/mcp
- SSE endpoint: http://localhost:8085/notifications

## Testing the Server

### Using the Custom Python Test Script

The most reliable way to test the server is using our custom Python test script:

```bash
# From the project root
python custom_http_test.py --debug
```

This script will:
1. Connect to the SSE endpoint to establish a session
2. Test the initialize method
3. Test the echo tool
4. Test the add tool
5. Test the async sleep tool

### Using the Bash Test Script

For a simple bash-based test:

```bash
# From the project root
./test_fastmcp.sh
```

## Client Implementation Notes

To implement a client for this server:

1. **Establish a Session**
   - Connect to the SSE endpoint (`/notifications`)
   - Extract the session ID from the first message (`Connected to session <id>`)

2. **Make Requests**
   - Send JSON-RPC requests to the `/mcp` endpoint
   - Include the session ID as either:
     - A query parameter: `?session_id=<id>`
     - A header: `Mcp-Session-Id: <id>`
   - All requests will return `202 Accepted` immediately

3. **Handle Responses**
   - Listen for events on the SSE connection
   - Parse JSON responses and match them to requests using the `id` field

## Available Tools

The server provides these built-in tools:

1. **echo**
   - Echoes back a message
   - Parameters: `{"message": "string"}`

2. **add**
   - Adds two numbers
   - Parameters: `{"a": number, "b": number}`

3. **sleep**
   - Sleeps for the specified duration (async)
   - Parameters: `{"seconds": number}`

## Protocol Compliance

This server is fully compliant with the MCP 2025-03-26 specification. See the compliance report in `reports/fastmcp_http_compliance_report.md` for details. 