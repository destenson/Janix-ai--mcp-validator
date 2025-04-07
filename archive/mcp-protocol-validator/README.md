# MCP Protocol Validator

A tool for validating MCP (Machine-Computer Protocol) server implementations against the protocol specification.

## Features

- Test MCP servers against different protocol versions (2024-11-05, 2025-03-26)
- Support for both HTTP and STDIO transport
- Detailed HTML and JUnit XML reports
- Debug mode for troubleshooting
- Built-in test server for development and testing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mcp-protocol-validator.git
cd mcp-protocol-validator
```

2. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Test an MCP server with HTTP transport:

```bash
python mcp_validator.py test --url http://localhost:8080 --version 2025-03-26
```

Test using STDIO transport with a Docker container:

```bash
python mcp_validator.py test --server-command "docker run -i --rm myserver" --version 2025-03-26
```

### Command-line Options

```
Usage: mcp_validator.py test [OPTIONS]

Options:
  --url TEXT                 URL of the MCP server (for HTTP transport)
  --server-command TEXT      Command to start the server (for STDIO transport)
  --version TEXT             Protocol version to test against. Supported
                             versions: 2024-11-05, 2025-03-26  [required]
  --report TEXT              Path to save the test report
  --format [html|junit]      Report format (html or junit)
  --debug                    Enable debug mode for more verbose output
  --help                     Show this message and exit.
```

### Environment Variables

The validator supports configuration through environment variables:

- `MCP_SERVER_URL`: URL of the MCP server (for HTTP transport)
- `MCP_PROTOCOL_VERSION`: Protocol version to test against
- `MCP_DEBUG_STDIO`: Enable debug mode for STDIO transport (set to "1" or "true")
- `MCP_STDIO_TIMEOUT`: Timeout in seconds for STDIO responses (default: 10.0)
- `MCP_STDIO_MAX_RETRIES`: Maximum number of retries for STDIO communication errors (default: 3)

## Test Server for Development

The repository includes a simple test server implementation that can be used to verify the validator itself or as a reference implementation.

### Running the Test Server

With STDIO transport (default):

```bash
python test_server.py
```

With HTTP transport:

```bash
python test_server.py --http --port 8080
```

### Test Server Options

```
Usage: test_server.py [OPTIONS]

Options:
  --http             Run as HTTP server instead of STDIO
  --port PORT        HTTP server port (default: 8080)
  --version VERSION  Protocol version to implement (default: 2025-03-26)
  --fail-rate N      Make every Nth request fail (default: 0, no failures)
  --delay SEC        Add delay to responses in seconds (default: 0)
  --debug            Enable debug output
  --help             Show this message and exit
```

### Testing with the Test Server

Test the validator against the test server with STDIO transport:

```bash
# In one terminal, run the validator
python mcp_validator.py test --server-command "python test_server.py" --version 2025-03-26 --debug

# Or with Docker
python mcp_validator.py test --server-command "docker run -i --rm -v $(pwd)/test_server.py:/app/test_server.py python:3.9 python /app/test_server.py" --version 2025-03-26 --debug
```

## Testing a STDIO Server with Local Validator

For the most reliable testing of STDIO-based MCP servers, we recommend running the validator locally and the server in Docker. This approach provides better error messages and avoids issues with Docker-to-Docker communication.

### Prerequisites

1. Make sure you have Python 3.11.8 installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a Docker network for isolated testing:
   ```bash
   docker network create mcp-test-network
   ```

### Steps to Test a STDIO Server

1. **Prepare Test Data** (optional):
   ```bash
   # Create a test directory with some sample files
   mkdir -p test_data
   echo "Test file content" > test_data/file1.txt
   mkdir -p test_data/subfolder
   echo "Subfolder content" > test_data/subfolder/file2.txt
   ```

2. **Run the Validator Against the Docker-based STDIO Server**:
   ```bash
   # Run all tests (including HTTP tests which will fail with connection errors)
   python mcp_validator.py test \
     --url http://localhost \
     --server-command "docker run -i --rm --network mcp-test-network \
       --mount type=bind,src=$(pwd)/../test_data,dst=/projects/test_data \
       mcp/filesystem /projects" \
     --report ./compliance-report.html \
     --format html \
     --debug
   ```

   **OR**

   ```bash
   # Run only STDIO-compatible tests (recommended)
   python mcp_validator.py test \
     --url http://localhost \
     --server-command "docker run -i --rm --network mcp-test-network \
       --mount type=bind,src=$(pwd)/../test_data,dst=/projects/test_data \
       mcp/filesystem /projects" \
     --report ./compliance-report.html \
     --format html \
     --debug \
     --stdio-only
   ```

   > **Important Notes**: 
   > - The `--url` parameter is required but not actually used for STDIO transport
   > - The `-i` flag in the Docker command is essential for STDIO transport
   > - The `--stdio-only` flag skips HTTP-specific tests, reducing connection errors in the report
   > - Check the generated HTML report for test results

3. **View Test Results**:
   ```bash
   # Open the HTML report in your browser
   open ./compliance-report.html
   ```

### Understanding STDIO vs. HTTP Tests

When testing with the STDIO transport, there are two approaches:

1. **Run All Tests**: The default behavior runs all tests regardless of transport. This will result in HTTP-specific tests failing with connection errors, but you'll see a complete test suite coverage.

2. **Run STDIO-Compatible Tests Only**: Using the `--stdio-only` flag filters out tests that specifically depend on HTTP features such as status codes, headers, and response formats that aren't directly applicable to STDIO transport.

The STDIO-only mode gives you cleaner test results, focusing only on the core JSON-RPC functionality that works over both transports.

### Troubleshooting STDIO Tests

If you encounter issues with STDIO testing:

1. **Environment Variables**: Set the correct environment variable to help the validator use STDIO transport:
   ```bash
   export MCP_TRANSPORT_TYPE=stdio
   export MCP_SERVER_URL=http://localhost
   ```

2. **Connection Errors**: Many tests will show connection errors - this is expected for HTTP-based tests when using STDIO transport. Use the `--stdio-only` flag to skip these tests.

3. **Lost STDIO Connection**: If you see "broken pipe" errors, it indicates the STDIO connection was interrupted. Try:
   - Running with the `--debug` flag
   - Increasing the timeout: `export MCP_STDIO_TIMEOUT=20.0`

4. **Path Not Found Errors**: If filesystem operations report "Path not found":
   - Check the path mappings in your Docker mount command
   - Ensure the paths match what the server expects (e.g., `/projects/test_data`)
   - Verify file permissions allow the server to access the mounted directories

5. **Recursion Depth Errors**: If you encounter "Maximum recursion depth exceeded" errors:
   - The filesystem server has a limit on how deep it will traverse directories
   - Use more specific paths instead of trying to list very deep directory structures
   - If using the test server, you can increase the limit with `--max-depth` option
   - Typical solutions:
     - Adjust your test data to have a flatter structure
     - Use more targeted operations on specific subdirectories instead of recursive operations
     - Modify server configuration if possible (depends on the server implementation)

6. **Filesystem Server Issues**: For filesystem-specific problems:
   - Ensure mount paths are correct
   - Try different filesystem server images (e.g., `janix-mcp-filesystem-server` instead of `mcp/filesystem`)
   - Check Docker network connectivity

7. **Timeouts**: If operations time out:
   - Increase the timeout values in the environment variables (`MCP_STDIO_TIMEOUT`)
   - Consider running smaller test batches
   - Check if the server is processing large directory structures

## Troubleshooting

### Common Issues

1. **Broken Pipe Errors**: If you see "Broken pipe" errors when using STDIO transport, make sure:
   - You're using the `-i` flag with Docker to keep stdin open
   - The server is properly handling line-buffered JSON-RPC messages
   - Try increasing the timeout with `MCP_STDIO_TIMEOUT=15.0`

2. **HTTP Connection Errors**: For HTTP transport issues:
   - Verify the server is running and accessible at the specified URL
   - Check that the server accepts POST requests with JSON-RPC content

3. **Empty or Incomplete Responses**: If tests fail due to invalid responses:
   - Enable debug mode to see the actual requests and responses
   - Check that the server is implementing the correct protocol version

### Debug Mode

Enable debug mode for detailed logging:

```bash
python mcp_validator.py test --url http://localhost:8080 --version 2025-03-26 --debug
```

Or with environment variables:

```bash
MCP_DEBUG_STDIO=1 python mcp_validator.py test --server-command "docker run -i --rm myserver" --version 2025-03-26
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 