# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP Testing Scripts

This directory contains utility scripts for testing MCP servers across different transports.

## Scripts Overview

- **compliance_report.py**: Generates detailed compliance reports for MCP servers, comparing their implementation against the protocol specification. Tests for MUST, SHOULD, and MAY requirements.

- **http_test.py**: Command-line interface for running the HTTP testing module. Tests MCP servers that use HTTP as the transport layer.

- **run_stdio_tests.py**: Command-line interface for running tests against STDIO-based MCP servers.

- **basic_interaction.py**: Provides a simple interactive client for basic interaction with MCP servers. Useful for manual testing and exploration of server functionality.

## Usage Examples

### Compliance Report

```bash
# Generate a compliance report for a STDIO server
python -m mcp_testing.scripts.compliance_report --server-command "/path/to/server" --protocol-version 2025-03-26 --output-dir "./reports"
```

### HTTP Testing

```bash
# Test an HTTP MCP server
python -m mcp_testing.scripts.http_test --server-url http://localhost:9000/mcp --debug
```

### STDIO Testing

```bash
# Run tests against a STDIO MCP server
python -m mcp_testing.scripts.run_stdio_tests --server-command "python /path/to/server.py" --debug
```

### Basic Interaction

```bash
# Interactively test a STDIO server
python -m mcp_testing.scripts.basic_interaction --server-command "python /path/to/server.py"

# Interactively test an HTTP server
python -m mcp_testing.scripts.basic_interaction --server-url http://localhost:9000/mcp
```

## Extending the Scripts

These scripts can be extended to support:

1. New protocol versions
2. Additional transport layers 
3. More detailed testing requirements
4. Custom reporting formats

See the main README for details on how to contribute new tests and extensions. 