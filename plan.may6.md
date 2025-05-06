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

## Implementation Status

- [x] Architecture design
- [x] Base transport classes
- [x] Session manager
- [x] Protocol handlers (2024-11-05, 2025-03-26)
- [x] HTTP server implementation
- [x] Test client
- [x] Launcher script
- [ ] Comprehensive integration tests
- [ ] Documentation
- [ ] Performance optimizations

## Next Steps

1. Complete integration tests for both protocol versions
2. Document API and usage patterns
3. Add performance metrics and monitoring
4. Create container and deployment configurations
5. Implement any additional features required by the latest MCP specifications 