# Security Policy

## Supported Versions

We currently provide security updates for the following versions of the MCP Validator:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.0   | :white_check_mark: |

## Reporting a Vulnerability

The MCP Validator team takes security seriously. If you believe you've found a security vulnerability, please follow these steps:

1. **Do not disclose the vulnerability publicly**
2. **Email us directly** at [scott@janix.ai](mailto:scott@janix.ai) with details about the vulnerability
3. Include the following information in your report:
   - Type of issue
   - Full paths of source file(s) related to the issue
   - Location of the affected source code
   - Any special configuration required to reproduce the issue
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue, including how an attacker might exploit it

## Response Process

We are committed to the following response process:

- We will acknowledge receipt of your vulnerability report within 3 business days
- We will provide an initial assessment of the report within 10 business days
- We will keep you informed of our progress throughout the process
- We will notify you when the vulnerability has been fixed

## Security Best Practices

When using the MCP Validator in your own projects, we recommend the following security best practices:

1. **Keep your dependencies updated**: Regularly update the MCP Validator and its dependencies to benefit from security patches
2. **Use caution with file operations**: When using the file operation tools in the MCP servers, be aware of potential security implications in your specific environment
3. **Control network access**: When using the HTTP MCP server, ensure it's only accessible to trusted clients or over secure networks

## Responsible Disclosure

We follow responsible disclosure principles. After a fix has been developed and released, we encourage security researchers to disclose the vulnerability in a responsible manner, giving users time to update their installations. We will credit security researchers who report valid vulnerabilities and work with us through the entire process.


Thank you for helping to keep the MCP Validator and its users secure! 