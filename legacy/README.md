# Legacy MCP Test Scripts

This directory contains legacy test scripts from earlier versions of the MCP Protocol Validator.

## Deprecation Notice

These scripts are **deprecated** and maintained only for backward compatibility. They will be removed in a future release. Please use the new unified test framework in the `tests/` directory instead.

## Script Overview

| Script | Purpose | Replacement |
|--------|---------|-------------|
| `test_protocols.py` | Tests protocol version adapters | `tests/test_protocol_negotiation.py` |
| `test_tool_invocation.py` | Tests basic tool invocation | `tests/test_tools.py` |
| `test_transport.py` | Tests transport layer implementations | Transport adapters in `tests/transports/` |
| `stdio_test.py` | Basic STDIO transport tests | STDIO transport in unified framework |
| `stdio_direct_test.py` | Direct STDIO testing without Docker | Unified framework with `--transport stdio` |
| `stdio_docker_test.py` | STDIO testing with Docker containers | Unified framework with `--transport docker` |
| `stdio_test_wrapper.py` | Wrapper utility for STDIO tests | Not needed in new framework |
| `direct_mcp_test.py` | Direct testing of MCP protocol | New test modules in `tests/` |
| `mcp_direct_test.py` | Another approach to direct MCP testing | New test modules in `tests/` |
| `mcp_stdio_test.py` | STDIO-specific MCP protocol tests | Unified STDIO transport support |
| `simple_stdio_test.py` | Simplified STDIO testing | Unified framework with simplified commands |

## Migration Guide

To migrate from these legacy scripts to the new unified framework:

1. For tool testing:
   ```bash
   # Old approach
   python legacy/test_tool_invocation.py
   
   # New approach
   ./run_validator.py --test-module test_tools
   ```

2. For STDIO testing:
   ```bash
   # Old approach
   python legacy/stdio_test.py
   
   # New approach
   ./run_validator.py --transport stdio --server-command "python your_server.py"
   ```

3. For Docker testing:
   ```bash
   # Old approach
   python legacy/stdio_docker_test.py
   
   # New approach
   ./run_validator.py --transport docker --docker-image mcp-stdio-server
   ```

For more detailed information about the legacy scripts and how they relate to the new framework, see [Legacy Tests Documentation](../docs/legacy_tests.md). 