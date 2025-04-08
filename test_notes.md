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

### Troubleshooting

When testing the Fetch server, you might encounter a "Failed to start transport" error. This could be due to:

1. **Dependencies not installed**: Make sure all dependencies are installed correctly.
   ```bash
   cd /Users/scott/AI/MCP/servers/src/fetch
   pip install -e .
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

### Server Configuration Details

The Fetch server has the following configuration in the testing framework:

- **Package**: `mcp-server-fetch`
- **Required Tools**: `fetch`
- **Recommended Protocol**: 2024-11-05
- **Skipped Tests**: `test_shutdown`, `test_exit_after_shutdown`, `test_initialization_order`

The fetch server provides a single tool to fetch content from web URLs and convert them to a format suitable for consumption by an LLM.

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