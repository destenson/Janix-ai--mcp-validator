# MCP HTTP Server Testing Module

This module provides comprehensive testing capabilities for MCP HTTP server implementations, focusing on **strict compliance with the official MCP specification**.

## Testing Philosophy

This test suite follows the principle of testing **only what is explicitly specified** in the official MCP specification at https://modelcontextprotocol.io. We do not test implementation details or "best practices" that are not mandated by the specification.

## Features

- **Specification-Only Testing**: Tests only behaviors explicitly required by the MCP specification
- **Protocol Version Support**: Tests compatibility with MCP protocol versions 2024-11-05, 2025-03-26, and 2025-06-18
- **OAuth 2.1 Authentication**: Comprehensive testing of OAuth 2.1 flows per the 2025-06-18 specification
- **HTTP Transport Compliance**: Validates proper HTTP transport implementation
- **Session Management**: Tests session handling where specified
- **Tool and Resource Testing**: Dynamic testing of available tools and resources
- **Error Handling**: Tests proper JSON-RPC error responses

## Quick Start

```python
from mcp_testing.http.tester import MCPHttpTester

# Initialize tester
tester = MCPHttpTester("http://localhost:8080", debug=True)

# Run comprehensive test suite
result = tester.run_comprehensive_tests()
```

## Test Categories

### Core Protocol Tests
- **Initialization**: Server initialization and capability negotiation
- **Session Management**: Session handling (where specified)
- **Tool Operations**: Tool listing and execution
- **Protocol Version Negotiation**: Multi-version compatibility

### HTTP Transport Tests
- **Status Codes**: Tests only specified HTTP behaviors (invalid JSON, missing method)
- **Headers**: Required header validation
- **CORS**: OPTIONS request handling

### OAuth 2.1 Authentication Tests (2025-06-18)
- **Authorization Code Flow**: PKCE-enabled OAuth flow
- **Token Management**: Token validation and refresh
- **Error Scenarios**: Proper OAuth error handling
- **WWW-Authenticate Headers**: Compliance with authentication requirements

### Protocol-Specific Features
- **2025-06-18**: Structured tool output, batch request rejection, elicitation support
- **2025-03-26**: Async tool support
- **2024-11-05**: Basic protocol compliance

## Example Test Output

```
=== MCP HTTP Server Comprehensive Test Suite ===
Protocol Version: 2025-06-18

Testing OAuth 2.1 authorization flow...
✅ Authorization code flow supported
✅ PKCE S256 method supported
✅ Token exchange flow validated

=== Testing HTTP Status Codes (MCP Specification Only) ===
✅ invalid_json: Got expected status code 400
    Invalid JSON should return 400 (HTTP standard)
✅ missing_method: Got expected status code 400
    Missing method field should return 400 (JSON-RPC requirement)

Note: Tests for unknown_method and invalid_session have been removed
because they test unspecified HTTP implementation details, not MCP specification compliance.

=== Testing HTTP Headers ===
✅ content_type: All required headers present and valid
✅ session_id_present: All required headers present and valid
✅ protocol_version: All required headers present and valid

=== Testing Protocol Version Negotiation ===
✅ Version 2024-11-05: Successfully negotiated (server: 2024-11-05)
✅ Version 2025-03-26: Successfully negotiated (server: 2025-03-26)
✅ Version 2025-06-18: Successfully negotiated (server: 2025-06-18)

🎉 SERVER IS FULLY COMPLIANT WITH MCP SPECIFICATION
   All core functionality and protocol-specific features validated
   ✅ OAuth 2.1 authentication flow validated
   ✅ WWW-Authenticate header handling compliant
   ✅ MCP 2025-06-18 specific features validated
```

## Removed Tests

The following tests have been **intentionally removed** because they test unspecified implementation details:

- **unknown_method**: The MCP specification does not mandate specific HTTP status codes for unknown JSON-RPC methods
- **invalid_session**: Session validation behavior is not clearly specified in the MCP protocol

This aligns with our philosophy of testing only what is explicitly specified in the official MCP documentation.

## Configuration

### Basic Configuration
```python
tester = MCPHttpTester("http://localhost:8080", debug=True)
```

### Protocol Version Testing
```python
# Test specific protocol version
tester.protocol_version = "2025-06-18"
result = tester.run_comprehensive_tests()
```

## API Reference

### MCPHttpTester Class

Main testing class for MCP HTTP server validation.

#### Methods

- `run_comprehensive_tests()`: Execute full test suite
- `initialize()`: Test server initialization
- `list_tools()`: Test tool listing
- `test_available_tools()`: Test all available tools
- `test_oauth_flow()`: Test OAuth 2.1 authentication
- `test_status_codes()`: Test HTTP status code handling
- `test_headers()`: Test HTTP header compliance
- `test_protocol_versions()`: Test version negotiation

## Contributing

When adding new tests, ensure they test **only behaviors explicitly specified** in the MCP specification. Do not add tests for:
- Implementation-specific HTTP status codes
- Unspecified error handling behavior
- Custom extensions or "best practices"

All tests should reference the specific section of the MCP specification they validate. 