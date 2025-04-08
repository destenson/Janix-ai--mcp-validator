# MCP Protocol Validator Test Notes

## Testing Brave Search Server

To test the Brave Search MCP server for compliance, use this command:

```bash
BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM" python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 --debug
```

This command:
1. Sets the required Brave API key as an environment variable
2. Runs the compliance report tool against the Brave Search server
3. Tests against protocol version 2024-11-05 (as recommended for this server)
4. Enables debug output for more detailed information

### Server Configuration Details

The Brave Search server has the following configuration in the testing framework:

- **Package**: `@modelcontextprotocol/server-brave-search`
- **Required Tools**: `brave_web_search`, `brave_local_search`
- **Recommended Protocol**: 2024-11-05
- **Skipped Tests**: `test_shutdown`, `test_exit_after_shutdown`

The server requires a Brave API key to function properly.

### Compliance Status

Running the full compliance test on the Brave Search server yields the following results:

- **Total Tests**: 33
- **Passed**: 23 (69.7%)
- **Failed**: 10 (30.3%)
- **Status**: ❌ Non-Compliant (69.7%)

Key issues found:
- Server does not properly reject calls to non-existent tools
- Does not support the `server/info` method
- Limited support for batch requests
- Issues with schema validation for tool parameters
- Problems with cancellation handling

### Running Specific Test Modes

For more focused testing, you can use the `--test-mode` parameter:

```bash
# Test only the core functionality (init, basic protocol)
BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM" python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 --test-mode core

# Test only tools functionality
BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM" python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 --test-mode tools

# Test only async functionality
BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM" python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 --test-mode async

# Test only specification requirements
BRAVE_API_KEY="BSA0cS6GWjZtWdb7D34r1Z8PYs-FoVM" python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 --test-mode spec
```

Available test modes:
- `all`: Run all tests (default)
- `core`: Test basic protocol functionality (initialization, etc.)
- `tools`: Test tools functionality
- `async`: Test asynchronous tool functionality
- `spec`: Test specification compliance requirements

## Testing Minimal MCP Server (STDIO)

The repository includes a reference implementation of an MCP server that uses STDIO for transport.

To test it for compliance:

```bash
# Test with protocol version 2025-03-26 (latest)
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26

# Basic test script included with the server
cd minimal_mcp_server && python test_minimal_server.py --protocol-version 2025-03-26 --full
```

The minimal server implements these tools:
- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (for testing async operations)
- `list_directory`: List files in a directory
- `read_file`: Read a file
- `write_file`: Write a file

### Compliance Status

The Minimal MCP Server achieves 100% compliance with the 2025-03-26 protocol specification:
- **Total Tests**: 37
- **Passed**: 37 (100%)
- **Status**: ✅ Fully Compliant (100%)

## Testing Minimal HTTP MCP Server

The repository also includes a reference implementation of an MCP server that uses HTTP transport.

To start the HTTP server:

```bash
# Start with default settings (localhost:8000)
python ./minimal_http_server/minimal_http_server.py
```

To test it for compliance:

```bash
# Run HTTP compliance tests
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Generate a compliance report
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir ./reports
``` 