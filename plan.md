# MCP Server Testing Suite Plan

## Overview
This document outlines a comprehensive testing approach for both stdio and HTTP MCP servers. The goal is to create a reusable testing framework that allows testing any MCP server implementation against either the 2024-11-05 or 2025-03-26 protocol specifications.

## Implementation Status

### ✅ Completed
- Full implementation of minimal_mcp_server with stdio transport
- Support for both 2024-11-05 and 2025-03-26 protocol versions
- Async tool functionality for the 2025-03-26 protocol
- Comprehensive test suite implementation
- All tests now passing for both protocol versions

### 🔄 In Progress
- HTTP transport implementation
- Performance optimization
- Documentation updates

## Test Suite Structure

### 1. Core Components

#### 1.1 Transport Adapters
- **StdioTransportAdapter**: For testing servers via stdin/stdout ✅
- **HttpTransportAdapter**: For testing servers via HTTP/SSE 🔄

Each adapter will implement a common interface that provides methods to:
- Start/stop the server process
- Send requests/notifications
- Receive responses/notifications
- Handle initialization/shutdown sequences

#### 1.2 Protocol Adapters
- **MCP2024_11_05ProtocolAdapter**: For testing 2024-11-05 protocol compliance ✅
- **MCP2025_03_26ProtocolAdapter**: For testing 2025-03-26 protocol compliance ✅

These adapters will handle protocol-specific details while using the transport adapters for communication.

#### 1.3 Test Runner
A utility to execute test cases with specific protocol/transport combinations and collect results. ✅

### 2. Test Categories

#### 2.1 Base Protocol Tests ✅
- **Initialization**: Test server initialization and version negotiation
- **Message Formatting**: Test JSON-RPC request/response formatting
- **Error Handling**: Test proper error responses
- **Batch Processing**: Test batch request handling
- **Lifecycle Management**: Test shutdown/exit behavior

#### 2.2 Core Feature Tests ✅
- **Tools**: Test tools/list and tools/call
  - Test built-in tools
  - Test tool error conditions
  - Test async tool calls (for 2025-03-26)
- **Resources**: Test resources/list, resources/get, resources/create
- **Prompt**: Test prompt/completion and prompt/models

#### 2.3 Transport-Specific Tests
- **STDIO-specific**: Newline handling, process management ✅
- **HTTP-specific**: SSE streaming, session management, HTTP status codes 🔄

#### 2.4 Protocol-Specific Tests ✅
- **2024-11-05 specific features**
- **2025-03-26 specific features** (async tool execution)

### 3. Implementation Progress

#### 3.1 Phase 1: Setup Testing Framework ✅
1. Create base interfaces for transport and protocol adapters
2. Implement stdio transport adapter
3. Create basic test runner
4. Implement 2024-11-05 protocol adapter
5. Create initial base protocol tests

#### 3.2 Phase 2: Expand Test Coverage ✅
1. Add tools/resources/prompt tests
2. Implement 2025-03-26 protocol adapter with async tool support
3. Add protocol-specific tests
4. Add transport-specific tests (STDIO)

#### 3.3 Phase 3: Reporting and Integration ✅
1. Implement test result collection and reporting
2. Create utility scripts for running test suites
3. Add documentation for adding new test cases

#### 3.4 Phase 4: Additional Transport Support 🔄
1. Implement HTTP transport adapter
2. Add HTTP-specific tests
3. Create visualizations for test coverage

## 4. Test Implementations

### 4.1 Base Protocol Test Cases ✅

#### Initialize Tests
- Test proper initialization with supported protocol version
- Test initialization with unsupported protocol version
- Test initialization without required parameters

#### JSON-RPC Message Tests
- Test proper request handling
- Test malformed request handling
- Test notification handling
- Test batch request handling
- Test error response formatting

#### Lifecycle Tests
- Test shutdown/exit sequence
- Test behavior after shutdown

### 4.2 Feature Test Cases ✅

#### Tools Tests
- Test tools/list returns correct tools
- Test tools/call with valid parameters
- Test tools/call with invalid parameters
- Test async tool calls (2025-03-26)
  - Test tools/call-async
  - Test tools/result for monitoring async operations
  - Test tools/cancel for canceling async operations
  - Test proper status reporting (running, completed, cancelled)

#### Resources Tests
- Test resources/list returns correct resources
- Test resources/get with valid ID
- Test resources/get with invalid ID
- Test resources/create with valid data
- Test resources/create with invalid data

#### Prompt Tests
- Test prompt/completion with valid input
- Test prompt/completion with invalid input
- Test prompt/models returns correct models

### 4.3 Transport-Specific Test Cases

#### STDIO Tests ✅
- Test newline handling
- Test process termination behavior
- Test stderr output

#### HTTP Tests 🔄
- Test SSE streaming
- Test session management
- Test HTTP status codes
- Test HTTP headers

## 5. Development Approach

### 5.1 Directory Structure ✅
```
mcp-testing/
├── transports/     # Transport adapters
│   ├── base.py     # Base transport adapter
│   ├── stdio.py    # STDIO transport adapter
│   └── http.py     # HTTP transport adapter (pending)
├── protocols/      # Protocol adapters
│   ├── base.py     # Base protocol adapter
│   ├── v2024_11_05.py  # 2024-11-05 protocol adapter
│   └── v2025_03_26.py  # 2025-03-26 protocol adapter
├── tests/          # Test cases
│   ├── base_protocol/  # Base protocol tests
│   ├── features/   # Feature tests
│   ├── transport_stdio/  # STDIO transport tests
│   └── transport_http/   # HTTP transport tests (pending)
├── utils/          # Utilities
│   └── runner.py   # Test runner
├── scripts/        # Scripts
│   ├── run_stdio_tests.py  # Run tests against STDIO server
│   └── run_http_tests.py   # Run tests against HTTP server (pending)
└── README.md       # Documentation
```

### 5.2 Implementation Strategy ✅
1. Started with a minimal implementation focusing on stdio transport
2. Used TDD (Test-Driven Development) approach
3. Used the minimal_mcp_server as a reference implementation for validation
4. Successfully implemented and tested async tool functionality for 2025-03-26

### 5.3 Dependencies
- pytest for test execution
- requests for HTTP communication
- sseclient-py for SSE handling
- rich for console output formatting
- click for CLI interface

## 6. Integration with minimal_mcp_server ✅

The minimal_mcp_server has been successfully implemented and tested to:
1. Pass all validation tests for both 2024-11-05 and 2025-03-26 protocol versions
2. Demonstrate correct implementation of async tool functionality
3. Serve as a reference implementation for other servers

### Key Features Implemented in minimal_mcp_server:
- Full protocol compliance for both versions
- Proper async tool support with the 2025-03-26 protocol
- Robust error handling
- Complete implementation of all required methods
- Support for long-running operations and cancellation

## 7. Conclusion

The testing suite has provided a comprehensive framework for testing MCP server implementations against both protocol specifications using the STDIO transport mechanism. The implementation of minimal_mcp_server serves as a complete reference implementation that correctly implements all aspects of the protocol, including the async tools functionality in the 2025-03-26 version. Future work will focus on extending support to HTTP transport and creating more advanced visualization tools for test results. 