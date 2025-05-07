# Contributing to MCP Validator

Thank you for your interest in contributing to the MCP Validator project! This guide will help you get started with the development environment and understand our workflow.

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mcp-validator.git
   cd mcp-validator
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Explore the codebase**
   - See `README.md` for an overview
   - Check `test_procedures.md` for how to run tests
   - Review `report.md` for the current state of the project

## Repository Structure

- `mcp_testing/`: Core testing framework
  - `protocols/`: Protocol version adapters
  - `transports/`: Transport adapters (HTTP, STDIO)
  - `scripts/`: Test scripts and utilities
  - `utils/`: Shared utilities

- `ref_stdio_server/`: Reference STDIO server implementations
  - `stdio_server_2024_11_05.py`: 2024-11-05 protocol version
  - `stdio_server_2025_03_26.py`: 2025-03-26 protocol version

- `ref_http_server/`: HTTP server with SSE transport
  - `fastmcp_server.py`: Main server implementation

- `reports/`: Generated test reports
- `schema/`: JSON schema definitions
- `archive/`: Deprecated code (kept for reference)

## Workflow

1. **Check the TODO list**
   - See `TODO.md` for current tasks and priorities

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Develop and test**
   - Follow the test procedures in `test_procedures.md`
   - Ensure all tests pass before submitting a PR

4. **Submit a pull request**
   - Include a clear description of your changes
   - Reference any related issues

## Testing Guidelines

- All new code should have accompanying tests
- Run both HTTP and STDIO tests to ensure full compatibility
- Generate compliance reports to verify specification adherence

## Code Style

- Follow PEP 8 guidelines for Python code
- Use clear, descriptive variable and function names
- Add docstrings to all functions and classes
- Keep lines to a reasonable length (120 characters max)

## Documentation

- Update README.md when adding new features
- Keep documentation in sync with code changes
- Document public APIs with clear examples

## Need Help?

- Check the existing documentation
- Review test reports for insights
- File an issue for questions or problems

Thank you for contributing to the MCP Validator project! 