# MCP Reference HTTP Server

This package provides reference implementations of HTTP servers for the Model Completion Protocol (MCP).

## Directory Structure

```
ref_http_server/
├── common/           # Common utilities and error handling
├── v2024_11_05/     # Implementation for version 2024-11-05
└── v2025_03_26/     # Implementation for version 2025-03-26
```

## Features

### Common Components
- JSON-RPC 2.0 request validation and response formatting
- Comprehensive error handling
- Shared utilities

### Version 2024-11-05
- Basic session management
- Filesystem operations
- Clean shutdown handling

### Version 2025-03-26
- Enhanced async capabilities
- Task management with UUID-based tracking
- Resource constraints
- Proper notification handling (204 responses)

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Servers

### Version 2024-11-05
```bash
python -m ref_http_server.v2024_11_05.run_server --port 8080
```

### Version 2025-03-26
```bash
python -m ref_http_server.v2025_03_26.run_server --port 8081
```

## Testing

### Version 2024-11-05
```bash
python -m pytest ref_http_server/v2024_11_05/tests/
```

### Version 2025-03-26
```bash
python -m pytest ref_http_server/v2025_03_26/tests/
```

## License

See LICENSE.txt for details. 