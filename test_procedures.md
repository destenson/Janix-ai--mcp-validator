# MCP Validator Testing Procedures

Quick reference guide for testing the MCP Validator implementations.

## HTTP Server with SSE Transport

### Starting the Server

```bash
# Start with default settings (localhost:8085)
cd ref_http_server && python fastmcp_server.py

# Start with debug output
cd ref_http_server && python fastmcp_server.py --debug

# Start with custom host/port
cd ref_http_server && python fastmcp_server.py --host 0.0.0.0 --port 8080
```

### Running Tests

```bash
# Basic compliance test
python -m mcp_testing.scripts.fastmcp_compliance

# With debug output
python -m mcp_testing.scripts.fastmcp_compliance --debug

# With custom server URL
python -m mcp_testing.scripts.fastmcp_compliance --server-url http://localhost:8080/mcp

# Generate a report file
python -m mcp_testing.scripts.fastmcp_compliance --report-file reports/custom_report.md
```

## STDIO Server

### Running Tests

```bash
# Test 2024-11-05 protocol version
python -m mcp_testing.scripts.run_stdio_tests \
  --server-command "./ref_stdio_server/stdio_server_2024_11_05.py" \
  --protocol-version 2024-11-05

# Test 2025-03-26 protocol version
python -m mcp_testing.scripts.run_stdio_tests \
  --server-command "./ref_stdio_server/stdio_server_2025_03_26.py" \
  --protocol-version 2025-03-26

# With debug output
python -m mcp_testing.scripts.run_stdio_tests \
  --server-command "./ref_stdio_server/stdio_server_2025_03_26.py" \
  --protocol-version 2025-03-26 \
  --debug

# Generate detailed compliance reports
python -m mcp_testing.scripts.compliance_report \
  --server-command "./ref_stdio_server/stdio_server_2024_11_05.py" \
  --protocol-version 2024-11-05 \
  --output-dir "./reports"

python -m mcp_testing.scripts.compliance_report \
  --server-command "./ref_stdio_server/stdio_server_2025_03_26.py" \
  --protocol-version 2025-03-26 \
  --output-dir "./reports"
```

## Manual Testing with Curl

### HTTP Server

```bash
# 1. Establish SSE connection and get session ID
curl -N http://localhost:8085/notifications

# 2. Initialize (replace session_id with your actual session ID)
curl -X POST "http://localhost:8085/mcp?session_id=your-session-id" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "id": "init-1", "params": {"protocol_version": "2025-03-26", "client_info": {"name": "curl-test"}}}'

# 3. Call a tool
curl -X POST "http://localhost:8085/mcp?session_id=your-session-id" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "id": "tool-1", "params": {"name": "echo", "arguments": {"message": "Hello World!"}}}'
```

## Notes

- Always ensure the server is running before running tests
- Check the generated reports in the `reports/` directory
- Debug mode provides detailed output for troubleshooting
- HTTP server requires both `/mcp` and `/notifications` endpoints to be accessible 