# MCP Protocol Validator

A comprehensive testing framework for validating MCP (Machine Conversation Protocol) server implementations.

## Features

- Test servers using HTTP or STDIO transport protocols
- Support for multiple protocol versions (2024-11-05, 2025-03-26)
- Comprehensive test suite covering all protocol features
- Docker-based reference implementations for testing
- Detailed test reporting

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-protocol-validator.git
cd mcp-protocol-validator

# Install dependencies
pip install -r requirements.txt

# Run tests against an HTTP server
./run_validator.py --transport http --server-url http://localhost:3000
```

## Transport Types

The validator supports three different ways to communicate with MCP servers:

### HTTP Transport
- Communication with an MCP server over HTTP/HTTPS protocol
- Sends JSON-RPC requests as HTTP POST requests to a server endpoint
- Requires a URL (e.g., `http://localhost:3000`)
- Example: `./run_validator.py --transport http --server-url http://localhost:3000`

### STDIO Transport
- Communication with an MCP server over Standard Input/Output streams
- Launches a server process, sends requests to stdin, reads responses from stdout
- Requires a command to start the server
- Example: `./run_validator.py --transport stdio --server-command "python server.py"`

### Docker Transport
- Runs an MCP server inside a Docker container for isolated testing
- Can test both HTTP and STDIO servers in a containerized environment
- Requires a Docker image name and optionally a directory to mount
- Example: `./run_validator.py --transport docker --docker-image mcp-stdio-server --mount-dir ./test_files`

## Documentation

For detailed usage instructions, see the [User Guide](docs/user_guide.md).

For information about protocol version differences, see the [Version Comparison](docs/version_comparison.md).

For future development plans, see the [Roadmap](docs/roadmap.md).

## Docker Test Servers

Build the Docker test servers:

```bash
cd docker
./build_test_servers.sh
```

## Running All Tests

To run a comprehensive test suite against both HTTP and STDIO servers with both protocol versions:

```bash
./run_all_tests.sh
```

This script:
1. Builds the Docker test servers if needed
2. Creates a reports directory
3. Runs all tests against the HTTP server with protocol version 2024-11-05
4. Runs all tests against the HTTP server with protocol version 2025-03-26
5. Runs all tests against the STDIO server with protocol version 2024-11-05
6. Runs all tests against the STDIO server with protocol version 2025-03-26
7. Generates HTML reports for each test run in the reports directory

The generated reports provide detailed information about test results, including:
- Failed or passed tests
- Detailed error messages
- Testing statistics

## Legacy Test Scripts

All legacy test scripts have been moved to the `legacy` directory. These scripts were created before the unified testing framework and are maintained for backward compatibility but are superseded by the new framework.

For information about these legacy scripts and how they relate to the new framework, see [Legacy Tests Documentation](docs/legacy_tests.md).

## Archive

The `archive` directory contains older versions of the codebase and other historical artifacts that are no longer in active use but are preserved for reference purposes. This includes an older version of the MCP Protocol Validator framework.

## License

AGPL-3.0-or-later