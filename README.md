# MCP Protocol Validator

A comprehensive testing framework for validating MCP (Model Conversation Protocol) server implementations.

## Features

- Test servers using HTTP, STDIO, or Docker transport protocols
- Support for multiple protocol versions (2024-11-05, 2025-03-26)
- Comprehensive test suite covering all protocol features
- Minimal reference implementation for testing
- Detailed test reporting

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-protocol-validator.git
cd mcp-protocol-validator

# Install dependencies
pip install -r requirements.txt

# Run tests against an HTTP server
python mcp_validator.py --transport http --server-url http://localhost:3000

# Run tests against an STDIO server
python mcp_validator.py --transport stdio --server-command "./your_server.py"

# Compare protocol versions
python mcp_validator.py compare 2024-11-05 2025-03-26 comparison.html
```

## Transport Types

The validator supports three different ways to communicate with MCP servers:

### HTTP Transport
- Communication with an MCP server over HTTP/HTTPS protocol
- Sends JSON-RPC requests as HTTP POST requests to a server endpoint
- Example: `python mcp_validator.py --transport http --server-url http://localhost:3000`

### STDIO Transport
- Communication with an MCP server over Standard Input/Output streams
- Launches a server process, sends requests to stdin, reads responses from stdout
- Example: `python mcp_validator.py --transport stdio --server-command "python your_server.py"`

### Docker Transport
- Runs an MCP server inside a Docker container for isolated testing
- Example: `python mcp_validator.py --transport docker --docker-image mcp-server-image --mount-dir ./test_files`
- Enhanced implementation with automatic image pulling, network creation, and robust error handling

## Test Categories

The validator includes tests for all key protocol features:

- **Base Protocol**: Initialization, shutdown, version negotiation
- **Tools**: Tool listing and execution with parameters
- **Resources**: Resource creation, listing, and management
- **Prompts**: Basic prompt handling and completions
- **Utilities**: Batch request handling, error handling

## Configuration

Configuration can be provided via command-line arguments or environment variables:

| Command-line Option | Environment Variable | Description |
|---------------------|----------------------|-------------|
| `--transport` | `MCP_TRANSPORT_TYPE` | Transport protocol (http, stdio, docker) |
| `--server-url` | `MCP_SERVER_URL` | URL for HTTP server |
| `--server-command` | `MCP_SERVER_COMMAND` | Command to start STDIO server |
| `--docker-image` | `MCP_DOCKER_IMAGE` | Docker image for container testing |
| `--protocol-version` | `MCP_PROTOCOL_VERSION` | Protocol version to test |
| `--debug` | `MCP_DEBUG` | Enable debug logging |
| `--report` | - | Report format (html, json) |

## Minimal MCP Server

A reference implementation of an MCP server is included in the `minimal_mcp_server` directory:

- Implements both protocol versions: `2024-11-05` and `2025-03-26`
- Supports all protocol methods and features
- Serves as an example for implementing compliant servers
- Passes all validator tests

To run the minimal server:

```bash
cd minimal_mcp_server
./minimal_mcp_server.py
```

To test the minimal server:

```bash
cd minimal_mcp_server
./test_minimal_server.py --full
```

## Project Structure

```
mcp-protocol-validator/
├── mcp_validator.py         # Main entry point
├── tests/                   # Test suite
│   ├── test_base.py         # Base test class
│   ├── test_tools.py        # Tool tests
│   ├── test_protocol_negotiation.py
│   ├── test_resources.py
│   ├── test_prompts.py
│   └── test_utilities.py
├── transport/               # Transport adapters
│   ├── base.py              # Abstract base class
│   ├── http_client.py
│   ├── stdio_client.py
│   ├── docker_client.py
│   └── enhanced_docker_client.py  # Enhanced Docker transport
├── utils/                   # Utility functions
├── minimal_mcp_server/      # Reference implementation
├── schema/                  # JSON schema definitions
├── protocols/               # Protocol version definitions
├── tools/                   # Utility tools and scripts
│   └── debug_docker_transport.py  # Docker transport debugging script
└── reports/                 # Test reports
```

## Running Tests

```bash
# Run all tests
python mcp_validator.py

# Run specific test module
python mcp_validator.py --test-modules tools

# Generate HTML report
python mcp_validator.py --report html
```

## Debugging the Docker Transport

If you encounter issues with the Docker transport, you can use the included debugging script:

```bash
# Debug Docker transport with a specific image
python tools/debug_docker_transport.py --image your-mcp-server-image

# Specify protocol version and mount directory
python tools/debug_docker_transport.py --image your-mcp-server-image --protocol 2025-03-26 --mount ./test_files
```

The script provides detailed logging of the Docker container setup, network creation, and communication with the MCP server.

## License

AGPL-3.0-or-later