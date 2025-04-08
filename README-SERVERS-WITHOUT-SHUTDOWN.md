# Testing MCP Servers Without Shutdown Support

This document provides guidance on testing MCP server implementations that don't support the `shutdown` method using the MCP Protocol Validator.

## Overview

Some MCP server implementations may not support the `shutdown` method defined in the specification. The MCP Protocol Validator has been enhanced to handle these cases gracefully by:

1. Auto-detecting server capabilities
2. Skipping shutdown-related tests
3. Gracefully handling process termination

## How to Use

When testing a server that doesn't support the `shutdown` method:

```bash
# Set any required API keys
export SERVER_API_KEY=your_api_key_here

# Set skip shutdown flag
export MCP_SKIP_SHUTDOWN=true

# Run compliance tests
python -m mcp_testing.scripts.compliance_report \
  --server-command "command-to-start-server" \
  --output-dir "./reports" \
  --skip-shutdown \
  --auto-detect \
  --dynamic-only
```

### Key Options Explained

- `MCP_SKIP_SHUTDOWN=true`: Environment variable that tells the validator to skip shutdown requests
- `--skip-shutdown`: Command line flag that reinforces the skip shutdown behavior
- `--auto-detect`: Automatically detects server-specific settings based on the server command
- `--dynamic-only`: Only runs tests that adapt to the server's capabilities

## Example: Testing Brave Search Server

The Brave Search MCP server is an example of a server that doesn't support the `shutdown` method.

```bash
# Set Brave API key
export BRAVE_API_KEY=your_api_key_here

# Set skip shutdown flag
export MCP_SKIP_SHUTDOWN=true

# Run compliance tests
python -m mcp_testing.scripts.compliance_report \
  --server-command "npx -y @modelcontextprotocol/server-brave-search" \
  --output-dir "./reports" \
  --skip-shutdown \
  --auto-detect \
  --dynamic-only
```

## Understanding Test Results

When using the `--skip-shutdown` flag, the validator will:

1. Skip running the `test_shutdown` and `test_exit_after_shutdown` tests
2. Mark these skipped tests as passed to avoid false compliance failures
3. Not attempt to call the shutdown method during test cleanup
4. Forcefully terminate the server process if needed

## Server-Specific Auto-Detection

The validator now includes a server compatibility module that can auto-detect settings for known servers:

- For Brave Search server:
  - Sets protocol version to 2024-11-05
  - Skips shutdown-related tests
  - Configures expected tools (brave_web_search, brave_local_search)

## Adding Support for New Servers

If you're testing a new server type that doesn't support shutdown, you can:

1. Set the environment variable and use the flags as described above
2. Consider submitting a pull request to enhance the auto-detection for your server type

## Troubleshooting

### Common Issues

1. **Hanging Tests**: If tests seem to hang, ensure you're using both the environment variable and the `--skip-shutdown` flag.

2. **Tool Call Failures**: Some servers may not fully implement error handling for invalid tool calls. This is a common compliance issue.

3. **Process Termination**: If processes remain after tests complete, you may need to manually terminate them with:
   ```bash
   ps aux | grep server-command-name
   kill -9 PID
   ```

## Technical Details

The `MCP_SKIP_SHUTDOWN` environment variable is detected in:
- `mcp_testing/utils/runner.py` - For controlling the test runner behavior
- `mcp_testing/scripts/compliance_report.py` - For configuring test selection 