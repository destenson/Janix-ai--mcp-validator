# Contributing to MCP Protocol Validator

Thank you for considering contributing to the MCP Protocol Validator! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. Any form of harassment or disrespectful behavior will not be tolerated.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion for improvement:

1. Check if the issue already exists in the [GitHub Issues](https://github.com/your-username/mcp-protocol-validator/issues)
2. If not, create a new issue using the appropriate template
3. Provide as much detail as possible, including steps to reproduce, expected behavior, and your environment

### Submitting Changes

1. Fork the repository
2. Create a new branch for your changes (`git checkout -b feature/your-feature-name`)
3. Make your changes
4. Run tests to ensure your changes don't break existing functionality
5. Commit your changes with a descriptive commit message
6. Push your branch to your fork
7. Submit a pull request to the main repository

### Pull Request Process

1. Ensure your code follows the project's coding style
2. Update documentation as necessary
3. Include tests for new functionality
4. Link any relevant issues in your pull request description
5. Your pull request will be reviewed by maintainers who may request changes

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Unix/MacOS: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run tests: `pytest`

## Testing

All changes should include appropriate tests:

- Unit tests for utility functions
- Integration tests for protocol handling
- End-to-end tests for server interaction

Run the test suite with `pytest` before submitting changes.

## Adding New Features

### Supporting New Protocol Versions

To add support for a new MCP protocol version:

1. Create a new protocol adapter in `mcp_testing/protocols/`
2. Update the test cases to include tests for the new protocol version
3. Update the server implementations to support the new protocol

### Adding New Transport Mechanisms

To add support for a new transport mechanism:

1. Create a new transport adapter in `mcp_testing/transports/`
2. Implement the required interface methods
3. Add tests for the new transport mechanism

## Style Guide

- Follow PEP 8 for Python code
- Use descriptive variable names
- Include docstrings for all modules, classes, and functions
- Keep functions small and focused on a single responsibility

## License

By contributing to this project, you agree that your contributions will be licensed under the project's AGPL-3.0 license. 