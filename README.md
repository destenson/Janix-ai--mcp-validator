# MCP Protocol Validator

A testing suite and reference implementation for the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol).

## Summary

The MCP Protocol Validator provides a comprehensive environment for testing and validating MCP server implementations. It includes reference implementations and a testing framework to ensure compliance with the MCP specification.

## HTTP Compliance Testing

The validator includes a comprehensive compliance testing suite for HTTP-based MCP servers.

### Running HTTP Tests

```bash
# Start the reference HTTP server (runs on port 8088)
python ref_http_server/reference_mcp_server.py

# Run compliance tests and generate a detailed report
python -m mcp_testing.scripts.http_compliance_test --output-dir reports
```

### HTTP Test Coverage

The HTTP compliance test suite verifies:

1. Protocol Initialization
2. Tools Functionality
   - Echo command
   - Add operation
   - Sleep function (async capabilities)
3. Error Handling
4. Batch Request Processing
5. Session Management
6. Protocol Negotiation
7. Ping Utility

## STDIO Compliance Testing

The validator includes a comprehensive testing suite for STDIO-based MCP servers.

### Running STDIO Tests

```bash
# Run compliance tests for the STDIO server
python -m mcp_testing.scripts.compliance_report --server-command "python ref_stdio_server/stdio_server_2025_03_26.py" --protocol-version 2025-03-26
```

### STDIO Test Coverage

The STDIO compliance tests verify:
1. Protocol Initialization
2. Tools Functionality
   - Basic tools (echo, add)
   - Async tools (sleep) for 2025-03-26 version
3. Error Handling
4. Protocol Version Negotiation

### Test Reports

Each test run generates a detailed report containing:
- Server information (command, protocol version)
- Test execution timestamp
- Test duration
- Success rate
- Detailed results for each test case
- Server capabilities
- Session information

## Testing Scripts Overview

The following scripts are available in `mcp_testing/scripts/`:

### Active and Maintained
- `http_compliance_test.py`: Primary script for HTTP server testing (7/7 tests passing)
- `compliance_report.py`: Primary script for STDIO server testing (36/37 tests passing)

### Supporting Scripts mixed working/in progress
- `basic_interaction.py`: Simple tool for testing basic server functionality
- `http_test.py`: Lower-level HTTP testing utilities
- `http_compliance.py`: Core HTTP compliance testing logic
- `http_compliance_report.py`: Report generation for HTTP tests
- `run_stdio_tests.py`: Lower-level STDIO testing utilities
- `session_test.py`: Session management testing utilities

```

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
