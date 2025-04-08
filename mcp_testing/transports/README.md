# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP Transport Layers

This directory contains the transport layer implementations for the MCP testing framework. Transport layers handle the communication between the testing framework and MCP servers using different protocols.

## Components

- **base.py**: Abstract base class defining the transport layer interface
- **stdio.py**: Implementation for Standard Input/Output (STDIO) transport
- **http.py**: Implementation for HTTP transport

## Transport Interface

All transport implementations inherit from the `MCPTransport` base class, which defines a common interface for MCP communication:

```python
class MCPTransport:
    def initialize(self, protocol_version, capabilities=None):
        """Initialize the MCP server."""
        pass
        
    def list_tools(self):
        """List available tools."""
        pass
        
    def invoke_tool_call(self, tool_name, parameters):
        """Invoke a tool."""
        pass
        
    def get_tool_call_status(self, tool_call_id):
        """Get status of an async tool call."""
        pass
        
    def shutdown(self):
        """Shutdown the MCP server."""
        pass
```

## Adding New Transport Layers

To add a new transport layer:

1. Create a new file in this directory (e.g., `websocket.py`)
2. Implement a class that inherits from `MCPTransport`
3. Implement all required methods defined in the base class
4. Add appropriate error handling and logging
5. Update the `__init__.py` file to expose the new transport

Example of a new transport implementation:

```python
from .base import MCPTransport

class WebSocketTransport(MCPTransport):
    def __init__(self, url, **kwargs):
        super().__init__()
        self.url = url
        self.connection = None
        # ... initialization code ...
        
    def initialize(self, protocol_version, capabilities=None):
        # ... implementation ...
        pass
        
    # ... other method implementations ...
```

## Usage Example

```python
from mcp_testing.transports.http import HTTPTransport
from mcp_testing.transports.stdio import STDIOTransport

# Create transport instances
http = HTTPTransport("http://localhost:9000/mcp")
stdio = STDIOTransport("python ./server.py")

# Initialize connections
http.initialize("2025-03-26")
stdio.initialize("2025-03-26")

# List available tools
http_tools = http.list_tools()
stdio_tools = stdio.list_tools()

# Clean up
http.shutdown()
stdio.shutdown()
``` 