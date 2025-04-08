# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP Protocol Versions

This directory contains the implementation of different MCP protocol versions for the testing framework. Each version implements the specific requirements and capabilities of that protocol version.

## Components

- **base.py**: Base protocol class defining common functionality across versions
- **v2024_11_05.py**: Implementation of the 2024-11-05 protocol version
- **v2025_03_26.py**: Implementation of the 2025-03-26 protocol version

## Protocol Interface

Each protocol version extends the base `MCPProtocol` class, which defines a common interface for interacting with different protocol versions:

```python
class MCPProtocol:
    def get_version(self):
        """Get the protocol version string."""
        pass
        
    def get_initialize_params(self):
        """Get parameters for the initialize request."""
        pass
        
    def check_initialization_response(self, response):
        """Validate an initialization response."""
        pass
        
    def validate_tool_list(self, tools_list):
        """Validate a tools list response."""
        pass
        
    def get_spec_requirements(self):
        """Get a list of specification requirements for this version."""
        pass
```

## Protocol Version Features

### 2024-11-05 (Initial Version)

The initial protocol version with:
- Basic synchronous tool calls
- Simple initialization/shutdown flow
- Base tool requirements

### 2025-03-26 (Latest Version)

The updated protocol version adding:
- Asynchronous tool support with toolCallId and status
- Session management via sessionId
- Resources API capabilities
- Enhanced error handling

## Adding New Protocol Versions

To add a new protocol version:

1. Create a new file (e.g., `v2026_01_15.py`)
2. Extend the `MCPProtocol` base class
3. Implement all required methods
4. Add specific tests for new features in that version
5. Update `__init__.py` to expose the new version

Example of a new protocol version implementation:

```python
from .base import MCPProtocol

class MCP2026_01_15Protocol(MCPProtocol):
    def get_version(self):
        return "2026-01-15"
        
    def get_initialize_params(self):
        params = {
            "protocolVersion": self.get_version(),
            "clientInfo": {
                "name": "MCP Testing Framework",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "asyncSupported": True
                },
                "resources": True,
                "newFeature": True  # New capability introduced in this version
            }
        }
        return params
        
    # ... other method implementations ...
```

## Usage Example

```python
from mcp_testing.protocols import get_protocol
from mcp_testing.transports import HTTPTransport

# Get the protocol implementation for a specific version
protocol = get_protocol("2025-03-26")

# Create a transport
transport = HTTPTransport("http://localhost:9000/mcp")

# Use the protocol with the transport
initialize_params = protocol.get_initialize_params()
success, response = transport.initialize(initialize_params)

# Validate the response according to protocol requirements
if protocol.check_initialization_response(response):
    print("Server successfully initialized with protocol version", protocol.get_version()) 