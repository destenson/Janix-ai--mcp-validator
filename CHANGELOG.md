# Changelog

All notable changes to the MCP Protocol Validator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- Support for testing MCP protocol versions 2024-11-05 and 2025-03-26
- Minimal reference implementation for STDIO transport
- Minimal reference implementation for HTTP transport
- Comprehensive test suite for protocol compliance
- Dynamic tool testing
- Timeout handling for problematic servers
- Detailed compliance reporting
- Support for pip-installed MCP servers

### Changed
- Improved timeout handling for problematic servers
- Enhanced reporting format with more detailed diagnostics
- Streamlined test execution with better progress indicators

### Fixed
- Properly handle servers that don't implement shutdown method
- Timeout gracefully for servers with tool list issues
- Correctly display status for skipped tests in reports 