# MCP Protocol Validator

A comprehensive testing tool for validating Model Context Protocol (MCP) server and client implementations across multiple protocol versions.

## Overview

The MCP Protocol Validator is a test suite designed to ensure compliance with the Model Context Protocol specification. It provides:

- **Multi-Version Testing**: Support for testing against both 2024-11-05 and 2025-03-26 protocol specifications
- **Comprehensive Tests**: Verifies all essential aspects of the MCP specification
- **Multiple Transport Mechanisms**: Test both HTTP and STDIO transport implementations
- **Detailed Reports**: Generate HTML reports for easy compliance analysis
- **Protocol Comparison**: Compare behavior across different protocol versions
- **Docker Integration**: Run tests in a controlled Docker environment

## Protocol Version Support

The following protocol versions are currently supported:

| Version | Status | Description |
|---------|--------|-------------|
| 2025-03-26 | Supported | Extended with async support and environment variables |
| 2024-11-05 | Supported | Initial MCP protocol version |

You can specify which protocol version to test against using the `--protocol-version` flag:

```bash
# HTTP testing
python mcp_validator.py --url http://localhost:8080 --protocol-version 2024-11-05

# STDIO testing
python stdio_docker_test.py --protocol-version 2025-03-26
```

## Installation

### Prerequisites

- Python 3.8+ with pytest installed
- Docker (for STDIO testing with the filesystem server)
- Virtual environment (recommended)

### Setup

1. Clone the repository and create a virtual environment:
   ```bash
   git clone https://github.com/your-org/mcp-protocol-validator.git
   cd mcp-protocol-validator
   
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. For STDIO testing with Docker, ensure:
   - Docker is installed and running
   - The `mcp/filesystem` image is built (or specify your own image)
   - A Docker network will be created automatically by the test script

## Testing Options

### 1. STDIO Docker Testing (Recommended for Most Users)

For comprehensive validation of STDIO-based MCP server implementations:

```bash
# Basic usage
python stdio_docker_test.py

# Advanced usage with all options
python stdio_docker_test.py \
  --protocol-version 2025-03-26 \
  --docker-image mcp/filesystem \
  --network-name mcp-test-network \
  --mount-dir ./test_data/files \
  --debug \
  --timeout 15.0 \
  --max-retries 5 \
  --run-all-tests \
  --report
```

This is the most straightforward approach for testing STDIO-based MCP servers running in Docker containers. The script handles all necessary setup and configuration automatically.

#### Key Features

- **Automatic Docker Network Setup**: Creates necessary Docker networks
- **Test File Preparation**: Sets up test files including nested directories
- **Protocol Version Testing**: Supports testing against different protocol versions
- **HTML Reports**: Generates detailed test reports
- **Server Information Capture**: Shows server logs and diagnostic information
- **Comprehensive Error Handling**: Robust handling of timeouts and disconnections

#### Command Line Options

- `--protocol-version`, `-v`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--docker-image`: Docker image to use (default: mcp/filesystem)
- `--network-name`: Docker network name (default: mcp-test-network)
- `--mount-dir`, `-m`: Directory to mount in the Docker container
- `--debug`, `-d`: Enable detailed debug output
- `--timeout`, `-t`: Timeout for STDIO responses in seconds (default: 10.0)
- `--max-retries`, `-r`: Maximum retries for broken pipes (default: 3)
- `--run-all-tests`, `-a`: Run all compatible tests, not just the base protocol tests
- `--report`: Generate HTML test report
- `--report-dir`: Directory to store HTML test reports (default: reports/)

### 2. Advanced Testing with mcp_validator.py

For more advanced testing scenarios and detailed control over the test process, you can use the `mcp_validator.py` script directly. This approach requires Python 3.11 and should be used for HTTP-based MCP servers or for specialized testing scenarios:

```bash
# Create a Python 3.11 virtual environment
python3.11 -m venv .venv-py311
source .venv-py311/bin/activate

# Install dependencies
cd mcp-protocol-validator
pip install -r requirements.txt

# Example: Testing an HTTP-based MCP server
python mcp_validator.py test \
  --url http://localhost:8080 \
  --report ./mcp-compliance-report.html \
  --format html \
  --version 2025-03-26
```

**Important Note**: While `mcp_validator.py` does have STDIO support, testing STDIO servers is more complex with this approach. For STDIO-based Docker servers, we strongly recommend using the `stdio_docker_test.py` script instead, which is specifically designed for this purpose.

#### Key Benefits

- **Fine-grained Control**: More options for controlling the test process
- **Detailed Reporting**: Generate comprehensive test reports in various formats (HTML, JSON, Markdown)
- **Module Selection**: Specify which test modules to run (base, resources, tools, prompts, utilities)
- **Debug Output**: Verbose output for troubleshooting and understanding test flow
- **Transport Flexibility**: Test both HTTP and STDIO transport mechanisms (though HTTP is preferred)

#### Command Line Options

- `--url`: URL of the MCP server to test (required for HTTP testing)
- `--server-command`: Command to start a local MCP server (required for STDIO testing)
- `--report`: Path to save the test report
- `--format`: Report format (html, json, markdown)
- `--test-modules`: Comma-separated list of test modules to run (base,resources,tools,prompts,utilities)
- `--version`: MCP protocol version to test against (2024-11-05 or 2025-03-26)
- `--debug`: Enable debug output
- `--stdio-only`: Run only STDIO-compatible tests

### 3. Protocol Version Comparison

To compare how your server implementation behaves with different protocol versions, you can use the `compare_protocol_versions.py` script:

```bash
python compare_protocol_versions.py
```

This will:
- Test your server against both supported protocol versions (2024-11-05 and 2025-03-26)
- Report on test results, negotiated versions, and capabilities
- Show detailed server information and diagnostics
- Provide recommendations on compatibility

The comparison report includes:
- Test results for each protocol version (passed/failed/skipped tests)
- Negotiated protocol versions
- Available tools
- Server capabilities
- Server information from logs

Example output:
```
================================================================================
PROTOCOL VERSION COMPARISON
================================================================================

Protocol Version 1 (2024-11-05):
  Status: Pass
  Tests: 3 passed, 0 failed, 0 skipped
  Negotiated Version: 2024-11-05
  Server Capabilities: Not reported
  Available Tools: filesystem/read_file, filesystem/write_file, filesystem/list_directory
  Server Information:
    [SERVER] Secure MCP Filesystem Server running on stdio
    [SERVER] Allowed directories: [ '/projects' ]

Protocol Version 2 (2025-03-26):
  Status: Pass
  Tests: 3 passed, 0 failed, 0 skipped
  Negotiated Version: 2025-03-26
  Server Capabilities: Not reported
  Available Tools: filesystem/read_file, filesystem/write_file, filesystem/list_directory
  Server Information:
    [SERVER] Secure MCP Filesystem Server running on stdio
    [SERVER] Allowed directories: [ '/projects' ]

Recommendation:
  Server implementation works well with both protocol versions.
================================================================================
```

This is particularly useful when:
- Upgrading your server to support a newer protocol version
- Ensuring backward compatibility
- Diagnosing protocol-specific issues

### 4. HTTP Transport Testing

For servers that implement the HTTP transport:

```bash
# Set environment variables
export MCP_SERVER_URL="http://localhost:8080"
export MCP_TRANSPORT_TYPE="http"
export MCP_PROTOCOL_VERSION="2024-11-05"  # Optional: specify protocol version

# Run tests
pytest -v tests/
```

### 5. Custom STDIO Testing

For testing other STDIO servers (not using the Docker test script):

```bash
# Set environment variables
export MCP_TRANSPORT_TYPE="stdio"
export MCP_DEBUG_STDIO="1"
export MCP_PROTOCOL_VERSION="2025-03-26"  # Or specify a different version

# Launch your server and capture its process
SERVER_PROCESS=$(your_server_command)

# Import the testing framework and run tests
python -c "from tests.test_base import set_server_process; set_server_process($SERVER_PROCESS)"
pytest -v -m "not http_only" tests/
```

## Test Report Generation

You can generate HTML test reports for better visualization of test results:

```bash
# Generate HTML report with pytest directly
pytest -v tests/ --html=reports/test-report.html --self-contained-html

# Or use the STDIO test script with report option
python stdio_docker_test.py --protocol-version 2025-03-26 --report
```

Reports include:
- Summary of passed, failed, and skipped tests
- Details of each test case
- Environment information
- Test logs and error messages

## Testing Different Capabilities

When testing servers that support different capability sets:

1. **Basic Filesystem Capabilities**:
   - Default test suite is designed for servers implementing filesystem tools

2. **Custom Capabilities**:
   - For servers with specialized capabilities, you might need to modify the initialization request in `test_base_protocol.py` to match the expected capabilities

3. **Server-Specific Tests**:
   - You can create specialized test files for specific server implementations

## Schema Validation

The validator includes JSON schema files for validating MCP protocol messages:

- `schema/mcp_schema_2024-11-05.json`: Schema for the original protocol version
- `schema/mcp_schema_2025-03-26.json`: Schema for the newer protocol version with async support

These schemas are used by the test suite to validate the structure of request and response messages.

## Troubleshooting

### Common Issues

- **Connection errors**: Verify the server is running and accessible
- **Import errors**: Make sure you're running from the project root
- **STDIO issues**: Enable debug mode with `--debug` or `MCP_DEBUG_STDIO=1`  
- **Docker errors**: Check permissions for mounted directories and Docker installation
- **Protocol version errors**: Ensure your server supports the protocol version you're testing against
- **Network issues**: Verify Docker network exists or let the script create it

### Docker Setup Issues

When using the Docker testing approach:

1. **Docker Network**: If the script fails to create a Docker network, you can create it manually:
   ```bash
   docker network create mcp-test-network
   ```

2. **Mount Permissions**: If you encounter permission issues with mounted directories:
   - Verify that the specified directories exist
   - Check that you have read/write permissions to those directories
   - For Linux/macOS, you might need to adjust the permissions with `chmod`

3. **Docker Image**: If the Docker image is not found:
   - Build the image using: `docker build -t mcp/filesystem .`
   - Or specify a different image with the `--docker-image` option

### STDIO Transport Issues

When testing STDIO transport:

1. **Broken Pipe Errors**: If you see "broken pipe" errors:
   - Try increasing the `--timeout` value
   - Increase the `--max-retries` count
   - Check if your server is properly handling stdin/stdout

2. **No Response**: If the server doesn't respond:
   - Enable debug mode with `--debug`
   - Check the server logs for errors
   - Verify that the server is correctly implementing the STDIO transport protocol

3. **Process Management**: If the server process is not properly terminated:
   - The script will attempt to force kill the process
   - Check for any orphaned processes with `ps aux | grep your-server-name`

## Advanced Configuration Environment Variables

- `MCP_PROTOCOL_VERSION`: Set the protocol version to test against
- `MCP_DEBUG_STDIO`: Enable verbose STDIO debug output (0/1)
- `MCP_STDIO_TIMEOUT`: Set timeout for STDIO responses in seconds
- `MCP_STDIO_MAX_RETRIES`: Set maximum retries for broken pipes
- `MCP_DOCKER_IMAGE`: Docker image to use for testing
- `MCP_NETWORK_NAME`: Docker network name to use

## Features Tested

The MCP Protocol Validator tests the following key aspects of the MCP specification:

1. **Protocol Initialization**:
   - Protocol version negotiation
   - Capabilities exchange
   - Client/server information

2. **Tools**:
   - Tool discovery (tools/list)
   - Tool invocation (tools/call)
   - Parameter validation
   - Error handling

3. **Filesystem Operations** (for filesystem servers):
   - Directory listing
   - File reading
   - File writing
   - Path validation

4. **JSON-RPC Compliance**:
   - Message structure
   - Error responses
   - Method handling

5. **Environment Variables** (for 2025-03-26):
   - Environment variable support
   - Resource constraints

6. **Asynchronous Execution** (for 2025-03-26):
   - Async tool support
   - Task status tracking

## License

[GNU AFFERO GENERAL PUBLIC LICENSE](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.