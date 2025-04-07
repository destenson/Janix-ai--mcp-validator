# MCP Testing Framework

A comprehensive testing framework for MCP (Model Conversation Protocol) server implementations.

## Overview

This framework allows testing any MCP server implementation against either the 2024-11-05 or 2025-03-26 protocol specifications, using either STDIO or HTTP transport mechanisms.

## Status Update

**✅ All tests now pass successfully for both protocol versions!**

The minimal_mcp_server implementation has been fully tested and validated against all test cases, including the async tool functionality in the 2025-03-26 protocol. The implementation now correctly handles:

- Asynchronous tool calls with `tools/call-async`
- Result retrieval with `tools/result`
- Tool cancellation with `tools/cancel`
- Proper status reporting (running, completed, cancelled)

## Features

- Test MCP servers with either STDIO or HTTP transport
- Support for both 2024-11-05 and 2025-03-26 protocol versions
- Comprehensive test coverage for all protocol features
- Full support for asynchronous tool calls in 2025-03-26
- Modular design for easy extension and customization
- Detailed test reports and summaries
- **NEW**: Markdown compliance reporting

## Installation

1. Clone the repository
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Tests

To run tests against a STDIO MCP server using the 2024-11-05 protocol:

```bash
python -m mcp_testing.scripts.run_stdio_tests --server-command "./path/to/server" --protocol-version 2024-11-05 --debug
```

To test against the 2025-03-26 protocol (including async tool calls):

```bash
python -m mcp_testing.scripts.run_stdio_tests --server-command "./path/to/server" --protocol-version 2025-03-26 --debug
```

### Generating Compliance Reports

To generate a detailed Markdown compliance report:

```bash
python -m mcp_testing.scripts.compliance_report \
  --server-command "./path/to/server" \
  --protocol-version 2025-03-26 \
  --debug
```

This will run all tests against the server and generate a comprehensive compliance report in Markdown format, which includes:
- Overall compliance status and score
- Test results categorized by feature area
- Detailed information about passed and failed tests
- Protocol-specific compliance notes

### Testing the Minimal MCP Server

The repository includes a fully compliant reference implementation in `minimal_mcp_server/`:

```bash
# Test minimal_mcp_server with 2024-11-05 protocol
python -m mcp_testing.scripts.run_stdio_tests --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2024-11-05 --debug

# Test minimal_mcp_server with 2025-03-26 protocol (including async tools)
python -m mcp_testing.scripts.run_stdio_tests --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26 --debug

# Generate a compliance report for minimal_mcp_server
python -m mcp_testing.scripts.compliance_report --server-command "./minimal_mcp_server/minimal_mcp_server.py" --protocol-version 2025-03-26
```

### Options

#### Standard Test Options
- `--server-command`: Command to start the server
- `--protocol-version`: Protocol version to use (2024-11-05 or 2025-03-26)
- `--debug`: Enable debug output
- `--output-file`: File to write results to (in JSON format)
- `--markdown`: Generate a Markdown report (with run_stdio_tests.py)

#### Compliance Report Options
- `--server-command`: Command to start the server
- `--protocol-version`: Protocol version to use (2024-11-05 or 2025-03-26)
- `--output-dir`: Directory to store report files (default: "reports")
- `--report-prefix`: Prefix for report filenames (default: "compliance_report")
- `--json`: Also generate a JSON report
- `--debug`: Enable debug output
- `--skip-async`: Skip async tool tests (for 2025-03-26)

## Protocol Version Differences

### 2024-11-05
- Basic MCP protocol with JSON-RPC messaging
- Synchronous tool calls via tools/call

### 2025-03-26
- All features from 2024-11-05
- Asynchronous tool calls via tools/call-async
- Tool result polling via tools/result
- Tool cancellation via tools/cancel

## Directory Structure

```
mcp_testing/
├── transports/     # Transport adapters
│   ├── base.py     # Base transport adapter
│   └── stdio.py    # STDIO transport adapter
├── protocols/      # Protocol adapters
│   ├── base.py     # Base protocol adapter
│   ├── v2024_11_05.py  # 2024-11-05 protocol adapter
│   └── v2025_03_26.py  # 2025-03-26 protocol adapter
├── tests/          # Test cases
│   ├── base_protocol/  # Base protocol tests
│   │   └── test_initialization.py  # Initialization tests
│   └── features/   # Feature tests
│       ├── test_tools.py  # Tools tests
│       └── test_async_tools.py  # Async tools tests (2025-03-26)
├── utils/          # Utilities
│   ├── runner.py   # Test runner
│   └── reporter.py # Report generation
├── scripts/        # Scripts
│   ├── run_stdio_tests.py   # Run tests against STDIO server
│   └── compliance_report.py # Generate compliance reports
└── README.md       # This file
```

## minimal_mcp_server Reference Implementation

The repository includes a complete reference implementation in the `minimal_mcp_server/` directory:

- Full implementation of both 2024-11-05 and 2025-03-26 protocol versions
- Complete support for async tools in the 2025-03-26 protocol
- Example tools including echo, add, sleep (for testing async functionality), and file operations
- STDIO transport with comprehensive error handling
- Well-documented and easy to understand codebase

This reference implementation can be used as a learning resource or starting point for other MCP server implementations.

## Extending the Framework

### Adding New Test Cases

1. Create a new test module in the appropriate directory
2. Define test functions following the pattern:
   ```python
   async def test_feature(protocol: MCPProtocolAdapter) -> Tuple[bool, str]:
       # Test code here
       return True, "Success message"
   ```
3. Add a `TEST_CASES` list at the end of the file
4. Import and use the test cases in your test script

### Adding Support for a New Protocol Version

1. Create a new protocol adapter in the `protocols` directory
2. Implement all required methods from the base adapter
3. Update the test runner to use the new adapter

### Adding Support for a New Transport Mechanism

1. Create a new transport adapter in the `transports` directory
2. Implement all required methods from the base adapter
3. Update the test runner to use the new adapter

### Customizing Compliance Reports

The reporting functionality in `mcp_testing.utils.reporter` can be extended to support:
- Additional report formats
- Custom categorization of tests
- Integration with CI/CD systems
- Custom compliance criteria

## License

This project is licensed under the MIT License - see the LICENSE file for details. 