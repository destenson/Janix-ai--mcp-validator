# Server Configurations

This directory contains configuration files for MCP servers that can be tested with the compliance toolkit.

## Adding a New Server Configuration

To add support for a new server, create a JSON file with the server's details. The filename should be descriptive, like `server-name.json`.

### Configuration File Format

```json
{
  "name": "Human-readable Server Name",
  "identifiers": ["command-substring1", "command-substring2"],
  "description": "Brief description of the server",
  "environment": {
    "ENV_VAR_NAME1": "Description of what this environment variable is for",
    "ENV_VAR_NAME2": "Description of another required variable"
  },
  "skip_tests": ["test_name1", "test_name2"],
  "required_tools": ["tool_name1", "tool_name2"],
  "recommended_protocol": "2024-11-05"
}
```

### Fields Explanation

- `name`: Human-readable name of the server
- `identifiers`: List of substrings that can identify this server in a command (used for auto-detection)
- `description`: Brief description of the server's purpose
- `environment`: Dictionary of environment variables required by this server
- `skip_tests`: List of test names that should be skipped for this server
- `required_tools`: List of tools that must be available in this server
- `recommended_protocol`: The recommended protocol version for this server

## Environment Variables

There are two ways to provide environment variables for a server:

1. **Direct setting**: Set the variable directly before running the test command
   ```bash
   BRAVE_API_KEY=your_key python -m mcp_testing.scripts.compliance_report ...
   ```

2. **Default values**: Set a default value using the `MCP_DEFAULT_` prefix
   ```bash
   MCP_DEFAULT_BRAVE_API_KEY=default_key python -m mcp_testing.scripts.compliance_report ...
   ```

The system will warn you if a required environment variable is missing.

## Example Configurations

See the existing configuration files in this directory for examples:

- `brave-search.json`: Configuration for the Brave Search MCP server 