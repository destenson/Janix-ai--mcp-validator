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

## OLD CONTENT

The following sections contain historical information about various implementations and may not reflect the current state of the project.

### Reference Implementations

#### STDIO Reference Implementations

Two reference implementations using STDIO for transport:

##### 2024-11-05 Protocol Version
```bash
python ./ref_stdio_server/stdio_server_2024_11_05.py
```

##### 2025-03-26 Protocol Version
```bash
python ./ref_stdio_server/stdio_server_2025_03_26.py
```

#### Minimal HTTP MCP Server

```bash
python ./minimal_http_server/minimal_http_server.py
python ./minimal_http_server/minimal_http_server.py --host 0.0.0.0 --port 8080
python ./minimal_http_server/test_http_server.py
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26
```

See the [HTTP Server README](minimal_http_server/README.md) for more details.

#### FastMCP HTTP Server with SSE Transport

```bash
python ./ref_http_server/fastmcp_server.py --debug
./test_improved_fastmcp.sh
```

##### Key Features
- SSE Transport
- Connection Management
- Session Management
- HTTP Integration

### MCP Testing Framework

#### For STDIO Servers:

```bash
python -m mcp_testing.scripts.basic_interaction --server-command "./minimal_mcp_server/minimal_mcp_server.py"
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26
```

#### For HTTP Servers:

```bash
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
```

#### For HTTP with SSE Servers:

```bash
./test_improved_fastmcp.sh
```

### Testing Pip-Installed MCP Servers

```bash
source .venv/bin/activate
pip install mcp-server-fetch sseclient-py==1.7.2

python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-mode tools
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-timeout 30 --tools-timeout 15
```

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
