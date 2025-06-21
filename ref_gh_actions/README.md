# Reference GitHub Actions Templates

This directory contains reference GitHub Actions workflow templates for validating MCP server implementations. These templates are meant to be copied into your own MCP server repository and customized as needed.

## 🚀 Quick Start

### For HTTP-based MCP Servers:
1. Copy `http-validation.yml` to your repo's `.github/workflows/` directory
2. Update line 58: Change `SERVER_PATH="path/to/your/http_server.py"` to your actual server file
3. Commit and push - validation runs automatically on PRs!

### For STDIO-based MCP Servers:
1. Copy `stdio-validation.yml` to your repo's `.github/workflows/` directory  
2. Update line 42: Change `SERVER_PATH="path/to/your/stdio_server.py"` to your actual server file
3. Commit and push - validation runs automatically on PRs!

### Example Server Paths:
```yaml
# If your server is in the root directory
SERVER_PATH="server.py"

# If your server is in a subdirectory
SERVER_PATH="src/mcp_server.py"

# If your server needs arguments
python "$SERVER_PATH" --config config.json --port "$SERVER_PORT"
```

## Available Templates

- `stdio-validation.yml` - Template for validating STDIO-based MCP servers
- `http-validation.yml` - Template for validating HTTP-based MCP servers

## Features

- Automated validation on pull requests
- Manual trigger option
- Multi-protocol version testing (2025-03-26, 2025-06-18)
- Detailed test reporting with protocol-specific features
- PR comment summaries with 2025-06-18 feature support
- Artifact storage for test reports
- Error handling and server health checks
- Environment variable support
- OAuth 2.1 authentication support for 2025-06-18

## Step-by-Step Setup Guide

### 1. Choose Your Template
- **HTTP servers**: Use `http-validation.yml` if your server runs on HTTP/REST
- **STDIO servers**: Use `stdio-validation.yml` if your server uses stdin/stdout communication

### 2. Copy the Template
```bash
# Create workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy the appropriate template
cp path/to/mcp-validator/ref_gh_actions/http-validation.yml .github/workflows/
# OR
cp path/to/mcp-validator/ref_gh_actions/stdio-validation.yml .github/workflows/
```

### 3. Customize the Template
Edit the copied file and update these key sections:

#### Required Changes:
```yaml
# Update this line with your actual server path
SERVER_PATH="your/server/path.py"  # Change this!

# For HTTP servers, also update startup command if needed
python "$SERVER_PATH" --port "$SERVER_PORT" &  # Customize as needed
```

#### Optional Changes:
```yaml
# Test different protocol versions
protocol-version: ["2025-03-26", "2025-06-18"]  # Add/remove versions

# Add environment variables your server needs
env:
  API_KEY: ${{ secrets.API_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  OAUTH_TOKEN: ${{ secrets.OAUTH_TOKEN }}  # For 2025-06-18 OAuth testing
```

### 4. Set Up Secrets (if needed)
For 2025-06-18 OAuth testing or server-specific configuration:
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets like:
   - `OAUTH_TOKEN` - Bearer token for OAuth 2.1 authentication
   - `API_KEY` - Your server's API key
   - Any other sensitive configuration

### 5. Commit and Test
```bash
git add .github/workflows/
git commit -m "Add MCP protocol validation"
git push
```

The validation will run automatically on your next pull request!

## Template Customization

### Common Settings
- Protocol versions in matrix strategy (now includes 2025-06-18)
- Python version (updated to 3.12)
- Test timeouts
- Environment variables

### STDIO-specific
- Server command and path
- CLI arguments updated to use `mcp_testing.stdio.cli`
- Test mode options
- Tool selection

### HTTP-specific
- Server port and startup arguments
- Health check settings with fallback endpoints
- Startup retry settings
- CLI arguments updated to use `mcp_testing.http.cli`
- OAuth 2.1 token configuration for 2025-06-18

## Protocol Version Support

### 2025-03-26
- Basic MCP protocol validation
- Tool functionality testing
- Standard error handling

### 2025-06-18 (Latest)
- All 2025-03-26 features
- **OAuth 2.1 authentication** - Set `OAUTH_TOKEN` environment variable
- **Structured tool output** - Enhanced tool response validation
- **Batch request rejection** - Server-side batch processing controls
- **Elicitation support** - Interactive request handling
- Enhanced error handling and reporting

## Environment Variables

### Required for 2025-06-18 OAuth Testing
```yaml
env:
  OAUTH_TOKEN: ${{ secrets.OAUTH_TOKEN }}  # Bearer token for authentication
```

### Optional Configuration
```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}          # Server-specific API keys
  SERVER_PORT: 8088                       # HTTP server port
  TEST_TIMEOUT: 30                        # Test timeout in seconds
```

## Common Customizations

### Testing Multiple Python Versions
```yaml
strategy:
  matrix:
    protocol-version: ["2025-03-26", "2025-06-18"]
    python-version: ['3.10', '3.11', '3.12']  # Uncomment and customize
```

### Custom Server Startup
```yaml
# For servers that need special startup commands
python "$SERVER_PATH" --config production.json --workers 4 --port "$SERVER_PORT" &

# For servers that need environment setup
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python "$SERVER_PATH" &
```

### Skip Specific Tests
```yaml
# Add these flags to the CLI command
--skip-tests test1,test2      # Skip specific tests
--skip-async                  # Skip async tool testing
--required-tools tool1,tool2  # Test only specific tools
```

## Best Practices

1. **Security**: Always use GitHub secrets for sensitive data (OAuth tokens, API keys)
2. **Timeouts**: Set appropriate timeouts based on your server's response times
3. **Error Handling**: Include proper cleanup and error reporting
4. **Health Checks**: Use multiple health check endpoints for HTTP servers
5. **Artifacts**: Keep test artifacts for debugging failed runs
6. **Protocol Testing**: Test against multiple protocol versions for compatibility
7. **OAuth 2.1**: For 2025-06-18, ensure your server supports Bearer token authentication

## Troubleshooting

### Common Issues:

**Server not found:**
```
Error: Server file not found at path/to/server.py
```
→ Update `SERVER_PATH` to the correct path

**Server startup timeout:**
```
Error: Server failed to start after 30 attempts
```
→ Increase `MAX_RETRIES` or check server startup requirements

**Permission denied:**
```
Permission denied: server.py
```
→ The template runs `chmod +x "$SERVER_PATH"` automatically, but ensure your server file is executable

**OAuth authentication failed:**
```
401 Unauthorized
```
→ Set up `OAUTH_TOKEN` secret for 2025-06-18 testing

## Migration from Older Templates

If you're updating from older templates:

1. **Update protocol versions**: Add "2025-06-18" to the matrix
2. **Update CLI commands**: 
   - STDIO: `mcp_testing.stdio.cli` instead of `compliance_report`
   - HTTP: `mcp_testing.http.cli` instead of `http_compliance_test`
3. **Add OAuth support**: Include `OAUTH_TOKEN` environment variable if needed
4. **Update Python version**: Consider upgrading to Python 3.12

## Example PR Comment Output

The templates will generate PR comments like:

```
## MCP HTTP Validation Results (2025-06-18)

- Protocol Version: 2025-06-18
- Success Rate: 100%
- Tests Run: 12
- OAuth 2.1 Support: ✅
- Structured Tool Output: ✅
- Batch Request Rejection: ✅
- Elicitation Support: ✅
```

## Need Help?

- Check the [MCP Validator repository](https://github.com/janix-ai/mcp-validator) for documentation
- Look at the comments in each template file for detailed customization instructions
- Open an issue if you encounter problems with the validation templates 