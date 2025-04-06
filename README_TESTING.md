# MCP Protocol Validator Testing Guide

This guide explains how to test MCP server implementations using both HTTP and STDIO transport mechanisms across different protocol versions.

## Prerequisites

- Python 3.8+ with pytest installed
- Docker (for STDIO testing with the filesystem server)
- Virtual environment (recommended)

## Setup

1. Install required packages:
   ```bash
   # Create and activate virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install pytest pytest-html requests
   ```

2. For STDIO testing with Docker, ensure:
   - Docker is installed and running
   - The `mcp/filesystem` image is built (or specify your own image)
   - A Docker network exists (automatically created by the test script)

## Protocol Version Testing

The validator supports testing against multiple versions of the MCP specification:

- **2025-03-26**: Latest protocol version with enhanced capabilities
- **2024-11-05**: Earlier protocol version

To specify which protocol version to test against:

```bash
# Via environment variable
export MCP_PROTOCOL_VERSION="2024-11-05"

# Via command-line parameter in the STDIO test script
python stdio_docker_test.py --protocol-version 2024-11-05

# Via mcp_validator.py
python mcp_validator.py --url http://localhost:8080 --protocol-version 2024-11-05
```

## Comprehensive Testing with Protocol Comparison

For the most thorough validation, you can compare your server implementation across multiple protocol versions using the protocol comparison tool:

```bash
python compare_protocol_versions.py
```

This will:
- Test your server against both supported protocol versions (2024-11-05 and 2025-03-26)
- Report on test results, negotiated versions, and capabilities
- Show detailed server information and diagnostics
- Provide recommendations on compatibility

The report shows:
- Test results (passed/failed/skipped)
- Negotiated protocol versions
- Available tools
- Server capabilities
- Server information from logs

## STDIO Docker Testing Options

The enhanced `stdio_docker_test.py` script provides comprehensive testing for STDIO transport servers:

```bash
# Basic usage with default settings
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
  --report \
  --report-dir ./reports
```

### Command-line Options

The script offers these command-line options:
- `--protocol-version` / `-v`: Protocol version to test (2024-11-05 or 2025-03-26)
- `--docker-image`: Docker image to use for testing (default: mcp/filesystem)
- `--network-name`: Docker network name (default: mcp-test-network)
- `--mount-dir` / `-m`: Directory to mount in the Docker container
- `--debug` / `-d`: Enable detailed debug output
- `--timeout` / `-t`: Timeout for STDIO responses in seconds (default: 10.0)
- `--max-retries` / `-r`: Maximum retries for broken pipes (default: 3)
- `--run-all-tests` / `-a`: Run all compatible tests, not just basic protocol tests
- `--report`: Generate HTML test report
- `--report-dir`: Directory to store HTML test reports (default: reports/)

### What the Script Does

The enhanced script:
- Creates a Docker network if it doesn't exist
- Prepares test files including nested directories and various file types
- Launches the Docker filesystem server with environment variables
- Configures the environment for STDIO transport
- Runs the appropriate tests based on the options provided
- Generates HTML reports if requested
- Handles server cleanup

## HTTP Transport Testing

For servers that implement the HTTP transport:

```bash
# Set environment variables
export MCP_SERVER_URL="http://localhost:8080"
export MCP_TRANSPORT_TYPE="http"
export MCP_PROTOCOL_VERSION="2024-11-05"  # Optional: specify protocol version

# Run tests
pytest -v tests/
```

## Custom STDIO Testing

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

## Troubleshooting

- **Connection errors**: Verify the server is running and accessible
- **Import errors**: Make sure you're running from the project root
- **STDIO issues**: Enable debug mode with `--debug` or `MCP_DEBUG_STDIO=1`  
- **Docker errors**: Check permissions for mounted directories and Docker installation
- **Protocol version errors**: Ensure your server supports the protocol version you're testing against
- **Network issues**: Verify Docker network exists or let the script create it

## Advanced Configuration Environment Variables

- `MCP_PROTOCOL_VERSION`: Set the protocol version to test against
- `MCP_DEBUG_STDIO`: Enable verbose STDIO debug output (0/1)
- `MCP_STDIO_TIMEOUT`: Set timeout for STDIO responses in seconds
- `MCP_STDIO_MAX_RETRIES`: Set maximum retries for broken pipes
- `MCP_DOCKER_IMAGE`: Docker image to use for testing
- `MCP_NETWORK_NAME`: Docker network name to use 