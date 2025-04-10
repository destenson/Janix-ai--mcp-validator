# MCP Protocol Validator v0.1.0

## Initial Release

This is the initial public release of the MCP Protocol Validator, a testing framework and reference implementation for the [Model Conversation Protocol (MCP)](https://github.com/microsoft/aimcp).

### Features

- **Protocol Support:** Test MCP servers implementing the 2024-11-05 and 2025-03-26 protocol versions
- **Transport Support:** Test servers using both STDIO and HTTP transports
- **Comprehensive Testing:** Validate server implementations against the protocol specification
- **Reference Implementations:** Includes minimal reference servers for both STDIO and HTTP
- **Detailed Reporting:** Generate comprehensive compliance reports
- **Server Adaptability:** Dynamically adapts to server capabilities
- **Timeout Handling:** Gracefully handles servers that may timeout on certain operations
- **PyPI Package:** Installable via pip for easy integration

### Minimal Reference Servers

The package includes two reference implementations:

1. **STDIO Server:** A minimal MCP-compliant server using standard input/output for transport
2. **HTTP Server:** A fully-featured MCP server that supports both protocol versions over HTTP

### Component Organization

- `mcp_testing/`: Testing framework for validating protocol compliance
- `minimal_mcp_server/`: Reference implementation using STDIO transport
- `minimal_http_server/`: Reference implementation using HTTP transport
- `schema/`: JSON Schema definitions for the MCP protocol
- `specification/`: Protocol specifications and documentation

### Getting Started

Install from source:

```bash
git clone https://github.com/your-username/mcp-protocol-validator.git
cd mcp-protocol-validator
pip install -e .
```

Run basic tests:

```bash
python -m mcp_testing.scripts.basic_interaction --server-command "./minimal_mcp_server/minimal_mcp_server.py"
```

Generate a compliance report:

```bash
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"
```

### Known Issues

- Some servers may timeout when requesting tool lists. Use the `--tools-timeout` parameter to handle these cases.
- See SERVER_COMPATIBILITY.md for details on specific server compatibility. 