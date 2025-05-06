# Plan for MCP HTTP Server Refactoring (May 6, 2025)

## Goals

1. Create a modular, maintainable reference implementation of the MCP HTTP server
2. Support multiple protocol versions (2024-11-05, 2025-03-26)
3. Cleanly separate concerns: transport, session management, protocol handling
4. Eliminate global state in favor of session-based state
5. Support comprehensive testing
6. Ensure robustness and error handling

## Architecture

The new architecture separates the server implementation into several key components:

### 1. Transport Layer

**Files:**
- `minimal_http_server/v2/base_transport.py`

Two transport implementations:
- `HTTPJSONRPCTransport` - Standard HTTP/JSON-RPC with request/response
- `HTTPSSETransport` - HTTP/SSE for push notifications from server to client

Both implement a common `BaseTransport` interface with methods for sending responses and notifications.

### 2. Session Management

**Files:**
- `minimal_http_server/v2/session_manager.py`

Responsible for:
- Creating and tracking client sessions
- Managing session state
- Cleaning up expired sessions
- Isolating state between different clients

### 3. Protocol Handlers

**Files:**
- `minimal_http_server/v2/protocol_handler.py`

Protocol-specific implementations:
- `Protocol_2024_11_05` - Handles the 2024-11-05 version of MCP
- `Protocol_2025_03_26` - Handles the 2025-03-26 version of MCP

Both implement a common `ProtocolHandler` interface. A `ProtocolHandlerFactory` creates the appropriate handler based on the client's requested protocol version.

### 4. HTTP Server

**Files:**
- `minimal_http_server/v2/server.py`

Provides:
- HTTP request handling
- JSON-RPC request parsing
- Session management
- Routing to appropriate protocol handlers
- Error handling and logging

### 5. Client and Testing

**Files:**
- `minimal_http_server/v2/test_client.py`

A test client that can:
- Initialize sessions
- Call tools (sync and async)
- Handle errors
- Verify correct server behavior

### 6. Launcher

**Files:**
- `minimal_http_server/launcher.py`

A unified entry point that can:
- Launch either the original or new server implementation
- Configure logging, ports, etc.
- Provide a consistent command-line interface

## Key Improvements

1. **Isolated Session State:**
   - Each client session maintains its own state
   - No more global state variables
   - Sessions can use different protocol versions simultaneously

2. **Clean Separation of Transport and Protocol:**
   - Transport layer handles HTTP communication details
   - Protocol layer handles MCP-specific logic
   - Makes it easier to add new protocol versions or transport mechanisms

3. **Error Handling:**
   - Consistent error reporting
   - Better logging
   - Graceful handling of client disconnections

4. **Resource Management:**
   - Proper cleanup of sessions and connections
   - Graceful shutdown with signal handling
   - Automatic port selection option

5. **Testing:**
   - Comprehensive test client
   - Better support for testing both protocol versions
   - Easier to extend for compliance testing

## Protocol Version Compatibility

The implementation now handles both protocol versions (2024-11-05 and 2025-03-26) with key differences:

1. **Schema Format Differences:**
   - 2024-11-05 uses `inputSchema` in tool definitions
   - 2025-03-26 uses `parameters` in tool definitions

2. **Tool Call Format Differences:**
   - 2024-11-05 uses `arguments` for parameters
   - 2025-03-26 uses `parameters` for parameters

3. **Capabilities Differences:**
   - 2024-11-05: `"tools": true`
   - 2025-03-26: `"tools": {"asyncSupported": true}`

4. **Feature Availability:**
   - Only 2025-03-26 supports async tool calls
   - Only 2025-03-26 supports resources

We've implemented compatibility features to handle these differences:
- Protocol handlers automatically convert between formats
- Backward compatibility for both parameter passing styles
- Root-level `protocolVersion` in responses for both versions

## Compliance Testing Status

- ✅ Successfully passed 2025-03-26 compliance tests
- ⚠️ Working through test harness issues with 2024-11-05 compliance tests
- ✅ Basic functionality verified through internal test client for both protocol versions
- ✅ Server correctly handles parameter format differences

## Implementation Status

- [x] Architecture design
- [x] Base transport classes
- [x] Session manager
- [x] Protocol handlers (2024-11-05, 2025-03-26)
- [x] HTTP server implementation
- [x] Test client
- [x] Launcher script
- [x] Protocol version-specific response handling
- [x] Successful 2025-03-26 compliance testing
- [ ] Complete 2024-11-05 compliance testing
- [ ] Comprehensive integration tests
- [ ] Documentation
- [ ] Performance optimizations

## Next Steps

1. **Fix 2024-11-05 Protocol Compliance**
   - Resolve connection timeout issues in compliance testing
   - Add special handling for compliance test edge cases
   - Ensure parameter handling is fully compatible

2. **Improve Reliability**
   - Add better error handling for network issues
   - Implement more robust session cleanup
   - Add timeouts and retries for operations

3. **Comprehensive Testing**
   - Complete integration tests for both protocol versions
   - Add unit tests for individual components
   - Test with real-world tool implementations

4. **Documentation and Deployment**
   - Document API and usage patterns
   - Create container and deployment configurations
   - Add performance metrics and monitoring

5. **Compliance Testing**
   - Run the full MCP compliance test suite on both protocol versions
   - Create test reports and compliance documentation
   - Address any remaining specification gaps 