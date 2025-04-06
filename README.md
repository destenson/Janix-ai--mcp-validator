# MCP Protocol Validator

A comprehensive testing tool for validating Model Context Protocol (MCP) server and client implementations.

## Overview

The MCP Protocol Validator is a containerized test suite designed to ensure compliance with the Model Context Protocol specification. It provides:

- **Comprehensive Tests**: Verifies all essential aspects of the MCP specification
- **Isolated Testing**: Run both your server and the validator in a controlled Docker environment
- **Detailed Reports**: Generate HTML or JSON reports for compliance analysis
- **CI Integration**: GitHub Action for continuous validation
- **Weighted Compliance Scoring**: Prioritizes critical requirements for accurate compliance assessment
- **Multi-transport Support**: Test both HTTP and STDIO transport implementations

## Features

- **Base Protocol Tests**: Initialization, capabilities, JSON-RPC compliance
- **Resources Tests**: List and read operations for resources
- **Tools Tests**: Discovery and invocation of tools
- **Prompts Tests**: Listing and retrieval of prompts
- **Utilities Tests**: Ping, cancellation, progress, logging, and more
- **Client Tests**: Roots and sampling features

## Installation

### Download Repository (Recommended)

```bash
# Clone the repository
git clone https://github.com/Janix-ai/mcp-protocol-validator.git
cd mcp-protocol-validator

# Build the validator Docker image locally
docker build -t mcp-validator .
```

### Using Pre-built Docker Image

```bash
docker pull Janix-ai/mcp-protocol-validator:latest
```

### From Source

```bash
git clone https://github.com/Janix-ai/mcp-protocol-validator.git
cd mcp-protocol-validator

# Create a virtual environment with Python 3.11.8
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Isolated Testing (HTTP Transport)

The reliable way to validate your HTTP-based MCP server implementation:

```bash
# 1. Create a Docker network for isolation
docker network create mcp-test-network

# 2. Run your MCP server implementation in Docker with the test network
# Replace 'your-server-image:latest' with your actual MCP server Docker image
docker run --rm --name mcp-server --network mcp-test-network \
  -d your-server-image:latest

# 3. Run the validator against your containerized MCP server
docker run --rm --network mcp-test-network mcp-validator \
  test \
  --url http://mcp-server:your-port/mcp \
  --report ./compliance-report.html \
  --format html

# 4. Clean up when done
docker stop mcp-server
docker network rm mcp-test-network
```

This approach:
- Isolates both server and validator in a controlled environment
- Prevents external network interference
- Provides consistent testing results
- Makes it easy to reset for clean testing

### STDIO Transport Testing

For testing MCP servers that implement the STDIO transport mechanism:

```bash
# 1. Create a Docker network for isolation
docker network create mcp-test-network

# 2. Test a STDIO-based server using the server-command parameter
# The validator will launch your server and communicate via stdin/stdout
docker run --rm --network mcp-test-network mcp-validator \
  test \
  --url http://localhost \
  --server-command "your-server-launch-command" \
  --report ./compliance-report.html \
  --format html

# 3. Clean up when done
docker network rm mcp-test-network
```

> **Important Note**: Although we're testing via STDIO transport, the validator still requires the `--url` parameter with a valid URL format. Use `http://localhost` as a placeholder; it won't actually be used for communication. The `--server-command` parameter is what initiates STDIO-based testing.

#### How STDIO Testing Works

In this approach:
- The validator launches your server as a subprocess using the `--server-command` parameter
- Communication happens over stdin/stdout as per STDIO transport specification
- The validator handles all the necessary plumbing for STDIO-based testing
- Your server must read JSON-RPC messages from stdin and write responses to stdout

#### Example: Testing a Filesystem MCP Server

Here's a specific example for testing a filesystem-based MCP server with bound volumes:

```bash
docker run --rm --network mcp-test-network mcp-validator \
  test \
  --url http://localhost \
  --server-command "docker run -i --rm --network mcp-test-network \
    --mount type=bind,src=/Users/username/Desktop,dst=/projects/Desktop \
    --mount type=bind,src=/path/to/other/allowed/dir,dst=/projects/other/allowed/dir,ro \
    --mount type=bind,src=/path/to/file.txt,dst=/projects/path/to/file.txt \
    mcp/filesystem /projects" \
  --report ./compliance-report.html \
  --format html
```

> **Note**: The `-i` flag in the server command is essential as it keeps stdin open, which is required for STDIO transport.

Replace the mount paths and target directories with your actual configuration.

### Testing External Servers

Test your MCP server implementation using Docker:

```bash
# Replace the URL with your actual MCP server endpoint
docker run --rm mcp-validator \
  test \
  --url https://your-mcp-server.com/mcp \
  --report ./reports/compliance-report.html \
  --format html
```

Test specific modules:

```bash
# Replace the URL with your actual MCP server endpoint
docker run --rm mcp-validator \
  test \
  --url https://your-mcp-server.com/mcp \
  --test-modules base,resources,tools \
  --report ./reports/compliance-report.html \
  --format html
```

### Local Development

```bash
# Test a local server (ensure you're using Python 3.11.8)
cd mcp-protocol-validator
python mcp_validator.py test \
  --url http://localhost:8080 \
  --report ./compliance-report.html \
  --format html
```

### GitHub Actions Integration

Add the following to your workflow file:

```yaml
- name: Set up Python 3.11.8
  uses: actions/setup-python@v2
  with:
    python-version: 3.11.8

- name: Run MCP Compliance Tests
  uses: Janix-ai/mcp-protocol-validator-action@v1
  with:
    server-url: http://localhost:8080
    test-modules: base,resources,tools,prompts,utilities
```

## Testing Clients

To test MCP clients:

```bash
# Set environment variables for client testing
export MCP_CLIENT_URL=http://localhost:8766
export MOCK_MCP_SERVER=1

# Run client tests
cd mcp-protocol-validator
python -m pytest tests/test_roots.py tests/test_sampling.py -v
```

## Compliance Scoring System

The validator uses a weighted scoring system to accurately reflect the importance of different requirements:

| Requirement Level | Weight | Impact | Severity |
|-------------------|--------|--------|----------|
| MUST (M-prefixed) | 10 | 80% | 🔴 Critical |
| SHOULD (S-prefixed) | 3 | 15% | 🟠 Medium |
| MAY (A-prefixed) | 1 | 5% | 🟢 Low |

This weighting ensures that failing critical requirements has a significantly larger impact on the compliance score than failing optional ones. The overall compliance score is calculated using:

```
ComplianceScore = (10*MustPassed + 3*ShouldPassed + 1*MayPassed) / (10*TotalMust + 3*TotalShould + 1*TotalMay) * 100
```

Based on the calculated score, implementations are classified into one of these compliance levels:

- **Fully Compliant** (100%): Passes all MUST requirements
- **Substantially Compliant** (90-99%): Passes most MUST requirements with minor issues
- **Partially Compliant** (75-89%): Has significant compliance issues
- **Minimally Compliant** (50-74%): Major interoperability concerns
- **Non-Compliant** (<50%): Unlikely to be interoperable

For more details, see [Compliance Scoring](docs/compliance-scoring.md).

## Troubleshooting

### Transport Compatibility

The MCP Protocol Validator is designed to work with servers implementing either transport mechanism:

- **HTTP Transport**: The default testing mode, activated by providing the `--url` parameter without a `--server-command`.
- **STDIO Transport**: Activated by providing both `--url` and `--server-command` parameters. The validator will spawn your server as a subprocess and communicate via stdin/stdout.

If you're having issues:

1. **Check for MCP Server Environment Variable**: Make sure `MCP_SERVER_URL` is properly set when using the validator. For STDIO testing, you might need to use:
   ```bash
   export MCP_SERVER_URL=http://localhost
   ```

2. **Examine the Generated Report**: Even if tests fail with connection errors, the HTML report might still contain useful information about which tests were attempted.

3. **Alternate Approach**: You might need to run the validator directly (not in Docker) for STDIO testing:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python mcp_validator.py test --url http://localhost --server-command "your-server-command"
   ```

4. **Debug Transport Issues**: If you're experiencing connection problems, try:
   - For HTTP: Check the server logs and ensure the server is accepting connections on the specified URL
   - For STDIO: Add debugging output to stderr in your server to diagnose communication issues

5. **Test Order**: We recommend testing with HTTP transport first if your server supports it, as it's easier to debug and provides clearer error messages. Once HTTP transport is working, you can test STDIO transport.

We're working to improve STDIO transport testing in future releases.

## Reports

Reports are generated in the format specified by the `--format` option:

- **HTML**: Interactive report with detailed test results
- **Markdown**: Simple text-based report
- **JSON**: Structured data for programmatic analysis

Each report includes:
- Overall compliance score and level
- Breakdown by requirement type (MUST, SHOULD, MAY)
- Section-by-section compliance details
- Failed tests categorized by severity
- Prioritized remediation plan
- Performance metrics (where available)

See a [sample report](docs/updated-sample-report.md) for an example.

## Development

### Requirements
- Python 3.11.8
- Docker (for containerized testing)

### Building the Docker Image

```bash
cd mcp-protocol-validator
docker build -t mcp-validator .
```

### Running Internal Tests

```bash
cd mcp-protocol-validator
# Ensure you're using Python 3.11.8
python -m pytest
```

## Specification Compliance

The test suite is based on the Model Context Protocol specification version 2025-03-26 and covers:

- **MUST** requirements: Essential for compliance (89 requirements)
- **SHOULD** requirements: Recommended practices (30 requirements)
- **MAY** requirements: Optional features (26 requirements)

## License

[GNU AFFERO GENERAL PUBLIC LICENSE](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Troubleshooting

### STDIO Transport Issues

When testing STDIO-based servers, you might encounter errors like:

```
requests.exceptions.MissingSchema: Invalid URL 'http://localhost': No scheme supplied. Perhaps you meant https://http://localhost?
```

or

```
requests.exceptions.ConnectionError: Connection refused
```

These errors occur because parts of the validator may still attempt to use HTTP requests even when STDIO transport is intended. Some potential workarounds:

1. **Check for MCP Server Environment Variable**: Make sure `MCP_SERVER_URL` is properly set when using the validator. For STDIO testing, you might need to use:
   ```bash
   export MCP_SERVER_URL=http://localhost
   ```

2. **Examine the Generated Report**: Even if tests fail with connection errors, the HTML report might still contain useful information about which tests were attempted.

3. **Alternate Approach**: You might need to run the validator directly (not in Docker) for STDIO testing:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python mcp_validator.py test --url http://localhost --server-command "your-server-command"
   ```

We're working to improve STDIO transport testing in future releases.