# Testing MCP Servers Without Shutdown Support

This document explains how to test MCP servers that don't implement the `shutdown` method, such as the Brave Search MCP server.

## Prerequisites

1. Node.js and npm installed
2. Python 3.8+ installed
3. The appropriate API key for the server you're testing

## Handling Servers Without Shutdown Support

Some MCP servers don't implement the `shutdown` method. In these cases, you need to:

1. Set the `MCP_SKIP_SHUTDOWN` environment variable to `true`
2. Use the `--skip-shutdown` flag when running the compliance tests
3. Use the `--auto-detect` flag to enable server-specific adaptations

The MCP Protocol Validator will:
- Skip shutdown-related tests
- Handle process termination gracefully
- Still generate valid compliance reports

## Running Compliance Tests for Brave Search

The Brave Search server requires an API key and does not support the shutdown method.

```bash
# Set your API key
export BRAVE_API_KEY=your_api_key_here

# Set skip shutdown flag
export MCP_SKIP_SHUTDOWN=true

# Run compliance tests with auto-detection
python -m mcp_testing.scripts.compliance_report \
  --server-command "npx -y @modelcontextprotocol/server-brave-search" \
  --output-dir "./reports" \
  --skip-shutdown \
  --auto-detect \
  --dynamic-only \
  --debug
```

The `--auto-detect` flag will:
1. Detect the server type (Brave Search)
2. Use the correct protocol version (2024-11-05)
3. Skip shutdown-related tests
4. Configure expected tools (brave_web_search, brave_local_search)

## Testing Other Servers Without Shutdown

For any MCP server that doesn't support shutdown, use this pattern:

```bash
# Set any required API keys or environment variables
export SERVER_API_KEY=your_api_key_here

# Set skip shutdown flag
export MCP_SKIP_SHUTDOWN=true

# Run compliance tests
python -m mcp_testing.scripts.compliance_report \
  --server-command "command-to-start-server" \
  --output-dir "./reports" \
  --skip-shutdown \
  --dynamic-only
```

## Example Tool Calls for Brave Search

### Using brave_web_search

```json
{
  "jsonrpc": "2.0",
  "id": "web-search-1",
  "method": "tools/call",
  "params": {
    "name": "brave_web_search",
    "arguments": {
      "query": "What is MCP protocol?",
      "count": 5
    }
  }
}
```

### Using brave_local_search

```json
{
  "jsonrpc": "2.0",
  "id": "local-search-1",
  "method": "tools/call",
  "params": {
    "name": "brave_local_search",
    "arguments": {
      "query": "coffee shops in San Francisco"
    }
  }
}
```

## Troubleshooting

1. **API Key Issues**:
   - Ensure the appropriate API key environment variable is correctly set
   - Check that your API key is valid

2. **Process Termination**:
   - Always set `MCP_SKIP_SHUTDOWN=true` for servers without shutdown support
   - With this environment variable, the validator will gracefully handle termination

3. **Server Features**:
   - The `--dynamic-only` flag ensures tests adapt to the available server features
   - This provides the most accurate compliance testing for any server 