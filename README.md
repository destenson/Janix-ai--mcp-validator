# MCP Protocol Validator

A testing suite and reference implementation for the [Model Conversation Protocol (MCP)](https://github.com/microsoft/aimcp).

## Components

This repository contains:

<<<<<<< Updated upstream
1. **Minimal MCP Server**: A reference implementation of an MCP server using STDIO transport
2. **Minimal HTTP MCP Server**: A reference implementation of an MCP server using HTTP transport
3. **MCP Testing Framework**: A robust testing framework for verifying MCP server implementations against the protocol specifications
=======
- **Comprehensive Tests**: Verifies all essential aspects of the MCP specification
- **Isolated Testing**: Run both your server and the validator in a controlled Docker environment
- **Detailed Reports**: Generate HTML or JSON reports for compliance analysis
- **CI Integration**: GitHub Action for continuous validation
- **Weighted Compliance Scoring**: Prioritizes critical requirements for accurate compliance assessment
>>>>>>> Stashed changes

## Status

The current implementation is fully compliant with the latest MCP protocol specification (2025-03-26).

✅ All tests pass for the reference implementations!

<<<<<<< Updated upstream
## Repository Organization

The repository is organized as follows:

```
.
├── mcp_testing/                # Testing framework
│   ├── bin/                    # Executable scripts
│   ├── http/                   # HTTP testing module
│   ├── protocols/              # Protocol version tests
│   ├── scripts/                # Command-line tools
│   ├── stdio/                  # STDIO testing module
│   ├── transports/             # Transport layer implementations
│   └── utils/                  # Shared utilities
├── minimal_http_server/        # HTTP server reference implementation
├── minimal_mcp_server/         # STDIO server reference implementation
├── reports/                    # Generated test reports
├── schema/                     # JSON Schema definitions
└── specification/              # Protocol specifications
```

Each directory contains its own README with specific documentation.

## Minimal MCP Server (STDIO)

A simple reference implementation of an MCP server that uses STDIO for transport and supports all protocol features:

- Basic protocol operations (initialization, shutdown)
- Synchronous tool calls
- Asynchronous tool calls (for 2025-03-26)
- Utility tools for file system operations

### Running the STDIO Server

```bash
# Run the server
python ./minimal_mcp_server/minimal_mcp_server.py
=======
### Requirements
- Python 3.11.8
- Docker (for containerized testing)

### Build the Docker Image

# Build the validator Docker image locally
docker build -t mcp-validator ./mcp-protocol-validator
>>>>>>> Stashed changes
```

### Supported Tools

The minimal server implements these tools:

- `echo`: Echo input text
- `add`: Add two numbers
- `sleep`: Sleep for specified seconds (useful for testing async operations)
- `list_directory`: List files in a directory
- `read_file`: Read a file
- `write_file`: Write a file

## Minimal HTTP MCP Server

A reference implementation of an MCP server that uses HTTP for transport and supports all protocol features:

- JSON-RPC 2.0 over HTTP implementation
- Support for both MCP protocol versions (2024-11-05 and 2025-03-26)
- Synchronous and asynchronous tool calls
- Resources capability (for 2025-03-26)
- Batch request support
- CORS support for browser clients

### Running the HTTP Server

```bash
# Run the server with default settings (localhost:8000)
python ./minimal_http_server/minimal_http_server.py

<<<<<<< Updated upstream
# Run with custom host and port
python ./minimal_http_server/minimal_http_server.py --host 0.0.0.0 --port 8080
=======
# Create a virtual environment with Python 3.11.8
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r mcp-protocol-validator/requirements.txt
>>>>>>> Stashed changes
```

### HTTP Testing Tools

<<<<<<< Updated upstream
The HTTP server includes testing utilities:

```bash
# Run a basic HTTP test suite
python ./minimal_http_server/test_http_server.py

# Run compliance tests against the HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000 --protocol-version 2025-03-26
=======
### Isolated Testing (Recommended)

The most reliable way to validate your MCP server implementation:

```bash
# 1. Create a Docker network for isolation
docker network create mcp-test-network

# 2. Run your server in Docker with the test network
docker run --rm --name mcp-server --network mcp-test-network \
  -d your-server-image:latest

# 3. Run validator tests against your containerized server
docker run --rm --network mcp-test-network mcp-validator \
  --url http://mcp-server:your-port/mcp \
  --report ./compliance-report.html

# 4. Clean up when done
docker stop mcp-server
docker network rm mcp-test-network
```

This approach:
- Isolates both server and validator in a controlled environment
- Prevents external network interference
- Provides consistent testing results
- Makes it easy to reset for clean testing

### Testing External Servers

Test an MCP server using Docker:

```bash
docker run --rm mcp-validator \
  --url https://your-mcp-server.com/mcp \
  --report ./reports/compliance-report.html
>>>>>>> Stashed changes
```

See the [HTTP Server README](minimal_http_server/README.md) for more details.

## MCP Testing Framework

A flexible testing framework for verifying MCP server compliance with protocol specifications.

### Key Features

- Support for both the 2024-11-05 and 2025-03-26 protocol versions
- Support for both STDIO and HTTP transport protocols
- Dynamic tool testing that adapts to any server's capabilities
- Detailed compliance reporting
- Configurable test modes for targeted functionality testing
- Comprehensive specification requirement testing (MUST, SHOULD, MAY)

### Transport Support

The testing framework supports multiple transport layers:

#### STDIO Testing

For servers that use standard input/output as the transport mechanism:

```bash
<<<<<<< Updated upstream
# Test the minimal STDIO server against the 2025-03-26 specification
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26

# Run only specification requirement tests (MUST, SHOULD, MAY)
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --spec-coverage-only --protocol-version 2025-03-26
=======
docker run --rm mcp-validator \
  --url https://your-mcp-server.com/mcp \
  --test-modules base,resources,tools \
  --report ./reports/compliance-report.html
>>>>>>> Stashed changes
```

#### HTTP Testing

For servers that implement MCP over HTTP:

```bash
<<<<<<< Updated upstream
# Using the dedicated HTTP test script
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26

# Using the executable script in the bin directory
./mcp_testing/bin/http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26
=======
# Test a local server (ensure you're using Python 3.11.8)
cd mcp-protocol-validator
python mcp_validator.py test \
  --url http://localhost:8080 \
  --report ./compliance-report.html
>>>>>>> Stashed changes
```

The HTTP testing module provides specific tests for HTTP-related features like CORS support, session management through headers, and proper HTTP status codes.

### Test Customization Options

<<<<<<< Updated upstream
The framework can be customized for different servers:
=======
```yaml
- name: Set up Python 3.11.8
  uses: actions/setup-python@v2
  with:
    python-version: 3.11.8

- name: Run MCP Compliance Tests
  uses: yourorg/mcp-protocol-validator-action@v1
  with:
    server-url: http://localhost:8080
    test-modules: base,resources,tools,prompts,utilities
```

## Testing Clients

To test MCP clients:
>>>>>>> Stashed changes

```bash
# Test a server with dynamic adaptation to its capabilities
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --dynamic-only --protocol-version 2025-03-26

# Test a specialized server that doesn't implement standard tools or shutdown method
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/specialized/server" --args "/path/to/directory" --skip-shutdown --dynamic-only --protocol-version 2024-11-05
```

<<<<<<< Updated upstream
For HTTP testing, additional options include:

```bash
# Configure connection retries and intervals
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --max-retries 5 --retry-interval 3

# Enable debug output for detailed logging
python -m mcp_testing.scripts.http_test --server-url http://example.com/mcp --debug
```
=======
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
>>>>>>> Stashed changes

### Generating Compliance Reports

The framework generates detailed Markdown reports:

```bash
<<<<<<< Updated upstream
# Generate a compliance report for STDIO server
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --output-dir "./reports"

# Generate a compliance report for HTTP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:8000/mcp --protocol-version 2025-03-26 --output-dir "./reports"
=======
cd mcp-protocol-validator
docker build -t mcp-validator .
```

### Running Internal Tests

```bash
cd mcp-protocol-validator
# Ensure you're using Python 3.11.8
python -m pytest
>>>>>>> Stashed changes
```

Reports include a section on specification coverage, showing how well the server implements all MUST, SHOULD, and MAY requirements from the official protocol specification.

### Programmatic Usage

You can also use the testing modules directly in your Python code:

```python
# For HTTP testing
from mcp_testing.http.tester import MCPHttpTester
from mcp_testing.http.utils import wait_for_server

if wait_for_server("http://localhost:8000/mcp"):
    tester = MCPHttpTester("http://localhost:8000/mcp", debug=True)
    success = tester.run_all_tests()
```

## Extensions and Customization

The framework is designed to be extended:

- Add new test cases for additional protocol features
- Support new protocol versions as they are released
- Create custom test adaptations for specialized server implementations
- Contribute tests for uncovered specification requirements

### Adding HTTP Tests

To add new tests to the HTTP test suite, edit the `mcp_testing/http/tester.py` file and add methods to the `MCPHttpTester` class. Tests should:

1. Return `True` if passing, `False` if failing
2. Print clear error messages
3. Handle exceptions gracefully

Add your test method to the list in the `run_all_tests` method to include it in the full test suite.

See the following documentation for detailed information:
- [MCP Testing README](mcp_testing/README.md) for general testing framework details
- [HTTP Testing README](mcp_testing/http/README.md) for HTTP-specific testing information

## License
<<<<<<< Updated upstream
SPDX-License-Identifier: AGPL-3.0-or-later
Copyright (c) 2025 Scott Wilcox
=======

[GNU AFFERO GENERAL PUBLIC LICENSE](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
>>>>>>> Stashed changes
