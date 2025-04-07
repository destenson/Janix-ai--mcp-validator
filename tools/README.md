# MCP Protocol Testing Tools

This directory contains various tools for testing and debugging MCP (Model Control Protocol) server implementations.

## Available Tools

### 1. debug_server.py

A simple debugging tool that tests basic interactions with a minimal MCP STDIO server.

Usage:
```bash
./debug_server.py
```

Features:
- Tests initialization sequence
- Tests basic method calls (initialize, tools/list)
- Tests proper shutdown sequence
- Displays full server responses and logs

### 2. debug_complete_test.py

A comprehensive testing tool that validates all core functionality of the minimal MCP STDIO server.

Usage:
```bash
./debug_complete_test.py
```

Features:
- Comprehensive testing of initialization
- Tools listing and calling
- Batch request handling
- Resource management
- Detailed response validation
- Error handling verification

### 3. validate_minimal_server.py

A wrapper for the MCP Protocol Validator that makes it easy to run validation tests against our minimal server.

Usage:
```bash
./validate_minimal_server.py [--protocol-version VERSION] [--test TYPE]
```

Options:
- `--protocol-version`: Protocol version to test (`2024-11-05` or `2025-03-26`, default: `2024-11-05`)
- `--test`: Test type to run (`basic`, `tools`, `resources`, `batch`, or `all`, default: `basic`)

Examples:
```bash
# Run basic initialization test with protocol version 2024-11-05
./validate_minimal_server.py

# Run all tests with protocol version 2025-03-26
./validate_minimal_server.py --protocol-version 2025-03-26 --test all
```

## Using These Tools

These tools are designed to work with the minimal MCP STDIO server implementation in the `minimal_mcp_stdio_server` directory. They help validate that the server correctly implements the MCP protocol specification and provide debugging information when issues arise.

The tools are particularly useful for:
1. Verifying protocol compliance
2. Debugging server behavior
3. Understanding the MCP protocol flow
4. Testing new server features

For more comprehensive validation, use the main validator script in the root directory:
```bash
../run_validator.py --transport stdio --server-command "../minimal_mcp_stdio_server/minimal_mcp_stdio_server.py" --protocol-version 2024-11-05
``` 