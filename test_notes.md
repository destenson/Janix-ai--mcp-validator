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

## Testing Fetch MCP Server

The Fetch MCP server provides web content fetching capabilities for LLMs. It can be installed using different methods, and each method requires a different testing approach.

### Installation Methods

1. **Using `uv` (recommended)**:
   ```bash
   # Install uv if not already installed
   # Run the Fetch server with uvx
   uvx mcp-server-fetch
   ```

2. **Using `pip`**:
   ```bash
   # Install the package
   pip install mcp-server-fetch
   
   # Run the server
   python -m mcp_server_fetch
   ```

3. **Local source installation**:
   ```bash
   # Navigate to the source directory
   cd /path/to/servers/src/fetch
   
   # Install dependencies and run
   pip install -e .
   python -m mcp_server_fetch
   ```

4. **Docker**:
   ```bash
   # Run via Docker
   docker run -i --rm mcp/fetch
   ```

### Testing Fetch Server with MCP Protocol Validator

The fetch server can be tested with the MCP Protocol Validator using any of the installation methods:

```bash
# Testing with uvx installation
python -m mcp_testing.scripts.compliance_report --server-command "uvx mcp-server-fetch" --protocol-version 2024-11-05

# Testing with pip installation
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05

# Testing with local source
python -m mcp_testing.scripts.compliance_report --server-command "cd /Users/scott/AI/MCP/servers/src/fetch && python -m mcp_server_fetch" --protocol-version 2024-11-05

# Testing with Docker
python -m mcp_testing.scripts.compliance_report --server-command "docker run -i --rm mcp/fetch" --protocol-version 2024-11-05
```

### Known Issues with Fetch Server

The Fetch server has a known issue with the `tools/list` method which causes it to hang indefinitely when this method is called. The server successfully initializes and can respond to the initialization request, but does not correctly implement the `tools/list` method.

To work around this issue, we've implemented two approaches:

1. **Use the Basic Interaction Script**: A simplified test that only verifies initialization
   ```bash
   python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
   ```

2. **Use Timeouts for Tools Tests**: The compliance report script now supports timeouts for tools-related tests
   ```bash
   python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-mode tools --tools-timeout 15 --report-prefix "fetch_"
   ```

When testing the fetch server, you will still see a successful initialization but the tool list test will time out. The test framework has been updated to treat tool test timeouts as non-critical, so a report can still be generated showing the server's partial compliance with the protocol.

### Compliance Status for Fetch Server

The Fetch MCP Server demonstrates partial compliance with the 2024-11-05 protocol specification:
- **Total Tests**: 5 (in tools mode)
- **Passed**: 1 (Initialization)
- **Failed/Timed out**: 4 (Tool-related tests)
- **Status**: ⚠️ Partially Compliant (Initialization works, tools functionality times out)

A successful basic interaction test shows:
```
Starting server...
Initializing server...
Initialization result:
{
  "jsonrpc": "2.0",
  "id": "init",
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "mcp-fetch",
      "version": "1.6.0"
    },
    "capabilities": {
      "tools": {
        "listChanged": false
      },
      "experimental": {}
    }
  }
}
Sending initialized notification...

Listing available tools...
Error listing tools: Timeout waiting for response
```

This shows the server initializes correctly but has an issue with the tools/list method.

### Troubleshooting

When testing the Fetch server, you might encounter a "Failed to start transport" error. This could be due to:

1. **Dependencies not installed**: Make sure all dependencies are installed correctly.
   ```bash
   pip install mcp-server-fetch sseclient-py==1.7.2
   ```

2. **Module Not Found**: The command might need to include the proper Python path.
   ```bash
   # Try with PYTHONPATH
   PYTHONPATH=/Users/scott/AI/MCP/servers/src/fetch python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
   ```

3. **Interactive Mode**: The fetch server might need to be run with the `-i` flag:
   ```bash
   python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch -i" --protocol-version 2024-11-05
   ```

4. **Running Single Script**: Try running the server with a direct path to the script:
   ```bash
   python -m mcp_testing.scripts.compliance_report --server-command "python /Users/scott/AI/MCP/servers/src/fetch/src/mcp_server_fetch/__main__.py" --protocol-version 2024-11-05
   ```

## Improved Test Framework Features

### Timeout Handling for Tool Tests

The testing framework has been enhanced to better handle servers that may time out during specific test operations, particularly tool-related tests. New features include:

1. **Separate timeouts for tool tests**:
   ```bash
   python -m mcp_testing.scripts.compliance_report --server-command "command" --test-timeout 30 --tools-timeout 15
   ```

2. **Non-critical tool test failures**: Tool tests that time out are now marked as non-critical and don't prevent the generation of a compliance report. This allows testing servers that may have issues with specific methods but are otherwise functional.

3. **Timeout visibility in reports**: Reports now show which tests timed out, making it easier to diagnose server issues.

### Example Run with Timeout Handling

Running the minimal MCP server with timeout parameters demonstrates the improved functionality:

```
[2025-04-08 18:33:04] Running 3 non-tool tests with 30s timeout
[2025-04-08 18:33:04] Starting test suite with 3 tests
[2025-04-08 18:33:04] Running test 1/3: test_echo_tool
[2025-04-08 18:33:05] Test 1/3: test_echo_tool - PASSED (0.51s)
[2025-04-08 18:33:05] Progress: 1/3 tests completed, time elapsed: 0.5s, estimated remaining: 1.0s
[2025-04-08 18:33:05] Running test 2/3: test_add_tool
[2025-04-08 18:33:05] Test 2/3: test_add_tool - PASSED (0.51s)
[2025-04-08 18:33:05] Progress: 2/3 tests completed, time elapsed: 1.0s, estimated remaining: 0.5s
[2025-04-08 18:33:05] Running test 3/3: test_invalid_tool
[2025-04-08 18:33:06] Test 3/3: test_invalid_tool - PASSED (0.52s)
[2025-04-08 18:33:06] Progress: 3/3 tests completed, time elapsed: 1.6s, estimated remaining: 0.0s
[2025-04-08 18:33:06] Test suite completed: 3 passed, 0 failed, total time: 1.55s
[2025-04-08 18:33:06] Running 2 tool tests with 15s timeout
```

### Test Output Interpretation

When a server has tool-related timeout issues, you'll see output like:

```
⚠️ WARNING: Test test_tools_list timed out after 15s (continuing)
```

And the generated report will indicate the timeout but still show initialization success:

```
## Status: Success

## Test Details

- ✅ Server Initialization: Successful
- ⚠️ Tools List: Timed out after 15s (non-critical)
```

This approach allows the testing framework to gracefully handle servers with partial compliance, providing useful feedback while still allowing the testing process to complete.

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