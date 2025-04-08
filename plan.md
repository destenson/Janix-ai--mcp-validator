# Plan for MCP Protocol Validator GitHub Action

## Overview

We'll create a GitHub Action that can be incorporated into any server repository implementing the MCP protocol. This will enable automatic validation against protocol specifications on Pull Requests.

## Implementation Steps

1. **Create GitHub Action Definition**
   - Develop a reusable GitHub Action workflow file in `.github/workflows/`
   - Package the validator as a GitHub Action that can be imported in other repositories

2. **Develop Action Script**
   - Create a flexible setup script that can adapt to different server implementations
   - Add support for both HTTP and STDIO server testing
   - Include configurable parameters for protocol versions and testing modes

3. **Compliance Report Generation**
   - Generate detailed Markdown reports for PR comments
   - Create status badges for README display
   - Store test results as GitHub Action artifacts

4. **Server-Specific Configuration**
   - Support a configuration file for server-specific settings
   - Allow customization of server startup commands and arguments
   - Include options for required tools and test exclusions

5. **Integration Documentation**
   - Create comprehensive documentation for integration steps
   - Include example configurations for common server types
   - Provide troubleshooting guide

## Detailed Implementation Plan

### 1. GitHub Action Definition

Create a GitHub Action definition in `action.yml`:

```yaml
name: 'MCP Protocol Compliance Validator'
description: 'Validate an MCP server implementation against protocol specifications'
author: 'Scott Wilcox'
inputs:
  server-type:
    description: 'Type of MCP server (stdio or http)'
    required: true
    default: 'http'
  server-command:
    description: 'Command to start the server (for stdio servers)'
    required: false
  server-url:
    description: 'URL of the HTTP server (for http servers)'
    required: false
    default: 'http://localhost:8000/mcp'
  protocol-version:
    description: 'Protocol version to test against'
    required: false
    default: '2025-03-26'
  test-mode:
    description: 'Testing mode: all, core, tools, async, spec'
    required: false
    default: 'all'
  server-config:
    description: 'Path to server configuration JSON file'
    required: false
  dynamic-only:
    description: 'Only run dynamic tests that adapt to server capabilities'
    required: false
    default: 'true'
  skip-shutdown:
    description: 'Skip shutdown method for servers that do not implement it'
    required: false
    default: 'false'
  output-dir:
    description: 'Directory to store report files'
    required: false
    default: 'reports'
outputs:
  compliance-score:
    description: 'Compliance score percentage'
  report-path:
    description: 'Path to the generated compliance report'
  status:
    description: 'Test status (success/failure)'
runs:
  using: 'composite'
  steps:
    # Implementation steps will go here
```

### 2. Create Workflow Scripts

Develop a wrapper script that handles both STDIO and HTTP server types:

```python
#!/usr/bin/env python3
# validate_mcp_server.py

import os
import sys
import subprocess
import json
import time

# Server type and parameters
server_type = os.environ.get('INPUT_SERVER-TYPE', 'http')
protocol_version = os.environ.get('INPUT_PROTOCOL-VERSION', '2025-03-26')
output_dir = os.environ.get('INPUT_OUTPUT-DIR', 'reports')
test_mode = os.environ.get('INPUT_TEST-MODE', 'all')
dynamic_only = os.environ.get('INPUT_DYNAMIC-ONLY', 'true') == 'true'
skip_shutdown = os.environ.get('INPUT_SKIP-SHUTDOWN', 'false') == 'true'
server_config = os.environ.get('INPUT_SERVER-CONFIG', '')

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Determine which test script to run based on server type
if server_type.lower() == 'stdio':
    server_command = os.environ.get('INPUT_SERVER-COMMAND', '')
    if not server_command:
        print("Error: Server command must be provided for STDIO servers")
        sys.exit(1)
    
    cmd = [
        'python', '-m', 'mcp_testing.scripts.compliance_report',
        '--server-command', server_command,
        '--protocol-version', protocol_version,
        '--output-dir', output_dir,
        '--test-mode', test_mode
    ]
    
    if dynamic_only:
        cmd.append('--dynamic-only')
    
    if skip_shutdown:
        cmd.append('--skip-shutdown')
    
    if server_config:
        cmd.extend(['--server-config', server_config])
    
elif server_type.lower() == 'http':
    server_url = os.environ.get('INPUT_SERVER-URL', 'http://localhost:8000/mcp')
    
    # Wait for server to be ready
    max_retries = 10
    retry_interval = 3
    for i in range(max_retries):
        try:
            import urllib.request
            urllib.request.urlopen(server_url, timeout=5)
            print(f"Server is ready at {server_url}")
            break
        except Exception as e:
            print(f"Waiting for server to be ready... ({i+1}/{max_retries})")
            if i == max_retries - 1:
                print(f"Error: Could not connect to server at {server_url}")
                sys.exit(1)
            time.sleep(retry_interval)
    
    cmd = [
        'python', '-m', 'mcp_testing.scripts.http_test',
        '--server-url', server_url,
        '--protocol-version', protocol_version,
        '--output-dir', output_dir,
        '--max-retries', '5',
        '--retry-interval', '3'
    ]
    
else:
    print(f"Error: Unknown server type: {server_type}")
    sys.exit(1)

# Run the tests
print(f"Running MCP compliance tests with command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)

# Output the results
print(result.stdout)
if result.stderr:
    print(f"Errors:\n{result.stderr}")

# Parse the compliance score from the output
compliance_score = 0
for line in result.stdout.splitlines():
    if "Compliance Status:" in line and "%" in line:
        try:
            compliance_score = line.split("(")[1].split("%")[0]
            break
        except IndexError:
            pass

# Set the action outputs
with open(os.environ.get('GITHUB_OUTPUT', ''), 'a') as f:
    f.write(f"compliance-score={compliance_score}\n")
    f.write(f"report-path={output_dir}\n")
    f.write(f"status={'success' if result.returncode == 0 else 'failure'}\n")

sys.exit(result.returncode)
```

### 3. Create Example Workflow File

Provide a template `.github/workflows/mcp-compliance.yml` that users can add to their repositories:

```yaml
name: MCP Protocol Compliance

on:
  pull_request:
    branches: [ main, master ]
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  validate-mcp-server:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    # Example step for starting HTTP server (users would modify this)
    - name: Start MCP HTTP Server
      run: |
        pip install -r requirements.txt
        # Replace with actual server start command
        python server.py &
        sleep 5  # Allow server to start
      
    - name: Run MCP Compliance Tests
      id: compliance
      uses: mcp/protocol-validator@v1  # Replace with actual action repo
      with:
        server-type: 'http'
        server-url: 'http://localhost:8000/mcp'
        protocol-version: '2025-03-26'
        dynamic-only: 'true'
    
    - name: Upload Compliance Report
      uses: actions/upload-artifact@v3
      with:
        name: mcp-compliance-report
        path: ${{ steps.compliance.outputs.report-path }}
    
    - name: Comment PR with Compliance Result
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const reportPath = require('path').join(
            process.env.GITHUB_WORKSPACE,
            '${{ steps.compliance.outputs.report-path }}',
            'http_test_report_2025-03-26.md'
          );
          
          let reportContent = '';
          if (fs.existsSync(reportPath)) {
            reportContent = fs.readFileSync(reportPath, 'utf8');
          } else {
            reportContent = 'Report file not found.';
          }
          
          const complianceScore = '${{ steps.compliance.outputs.compliance-score }}';
          const status = '${{ steps.compliance.outputs.status }}';
          
          const comment = `## MCP Protocol Compliance: ${status === 'success' ? '✅' : '❌'}
          
          Compliance Score: ${complianceScore}%
          
          <details>
          <summary>View Full Report</summary>
          
          ${reportContent}
          </details>`;
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### 4. Configuration File Structure

Create a sample configuration file template for server-specific settings:

```json
{
  "server_name": "My MCP Server",
  "required_tools": ["echo", "add", "list_directory"],
  "skip_tests": ["test_async_tools"],
  "custom_settings": {
    "timeout": 30,
    "max_response_time": 5000
  }
}
```

### 5. Integration Documentation

Finally, create a comprehensive README that explains how to use the GitHub Action:

```markdown
# MCP Protocol Validator GitHub Action

This GitHub Action validates MCP (Model Conversation Protocol) server implementations against the official protocol specifications.

## Usage

Add this GitHub Action to your workflow file:

```yaml
- name: Run MCP Compliance Tests
  uses: mcp/protocol-validator@v1
  with:
    server-type: 'http'
    server-url: 'http://localhost:8000/mcp'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| server-type | Type of MCP server (stdio or http) | Yes | http |
| server-command | Command to start the server (for stdio servers) | For stdio | - |
| server-url | URL of the HTTP server (for http servers) | For http | http://localhost:8000/mcp |
| protocol-version | Protocol version to test against | No | 2025-03-26 |
| test-mode | Testing mode (all, core, tools, async, spec) | No | all |
| server-config | Path to server configuration JSON file | No | - |
| dynamic-only | Only run dynamic tests that adapt to server capabilities | No | true |
| skip-shutdown | Skip shutdown method for servers that don't implement it | No | false |
| output-dir | Directory to store report files | No | reports |

## Outputs

| Output | Description |
|--------|-------------|
| compliance-score | Compliance score percentage |
| report-path | Path to the generated compliance report |
| status | Test status (success/failure) |

## Examples

### HTTP Server Example

```yaml
name: MCP Protocol Compliance

on:
  pull_request:
    branches: [ main ]

jobs:
  validate-mcp-server:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Start MCP HTTP Server
      run: |
        npm install
        npm start &
        sleep 5  # Allow server to start
      
    - name: Run MCP Compliance Tests
      id: compliance
      uses: mcp/protocol-validator@v1
      with:
        server-type: 'http'
        server-url: 'http://localhost:8000/mcp'
        protocol-version: '2025-03-26'
```

### STDIO Server Example

```yaml
name: MCP Protocol Compliance

on:
  pull_request:
    branches: [ main ]

jobs:
  validate-mcp-server:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run MCP Compliance Tests
      id: compliance
      uses: mcp/protocol-validator@v1
      with:
        server-type: 'stdio'
        server-command: 'python ./my_mcp_server.py'
        protocol-version: '2025-03-26'
        skip-shutdown: 'true'
```
```

## Benefits of the GitHub Action Approach

1. **Universal Testing**: Any MCP server implementation can be validated against the protocol specification.

2. **Integration with CI/CD**: Automatically test protocol compliance on every PR or push.

3. **Protocol Version Testing**: Ensure compatibility with specific MCP protocol versions.

4. **Detailed Reporting**: Generate comprehensive reports of test results.

5. **Dynamic Adaptation**: Tests adapt to each server's unique tool capabilities rather than enforcing fixed expectations.

6. **Configurable Testing**: Control which parts of the protocol are tested based on server features.

## Conclusion

This plan outlines a comprehensive approach to creating a GitHub Action for MCP protocol compliance testing. The action will make it simple for any repository implementing an MCP server to validate their implementation against the protocol specifications through automated testing on Pull Requests.

By leveraging the existing dynamic testing capabilities of the MCP Protocol Validator, this GitHub Action will be flexible enough to work with any server implementation, regardless of the specific tools it provides or its unique features. The action will generate detailed compliance reports that highlight any areas where the server doesn't meet the protocol specifications. 