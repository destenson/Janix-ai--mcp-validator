# MCP Validator Release Notes

## v0.3.0 - 2025-01-21

### 🚀 Major Release: Full MCP 2025-06-18 Protocol Support

This release brings comprehensive support for the latest MCP 2025-06-18 specification, including OAuth 2.1 authentication, structured tool output, and production-ready GitHub Actions templates.

#### 🔐 OAuth 2.1 Authentication Framework
- **Complete OAuth 2.1 Implementation**: RFC 6749, RFC 6750, and OAuth 2.1 draft compliance
- **Bearer Token Support**: Automatic token extraction and validation from Authorization headers
- **WWW-Authenticate Headers**: Standards-compliant 401 responses with authentication challenges
- **Resource Server Capabilities**: Full OAuth 2.1 resource server implementation in reference HTTP server
- **MCP-Protocol-Version Headers**: Protocol version negotiation via HTTP headers
- **Security Features**: CORS support, origin validation, and DNS rebinding attack prevention

#### 📊 Structured Tool Output (2025-06-18)
- **Enhanced Tool Responses**: Tools return structured responses with `content`, `isError`, and `structuredContent` fields
- **Improved Tool Schema**: Tools use `inputSchema` (renamed from `parameters`), `title`, and `outputSchema` fields
- **Better Error Handling**: Structured error responses with detailed diagnostics
- **Validation Framework**: Comprehensive validation of tool output formats

#### 🔄 Protocol Enhancements
- **JSON-RPC Batching Removal**: Batch requests are properly rejected for 2025-06-18 protocol
- **Elicitation Support**: Framework for server-initiated user interactions and data collection
- **Enhanced Session Management**: Per-session protocol version tracking and feature negotiation
- **Resource Lifecycle Management**: Improved resource handling and metadata support

#### 🤖 GitHub Actions Templates
- **Production-Ready Templates**: Copy-paste GitHub Actions workflows for STDIO and HTTP servers
- **Multi-Protocol Testing**: Automated testing against 2025-03-26 and 2025-06-18 protocols
- **OAuth 2.1 Support**: Built-in authentication testing for 2025-06-18 servers
- **Detailed PR Comments**: Automatic compliance reports with feature-specific indicators
- **Easy Setup**: 3-step process - copy, edit one line, commit and push

#### 📈 Comprehensive Test Coverage
- **16 New Test Cases**: Specific validation for 2025-06-18 features
- **70% Protocol Coverage**: Achieved 70% test coverage for 2025-06-18 module (up from 12%)
- **End-to-End Testing**: Complete workflow testing from initialization to tool execution
- **Backward Compatibility**: All tests support 2024-11-05, 2025-03-26, and 2025-06-18 protocols

#### 🛠 Developer Experience Improvements
- **Updated CLI Tools**: All commands default to 2025-06-18 protocol
- **Enhanced Debug Output**: Better logging and error messages for troubleshooting
- **Comprehensive Documentation**: Updated README with OAuth 2.1 setup and examples
- **Reference Server Updates**: HTTP server supports all three protocol versions with feature detection

### 🔧 Technical Improvements

#### HTTP Transport Enhancements
- **Session ID Management**: Proper extraction from response body and URL parameters
- **Protocol Headers**: MCP-Protocol-Version header support for all requests
- **Error Handling**: Enhanced error responses with structured format
- **URL Construction**: Fixed endpoint handling for `/messages` vs root URL

#### STDIO Transport Updates
- **Protocol Negotiation**: Improved version detection and capability handling
- **Tool Output Validation**: Enhanced validation for structured responses
- **Error Recovery**: Better handling of malformed responses

#### Reference Server Improvements
- **Multi-Protocol Support**: Single server supporting 2024-11-05, 2025-03-26, and 2025-06-18
- **OAuth 2.1 Resource Server**: Complete authentication framework implementation
- **Dynamic Features**: Protocol-specific feature detection and response formatting
- **Production Ready**: Environment variable configuration for OAuth and security settings

### 🐛 Bug Fixes
- Fixed undefined `server` variable in reference HTTP server
- Corrected session ID extraction and URL parameter handling
- Fixed initialization request format for 2025-06-18 protocol
- Resolved unit test failures due to missing TransportError class
- Fixed CLI test expectations for default protocol version

### 📚 Documentation Updates
- **Comprehensive README**: OAuth 2.1 setup, 2025-06-18 features, and examples
- **GitHub Actions Guide**: Step-by-step setup instructions with troubleshooting
- **API Documentation**: Updated with new protocol features and authentication
- **Migration Guide**: Clear instructions for upgrading from older protocol versions

### 🔄 Backward Compatibility
- **Full Compatibility**: All existing protocol versions (2024-11-05, 2025-03-26) remain supported
- **Automatic Detection**: Protocol version detection and feature negotiation
- **Legacy Support**: Older tool response formats maintained for compatibility
- **Graceful Degradation**: Features unavailable in older protocols are properly handled

### 🚀 Getting Started with v0.3.0

#### Quick OAuth 2.1 Setup
```bash
# Enable OAuth 2.1 authentication
export MCP_OAUTH_ENABLED=true
export MCP_OAUTH_INTROSPECTION_URL=https://auth.example.com/oauth/introspect
export MCP_OAUTH_REQUIRED_SCOPES=mcp:read,mcp:write

# Start the reference server
python ref_http_server/reference_mcp_server.py --port 8088
```

#### GitHub Actions Integration
```bash
# Copy the template
cp ref_gh_actions/http-validation.yml .github/workflows/

# Edit one line - update SERVER_PATH
# Commit and push - automatic validation on PRs!
```

#### Test 2025-06-18 Features
```bash
# Test structured tool output
python -m mcp_testing.http.cli --server-url http://localhost:8088 --protocol-version 2025-06-18

# Test OAuth 2.1 authentication
curl -H "Authorization: Bearer your-token" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     http://localhost:8088/messages
```

---

## v0.2.0 - 2025-01-11

### Added
- **MCP Protocol 2025-06-18 Support**: Initial implementation of the latest MCP specification
- **Enhanced Reference HTTP Server**: Updated to support multiple protocol versions
- **New Test Cases**: 7 additional test cases for 2025-06-18 features
- **Improved Documentation**: Updated README with 2025-06-18 examples

### Changed
- **Default Protocol Version**: Updated default from 2025-03-26 to 2025-06-18
- **Tool Response Format**: Enhanced tool result structure
- **Test Coverage**: Expanded test suite

---

## v0.1.0 - 2023-07-15

### Added
- Initial public release
- Support for MCP protocol versions 2024-11-05 and 2025-03-26
- Reference implementations for STDIO and HTTP transports
- Comprehensive test suite for protocol compliance
- Dynamic tool testing and timeout handling
- Detailed compliance reporting 