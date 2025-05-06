# MCP Reference HTTP Servers

This directory contains reference implementations of the Model Completion Protocol (MCP) over HTTP for different protocol versions.

## Structure

```
ref_http_servers/
├── common/              # Shared utilities and error handling
├── v2024_11_05/        # 2024-11-05 protocol implementation
└── v2025_03_26/        # 2025-03-26 protocol implementation
```

## Protocol Versions

### 2024-11-05
- JSON-RPC 2.0 based protocol
- Session management via X-Session-Id header
- Basic filesystem operations support
- Initialize/shutdown lifecycle

### 2025-03-26
- JSON-RPC 2.0 based protocol
- Enhanced session management
- Extended filesystem operations
- Tool execution support
- Progress reporting

## Common Features

Both implementations share:
- JSON-RPC 2.0 message format
- Error handling
- Session management
- Basic protocol validation

## Running the Servers

Each version can be run independently:

```bash
# 2024-11-05 version
python -m ref_http_servers.v2024_11_05.server --port 8080

# 2025-03-26 version
python -m ref_http_servers.v2025_03_26.server --port 8081
```

## Testing

Each version includes its own test suite and can be tested independently:

```bash
# Test 2024-11-05 version
python -m pytest ref_http_servers/v2024_11_05/tests/

# Test 2025-03-26 version
python -m pytest ref_http_servers/v2025_03_26/tests/
```

## Dependencies

- Python 3.8+
- aiohttp
- pytest (for testing)
- pytest-asyncio (for testing) 