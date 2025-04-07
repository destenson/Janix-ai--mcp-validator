# MCP Protocol Validator

A testing suite and reference implementation for the [Model Conversation Protocol (MCP)](https://github.com/microsoft/aimcp).

## Components

This repository contains:

1. **Minimal MCP Server**: A reference implementation of an MCP server
2. **MCP Testing Framework**: A robust testing framework for verifying MCP server implementations against the protocol specifications

## Status

The current implementation is fully compliant with the latest MCP protocol specification (2025-03-26).

✅ All tests pass for the reference implementation!

## Minimal MCP Server

A simple reference implementation of an MCP server that supports all protocol features:

- Basic protocol operations (initialization, shutdown)
- Synchronous tool calls
- Asynchronous tool calls (for 2025-03-26)
- Utility tools for file system operations

### Running the Server

```bash
# Run the server
python ./minimal_mcp_server/minimal_mcp_server.py
```

### Supported Tools

The minimal server implements these tools:

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (useful for testing async operations)
- `list_directory`: List files in a directory
- `read_file`: Read a file
- `write_file`: Write a file

## MCP Testing Framework

A flexible testing framework for verifying MCP server compliance with protocol specifications.

### Key Features

- Support for both the 2024-11-05 and 2025-03-26 protocol versions
- Dynamic tool testing that adapts to any server's capabilities
- Detailed compliance reporting
- Configurable test modes for targeted functionality testing

### Running Compliance Tests

```bash
# Test the minimal server against the 2025-03-26 specification
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26

# Test a server with dynamic adaptation to its capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only --protocol-version 2025-03-26

# Test a specialized server that doesn't implement standard tools or shutdown method
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/specialized/server" --args "/path/to/directory" --skip-shutdown --dynamic-only --protocol-version 2024-11-05
```

### Generating Compliance Reports

The framework generates detailed Markdown reports:

```bash
# Generate a compliance report
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"
```

## Extensions and Customization

The framework is designed to be extended:

- Add new test cases for additional protocol features
- Support new protocol versions as they are released
- Create custom test adaptations for specialized server implementations

See the [MCP Testing README](mcp_testing/README.md) for detailed information.

## License

MIT License 