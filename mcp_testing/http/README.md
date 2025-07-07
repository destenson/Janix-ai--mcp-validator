# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP HTTP Testing Framework

This module provides comprehensive testing capabilities for MCP HTTP server implementations, with full support for OAuth 2.1 authentication flows.

## Features

### Core Testing
- **Protocol Compliance**: Tests adherence to MCP specifications across all supported versions
- **Session Management**: Validates proper session handling and state management
- **Tool Invocation**: Tests both synchronous and asynchronous tool calling
- **Error Handling**: Validates proper error responses and status codes

### OAuth 2.1 Authentication Testing
- **401 Response Handling**: Properly handles authentication challenges instead of treating them as failures
- **WWW-Authenticate Header Parsing**: Extracts and validates authentication challenges
- **OAuth Server Metadata**: Fetches and validates `.well-known/oauth-authorization-server` endpoints
- **Bearer Token Support**: Tests proper Bearer token handling and validation

## Components

- **tester.py**: Core `MCPHttpTester` class that implements the test suite
- **session_validator.py**: `MCPSessionValidator` class for testing server session handling
- **utils.py**: Helper utilities for server connectivity checks and other common tasks
- **cli.py**: Command-line interface for running tests

## Usage

### Basic Usage

```python
from mcp_testing.http.tester import MCPHttpTester

# Create tester instance
tester = MCPHttpTester("http://localhost:8080/mcp", debug=True)

# Run comprehensive tests (includes OAuth flow testing)
success = tester.run_comprehensive_tests()

# Or run basic tests only
success = tester.run_all_tests()
```

### Command Line Interface

```bash
# Run comprehensive tests (default)
python -m mcp_testing.http.cli --server-url http://localhost:8080/mcp

# Run basic tests only
python -m mcp_testing.http.cli --server-url http://localhost:8080/mcp --basic-only

# Test specific protocol version
python -m mcp_testing.http.cli --server-url http://localhost:8080/mcp --protocol-version 2025-06-18

# Enable debug output
python -m mcp_testing.http.cli --server-url http://localhost:8080/mcp --debug
```

## OAuth 2.1 Flow Testing

The comprehensive test suite includes OAuth 2.1 authentication flow testing:

### What It Tests

1. **401 Response Handling**: When a server returns 401 Unauthorized, the tester:
   - ✅ Recognizes this as a proper authentication challenge (not a failure)
   - ✅ Extracts and parses WWW-Authenticate headers
   - ✅ Validates Bearer token challenge parameters

2. **OAuth Server Metadata**: Attempts to fetch OAuth server metadata from:
   - `.well-known/oauth-authorization-server`
   - Validates required fields: `authorization_endpoint`, `token_endpoint`, `issuer`

3. **Protocol Compliance**: Ensures servers follow OAuth 2.1 and MCP 2025-06-18 specifications

### Example Output

```
=== MCP HTTP Server Comprehensive Test Suite ===
Testing OAuth 2.1 authorization flow...
✅ Server properly returns 401 for unauthenticated requests
✅ Server provides WWW-Authenticate header
✅ Server uses Bearer authentication scheme
✅ OAuth server metadata available
✅ OAuth metadata contains authorization_endpoint
✅ OAuth metadata contains token_endpoint
✅ OAuth metadata contains issuer

=== Testing HTTP Status Codes ===
✅ invalid_json: Got expected status code 400
✅ no_method: Got expected status code 400
✅ unknown_method: Got expected status code 404
✅ authentication_required: Got expected status code 401
    OAuth challenge detected: True

=== Testing HTTP Headers ===
✅ content_type: All required headers present and valid
✅ session_id_present: All required headers present and valid
✅ protocol_version: All required headers present and valid

=== Testing Protocol Version Negotiation ===
✅ Version 2024-11-05: Successfully negotiated (server: 2024-11-05)
✅ Version 2025-03-26: Successfully negotiated (server: 2025-03-26)
✅ Version 2025-06-18: Server requires authentication (OAuth 2.1)

==================================================
✅ ALL TESTS PASSED
Server is fully compliant with MCP specification
==================================================
```

## Implementation Notes

### Key Changes from Previous Versions

1. **401 Not a Failure**: 401 responses are now properly handled as authentication challenges rather than test failures
2. **OAuth Flow Recognition**: The tester recognizes and validates OAuth 2.1 authentication flows
3. **Well-Known Endpoint Support**: Automatically fetches OAuth server metadata when available
4. **Flexible Response Handling**: Adapts to servers that require authentication vs. those that don't

### Backward Compatibility

The framework maintains backward compatibility:
- `run_all_tests()` still available for basic testing
- `run_comprehensive_tests()` includes new OAuth flow testing
- All existing test methods remain unchanged

## Testing Different Server Types

### No Authentication Required
- Server responds with 200 OK to requests
- Tests proceed normally
- Result: ✅ Server doesn't require authentication

### OAuth 2.1 Required
- Server responds with 401 Unauthorized
- Includes WWW-Authenticate header with Bearer challenge
- Provides OAuth server metadata at `.well-known/oauth-authorization-server`
- Result: ✅ Server requires authentication (OAuth 2.1)

### Legacy Authentication
- Server responds with 401 Unauthorized
- May or may not include WWW-Authenticate header
- No OAuth server metadata available
- Result: ⚠️ Server requires authentication (legacy method)

## Future Enhancements

Planned improvements include:
- **Full OAuth Flow Testing**: Complete authorization code flow testing
- **Token Refresh Testing**: Validation of token refresh mechanisms
- **Scope Validation**: Testing of OAuth scope requirements
- **PKCE Support**: Testing of Proof Key for Code Exchange

## Comprehensive Testing Script

For advanced testing scenarios, use the comprehensive testing script:

```bash
# Run all tests (basic, OAuth, comprehensive, security)
python -m mcp_testing.scripts.comprehensive_http_test --server-url http://localhost:8080/mcp --test-type all

# Run only OAuth 2.1 validation
python -m mcp_testing.scripts.comprehensive_http_test --server-url http://localhost:8080/mcp --test-type oauth

# Run security-focused validation
python -m mcp_testing.scripts.comprehensive_http_test --server-url http://localhost:8080/mcp --test-type security

# Generate detailed compliance report
python -m mcp_testing.scripts.comprehensive_http_test --server-url http://localhost:8080/mcp --output compliance_report.json
```

### Advanced Features Implemented

✅ **Complete OAuth 2.1 Implementation**
- Authorization code flow with PKCE validation
- Token refresh mechanism testing
- Scope validation and enforcement testing
- Resource indicators (RFC 8707) support

✅ **Enhanced Authentication Testing**
- OAuth error scenario validation (invalid_client, invalid_grant, invalid_scope)
- Token audience claim validation (prevents confused deputy attacks)
- Bearer token format and usage compliance

✅ **Protocol Compliance Testing**
- WWW-Authenticate header flexibility (MUST → SHOULD change)
- MCP 2025-06-18 structured tool output validation
- Batch request rejection testing (removed in 2025-06-18)
- Elicitation support framework testing

✅ **Security Validation**
- Confused deputy attack prevention
- Session security validation
- CORS compliance verification
- Token passthrough prevention

### Test Categories

**Basic Tests**: Core MCP functionality (initialization, tool listing, tool calls)
**OAuth Tests**: OAuth 2.1 authentication flow validation
**Comprehensive Tests**: All basic + OAuth + protocol compliance + security
**Security Tests**: Focused security and OAuth security validation

## Test Coverage

The HTTP testing module currently tests:

1. **CORS Support**: Verifies that the server properly handles OPTIONS requests and returns CORS headers
2. **Initialization**: Tests the server's ability to initialize and return a session ID
3. **Tools Listing**: Verifies that the server can list available tools
4. **Tool Execution**: Tests basic tool execution (echo, add)
5. **Async Tools**: Tests async tool execution with the sleep tool
6. **Session Handling**: Tests server's ability to maintain and validate sessions via the `Mcp-Session-Id` header

### Session Test Coverage

The session validator specifically tests:

1. **Session Creation**: Tests that the server generates a valid session ID during initialization
2. **Session Validation**: Tests that the server properly accepts or rejects requests based on session ID validity
3. **Session Persistence**: Tests that the server maintains state across multiple requests with the same session ID
4. **Missing Session**: Tests server behavior when session ID is not provided
5. **Invalid Session**: Tests server behavior when an invalid session ID is provided

## Adding New Tests

To add new tests, add methods to the `MCPHttpTester` class in `tester.py` or the `MCPSessionValidator` class in `session_validator.py`. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your new test method to the list in the `run_all_tests` method to include it in the full test suite. 