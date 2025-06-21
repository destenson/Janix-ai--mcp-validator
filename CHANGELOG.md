# Changelog

All notable changes to the MCP Protocol Validator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-21

### Added
- **OAuth 2.1 Authentication Framework**: Complete implementation for 2025-06-18 protocol
  - Bearer token extraction and validation from Authorization headers
  - WWW-Authenticate headers for 401 responses with authentication challenges
  - Resource server capabilities in reference HTTP server
  - MCP-Protocol-Version header support for protocol negotiation
  - CORS support, origin validation, and DNS rebinding attack prevention
  - Environment variable configuration for OAuth settings
- **GitHub Actions Templates**: Production-ready CI/CD workflows
  - `http-validation.yml` for HTTP-based MCP servers
  - `stdio-validation.yml` for STDIO-based MCP servers
  - Multi-protocol testing (2025-03-26 and 2025-06-18)
  - OAuth 2.1 authentication testing support
  - Automated PR comments with detailed compliance reports
  - 3-step setup process with comprehensive documentation
- **Enhanced Test Coverage**: Achieved 70% coverage for 2025-06-18 protocol module
  - 16 comprehensive test cases for 2025-06-18 features
  - OAuth capability negotiation and token handling tests
  - Structured tool output validation tests
  - Batch request rejection tests
  - Elicitation support framework tests
  - End-to-end workflow testing from initialization to tool execution
- **JSON Schema**: Complete `mcp_schema_2025-06-18.json` with OAuth 2.1 requirements
- **Production-Ready Reference Server**: Enhanced HTTP server with OAuth 2.1 resource server capabilities

### Changed
- **HTTP Transport**: Major improvements for 2025-06-18 protocol
  - Fixed session ID extraction from response body and URL parameters
  - Added MCP-Protocol-Version header to all requests
  - Improved URL construction for `/messages` endpoint
  - Enhanced error handling with structured responses
  - Fixed initialization request format for 2025-06-18
- **Protocol Adapters**: Enhanced 2025-06-18 adapter with OAuth token handling
- **CLI Tools**: Updated all commands to default to 2025-06-18 protocol
- **Documentation**: Comprehensive updates with OAuth 2.1 setup and GitHub Actions guidance

### Fixed
- **Reference HTTP Server**: Fixed undefined `server` variable (lines 617 and 676)
- **Session Management**: Corrected session ID extraction and URL parameter handling
- **Unit Tests**: Resolved missing TransportError class causing test failures
- **CLI Tests**: Fixed protocol version expectations for 2025-06-18 default
- **Transport Layer**: Fixed initialization flow and notification handling

### Security
- **OAuth 2.1 Compliance**: Full RFC 6749, RFC 6750, and OAuth 2.1 draft compliance
- **Bearer Token Validation**: Secure token extraction and validation
- **Origin Validation**: DNS rebinding attack prevention
- **CORS Support**: Proper cross-origin resource sharing configuration

## [0.2.0] - 2025-01-11

### Added
- **MCP Protocol 2025-06-18 Support**: Full implementation of the latest MCP specification
  - Structured tool output with `content` arrays and `structuredContent` fields
  - Elicitation support for server-initiated user interactions
  - Enhanced error handling with structured error responses
  - Tool schema improvements with `inputSchema`, `outputSchema`, and `title` fields
- **JSON-RPC Batching Restrictions**: Proper rejection of batch requests in 2025-06-18 protocol
- **New Test Cases**: 7 additional test cases specifically for 2025-06-18 features
  - `test_structured_tool_output`: Validates structured tool response format
  - `test_elicitation_support`: Tests elicitation capability framework
  - `test_no_batch_requests`: Ensures batch requests are properly rejected
  - `test_enhanced_error_handling`: Verifies improved error response structure
  - `test_resource_lifecycle`: Tests resource management improvements
  - `test_tool_output_validation`: Validates stricter tool output requirements
  - `test_session_management`: Tests enhanced session handling
- **Enhanced Reference HTTP Server**: Updated to support all three protocol versions (2024-11-05, 2025-03-26, 2025-06-18)
  - Backward compatibility with older protocol versions
  - Protocol-specific response formatting
  - Dynamic feature detection based on negotiated protocol version

### Changed
- **Default Protocol Version**: Updated default from 2025-03-26 to 2025-06-18 across all CLI tools
- **Tool Response Format**: Enhanced tool result structure for 2025-06-18 compatibility
- **Error Response Structure**: Improved error messages and categorization
- **Test Coverage**: Expanded test suite to cover new protocol features
- **Documentation**: Updated README with 2025-06-18 examples and feature descriptions

### Backward Compatibility
- All existing protocol versions (2024-11-05, 2025-03-26) remain fully supported
- Automatic protocol version detection and handling
- Legacy tool response formats maintained for older protocols

## [0.1.0] - 2023-07-15

### Added
- Initial public release
- Support for testing MCP protocol versions 2024-11-05 and 2025-03-26
- Minimal reference implementation for STDIO transport
- Minimal reference implementation for HTTP transport
- Comprehensive test suite for protocol compliance
- Dynamic tool testing
- Timeout handling for problematic servers
- Detailed compliance reporting
- Support for pip-installed MCP servers

### Changed
- Improved timeout handling for problematic servers
- Enhanced reporting format with more detailed diagnostics
- Streamlined test execution with better progress indicators

### Fixed
- Properly handle servers that don't implement shutdown method
- Timeout gracefully for servers with tool list issues
- Correctly display status for skipped tests in reports 