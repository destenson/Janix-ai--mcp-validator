# MCP Protocol Validator

A testing suite and reference implementation for the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol).

## Summary

The MCP Protocol Validator provides a comprehensive environment for testing and validating MCP server implementations. It includes reference implementations and a testing framework to ensure compliance with the MCP specification.

**Latest Protocol Support**: The validator now supports MCP protocol version **2025-06-18**, which includes major enhancements like structured tool output, OAuth 2.1 authentication, elicitation support, removal of JSON-RPC batching, and enhanced security features.

## 🔐 OAuth 2.1 Authentication Support

The validator includes comprehensive OAuth 2.1 authentication support for the 2025-06-18 protocol version, providing a complete framework for secure MCP implementations.

### Authentication Features

- **OAuth 2.1 Compliance**: Full RFC 6749, RFC 6750, and OAuth 2.1 draft compliance
- **Bearer Token Support**: Proper Bearer token extraction and validation
- **WWW-Authenticate Headers**: Standards-compliant 401 responses with authentication challenges
- **Resource Server Capabilities**: Complete OAuth 2.1 resource server implementation
- **MCP-Protocol-Version Headers**: Protocol version negotiation via HTTP headers
- **Security Headers**: CORS, Origin validation, and DNS rebinding attack prevention

### OAuth 2.1 Configuration

The reference HTTP server supports OAuth 2.1 authentication through environment variables:

```bash
# Enable OAuth 2.1 authentication
export MCP_OAUTH_ENABLED=true
export MCP_OAUTH_INTROSPECTION_URL=https://auth.example.com/oauth/introspect
export MCP_OAUTH_REQUIRED_SCOPES=mcp:read,mcp:write
export MCP_OAUTH_REALM=mcp-server

# Optional: Configure resource indicators (RFC 8707)
export MCP_OAUTH_RESOURCE_INDICATORS=https://api.example.com/mcp
```

### Authentication Testing

Test OAuth 2.1 compliance with the built-in authentication test suite:

```bash
# Test OAuth 2.1 features (framework validation)
python mcp_testing/scripts/http_compliance_test.py --debug

# Test with authentication enabled
MCP_OAUTH_ENABLED=true python ref_http_server/reference_mcp_server.py --port 8088 &
python mcp_testing/scripts/http_compliance_test.py --server-url http://localhost:8088

# Test Bearer token handling
curl -H "Authorization: Bearer your-token-here" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"client_info":{"name":"Test"},"client_capabilities":{"protocol_versions":["2025-06-18"]}}}' \
     http://localhost:8088/messages
```

## 🚀 2025-06-18 Protocol Features

### Core Enhancements

- **Structured Tool Output**: Tools return structured responses with `content`, `isError`, and `structuredContent` fields
- **Enhanced Tool Schema**: Tools use `inputSchema` (renamed from `parameters`), `title`, and `outputSchema` fields
- **JSON-RPC Batching Removal**: Batch requests are properly rejected for 2025-06-18 protocol
- **Elicitation Support**: Framework for user interaction and data collection
- **Protocol Version Headers**: HTTP requests include `MCP-Protocol-Version` header

### Security Improvements

- **OAuth 2.1 Authentication**: Complete authentication framework
- **Enhanced Error Handling**: Improved error responses with security considerations
- **Origin Validation**: DNS rebinding attack prevention
- **Session Security**: Secure session management with per-session protocol versions

## STDIO Compliance Testing

The validator includes a comprehensive testing suite for STDIO-based MCP servers.

### Running STDIO Tests

```bash
# Run compliance tests for the STDIO server (latest protocol)
python -m mcp_testing.scripts.compliance_report --server-command "python ref_stdio_server/stdio_server_2025_03_26.py" --protocol-version 2025-06-18

# Run with previous protocol versions
python -m mcp_testing.scripts.compliance_report --server-command "python ref_stdio_server/stdio_server_2025_03_26.py" --protocol-version 2025-03-26
```

### STDIO Test Coverage

The STDIO compliance tests verify:
1. Protocol Initialization
2. Tools Functionality
   - Basic tools (echo, add)
   - Async tools (sleep) for 2025-03-26+ versions
   - Structured tool output (2025-06-18)
3. Error Handling
4. Protocol Version Negotiation
5. Advanced Features (2025-06-18)
   - Elicitation support
   - Enhanced validation
   - JSON-RPC batching restrictions

### Testing Different STDIO Server Types

The validator supports testing any STDIO-based MCP server, whether it's run directly from a command or installed via pip. Here's how to test different types of servers:

#### Direct Command Testing

For servers that run directly from a Python file or command:

```bash
# Test a local Python file (latest protocol)
python -m mcp_testing.scripts.compliance_report --server-command "python path/to/your/server.py" --protocol-version 2025-06-18

# Test with specific timeouts
python -m mcp_testing.scripts.compliance_report --server-command "python path/to/server.py" --protocol-version 2025-06-18 --test-timeout 30 --tools-timeout 15

# Focus on tools testing with dynamic discovery
python -m mcp_testing.scripts.compliance_report --server-command "python path/to/server.py" --protocol-version 2025-06-18 --test-mode tools --dynamic-only

# Test with previous protocol versions for compatibility
python -m mcp_testing.scripts.compliance_report --server-command "python path/to/server.py" --protocol-version 2025-03-26
```

#### Testing Pip-Installed Servers

For servers installed via pip (like `mcp-server-fetch`):

```bash
# Ensure you're in the correct virtual environment
source .venv/bin/activate

# Install the server and dependencies
pip install your-mcp-server  # Replace with actual package name

# Run compliance tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m your_server_module" --protocol-version 2024-11-05

# Run tools-only tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m your_server_module" --protocol-version 2024-11-05 --test-mode tools

# example brave search server
BRAVE_API_KEY=api-key python -m mcp_testing.scripts.compliance_report --server-command "npx -y @modelcontextprotocol/server-brave-search" --protocol-version 2024-11-05 
```

#### Test Configuration Options

Common options for both types:

- `--test-mode tools`: Focus on testing tool functionality
- `--dynamic-only`: Automatically discover and test available tools
- `--test-timeout 30`: Set timeout for regular tests (seconds)
- `--tools-timeout 15`: Set timeout for tool-specific tests (seconds)
- `--required-tools tool1,tool2`: Specify required tools to test
- `--skip-tests test1,test2`: Skip specific tests
- `--skip-async`: Skip async tool testing

Note: Tool-related tests that timeout are treated as non-critical, allowing testing to continue.

### Test Reports

Each test run generates a detailed report containing:
- Server information (command, protocol version)
- Test execution timestamp
- Test duration
- Success rate
- Detailed results for each test case
- Server capabilities
- Session information


### Running Tests

You can run different types of tests using module-style commands:

```bash
# Basic interaction test (latest protocol)
python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2025-06-18

# Compliance tests with tools-only mode
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2025-06-18 --test-mode tools

# Set custom timeouts for tools tests vs. other tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2025-06-18 --test-timeout 30 --tools-timeout 15

# Test only specific functionality
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --protocol-version 2025-06-18 --test-mode tools

# Skip async tests if experiencing hanging issues
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --protocol-version 2025-06-18 --skip-async

# HTTP debug output
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --debug

# Test backward compatibility with older protocols
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05
```

Note: Tool-related tests that timeout are treated as non-critical, allowing testing to continue.

## HTTP Compliance Testing

The validator includes a comprehensive compliance testing suite for HTTP-based MCP servers with full 2025-06-18 protocol support.

### Running HTTP Tests

```bash
# Start the reference HTTP server (runs on port 8088)
python ref_http_server/reference_mcp_server.py

# Run compliance tests and generate a detailed report
python -m mcp_testing.scripts.http_compliance_test --output-dir reports

# Test with OAuth 2.1 authentication enabled
MCP_OAUTH_ENABLED=true python ref_http_server/reference_mcp_server.py --port 8088 &
python -m mcp_testing.scripts.http_compliance_test --server-url http://localhost:8088 --debug
```

### HTTP Test Coverage

The HTTP compliance test suite verifies:

1. **Protocol Initialization**
   - 2025-06-18 protocol negotiation
   - Session management with protocol-specific features
   - MCP-Protocol-Version header handling

2. **Tools Functionality**
   - Structured tool output (2025-06-18)
   - Legacy tool responses (older protocols)
   - Enhanced tool schema validation

3. **Error Handling**
   - Enhanced error responses (2025-06-18)
   - OAuth 2.1 authentication errors
   - Proper HTTP status codes

4. **Batch Request Processing**
   - Batch request restrictions (2025-06-18)
   - Legacy batch support (older protocols)

5. **Session Management**
   - Per-session protocol versions
   - Session security and validation

6. **Protocol Negotiation**
   - Multi-version support (2024-11-05, 2025-03-26, 2025-06-18)
   - Intelligent version selection

7. **Authentication & Security**
   - OAuth 2.1 Bearer token validation
   - WWW-Authenticate header compliance
   - CORS and origin validation

8. **Ping Utility**
   - Connection testing and validation

### Production Deployment

For production deployments with 2025-06-18 protocol:

```bash
# Enable HTTPS (required for OAuth 2.1 in production)
export MCP_TLS_CERT_FILE=/path/to/cert.pem
export MCP_TLS_KEY_FILE=/path/to/key.pem

# Configure OAuth 2.1 authentication
export MCP_OAUTH_ENABLED=true
export MCP_OAUTH_INTROSPECTION_URL=https://auth.example.com/oauth/introspect
export MCP_OAUTH_REQUIRED_SCOPES=mcp:read,mcp:write

# Configure CORS for web clients
export MCP_CORS_ORIGINS=https://myapp.example.com,https://anotherapp.example.com

# Enable rate limiting and security features
export MCP_RATE_LIMIT_ENABLED=true
export MCP_MAX_REQUESTS_PER_MINUTE=100

# Start the server
python ref_http_server/reference_mcp_server.py --port 443 --production
```

## Testing Scripts Overview

The following scripts are available in `mcp_testing/scripts/`:

### Active and Maintained
- `http_compliance_test.py`: Primary script for HTTP server testing with 2025-06-18 support (7/7 tests passing)
- `compliance_report.py`: Primary script for STDIO server testing with 2025-06-18 support (enhanced test coverage)

### Supporting Scripts mixed working/in progress
- `basic_interaction.py`: Simple tool for testing basic server functionality
- `http_test.py`: Lower-level HTTP testing utilities with OAuth 2.1 support
- `http_compliance.py`: Core HTTP compliance testing logic
- `http_compliance_report.py`: Report generation for HTTP tests
- `run_stdio_tests.py`: Lower-level STDIO testing utilities
- `session_test.py`: Session management testing utilities

## 📋 Protocol Version Support

| Protocol Version | Status | Features |
|-----------------|--------|----------|
| 2025-06-18 | ✅ **Full Support** | Structured tool output, OAuth 2.1, elicitation, no batching |
| 2025-03-26 | ✅ **Full Support** | Async tools, enhanced capabilities, batch support |
| 2024-11-05 | ✅ **Full Support** | Basic MCP functionality, legacy compatibility |

## 🧪 Test Results Summary

Current test coverage for 2025-06-18 protocol:

```
✅ HTTP Compliance Test: 7/7 tests passed
✅ OAuth 2.1 Framework: 6/6 tests passed  
✅ Protocol Features: 7/7 tests passed
✅ Multi-Protocol Support: 3/3 versions supported
✅ Backward Compatibility: 100% maintained
✅ Security Features: Authentication, CORS, Origin validation
```

## 📚 Additional Resources

- **JSON Schema**: Complete schemas available in `schema/` directory
- **Specification Documents**: Full specification files in `specification/` directory
- **Reference Implementations**: HTTP and STDIO servers in `ref_http_server/` and `ref_stdio_server/`
- **Test Reports**: Generated reports available in `reports/` directory

## License

SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
