# MCP Server Testing Suite Plan

## Overview
This document outlines a comprehensive testing approach for both stdio and HTTP MCP servers. The goal is to create a reusable testing framework that allows testing any MCP server implementation against either the 2024-11-05 or 2025-03-26 protocol specifications.

## Test Suite Structure

### 1. Core Components

#### 1.1 Transport Adapters
- **StdioTransportAdapter**: For testing servers via stdin/stdout
- **HttpTransportAdapter**: For testing servers via HTTP/SSE

Each adapter will implement a common interface that provides methods to:
- Start/stop the server process
- Send requests/notifications
- Receive responses/notifications
- Handle initialization/shutdown sequences

#### 1.2 Protocol Adapters
- **MCP2024_11_05ProtocolAdapter**: For testing 2024-11-05 protocol compliance
- **MCP2025_03_26ProtocolAdapter**: For testing 2025-03-26 protocol compliance

These adapters will handle protocol-specific details while using the transport adapters for communication.

#### 1.3 Test Runner
A utility to execute test cases with specific protocol/transport combinations and collect results.

### 2. Test Categories

#### 2.1 Base Protocol Tests
- **Initialization**: Test server initialization and version negotiation
- **Message Formatting**: Test JSON-RPC request/response formatting
- **Error Handling**: Test proper error responses
- **Batch Processing**: Test batch request handling
- **Lifecycle Management**: Test shutdown/exit behavior

#### 2.2 Core Feature Tests
- **Tools**: Test tools/list and tools/call
  - Test built-in tools
  - Test tool error conditions
  - Test async tool calls (for 2025-03-26)
- **Resources**: Test resources/list, resources/get, resources/create
- **Prompt**: Test prompt/completion and prompt/models

#### 2.3 Transport-Specific Tests
- **STDIO-specific**: Newline handling, process management
- **HTTP-specific**: SSE streaming, session management, HTTP status codes

#### 2.4 Protocol-Specific Tests
- **2024-11-05 specific features**
- **2025-03-26 specific features** (e.g., async tool execution)

### 3. Implementation Plan

#### 3.1 Phase 1: Setup Testing Framework
1. Create base interfaces for transport and protocol adapters
2. Implement stdio transport adapter
3. Create basic test runner
4. Implement 2024-11-05 protocol adapter
5. Create initial base protocol tests

#### 3.2 Phase 2: Expand Test Coverage
1. Add tools/resources/prompt tests
2. Implement HTTP transport adapter
3. Add protocol-specific tests
4. Add transport-specific tests

#### 3.3 Phase 3: Reporting and Integration
1. Implement test result collection and reporting
2. Create utility scripts for running test suites
3. Add documentation for adding new test cases
4. Create visualizations for test coverage

## 4. Test Implementations

### 4.1 Base Protocol Test Cases

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

### 4.2 Feature Test Cases

#### Tools Tests
- Test tools/list returns correct tools
- Test tools/call with valid parameters
- Test tools/call with invalid parameters
- Test async tool calls (2025-03-26)

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

#### STDIO Tests
- Test newline handling
- Test process termination behavior
- Test stderr output

#### HTTP Tests
- Test SSE streaming
- Test session management
- Test HTTP status codes
- Test HTTP headers

## 5. Development Approach

### 5.1 Directory Structure
```
mcp-testing/
├── transports/
│   ├── base.py
│   ├── stdio.py
│   └── http.py
├── protocols/
│   ├── base.py
│   ├── v2024_11_05.py
│   └── v2025_03_26.py
├── tests/
│   ├── base_protocol/
│   ├── features/
│   ├── transport_stdio/
│   └── transport_http/
├── utils/
│   ├── runner.py
│   └── reporter.py
└── scripts/
    ├── run_all_tests.py
    ├── run_stdio_tests.py
    └── run_http_tests.py
```

### 5.2 Implementation Strategy
1. Start with a minimal implementation focusing on stdio transport
2. Use TDD (Test-Driven Development) approach
3. Use the minimal_mcp_server as a reference implementation for validation
4. Add HTTP transport support once stdio tests are stable
5. Implement reporting and visualization last

### 5.3 Dependencies
- pytest for test execution
- requests for HTTP communication
- sseclient-py for SSE handling
- rich for console output formatting
- click for CLI interface

## 6. Integration with minimal_mcp_server

The minimal_mcp_server will be used as a reference implementation to:
1. Validate test cases (tests should pass when run against the minimal_mcp_server)
2. Provide examples of correct server behavior
3. Serve as a baseline for performance metrics

## 7. Conclusion

This testing suite will provide a comprehensive framework for testing any MCP server implementation against either protocol specification using either transport mechanism. The modular design allows for easy extension to support new protocol versions or transport mechanisms in the future. 