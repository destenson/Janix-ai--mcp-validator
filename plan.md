# MCP Protocol Validator Enhancement Plan

## Objective
Create a unified, flexible testing framework for MCP servers that supports:
- Both STDIO and HTTP transport protocols
- Multiple protocol versions (2024-11-05 and 2025-03-26)
- Comprehensive test coverage for all MCP features
- Easy configuration and execution

## Current Challenges
1. Inconsistent handling of STDIO vs HTTP testing
2. Multiple overlapping test scripts with different approaches
3. Lack of clear organization for protocol version testing
4. Incomplete test coverage for some MCP features
5. Confusing setup process for users

## Solution Architecture

### 1. Core Components

#### 1.1 Transport Layer
- Create a unified transport interface with concrete implementations for:
  - HTTP client (for testing HTTP servers)
  - STDIO client (for testing servers using stdin/stdout)
  - Docker STDIO client (for testing containerized servers)

#### 1.2 Protocol Version Support
- Implement protocol version adapters for:
  - 2024-11-05 (original specification)
  - 2025-03-26 (with async support)
  - Future versions as needed

#### 1.3 Test Framework
- Organize tests by feature categories:
  - Base protocol (initialization, capabilities)
  - Filesystem operations
  - Tools functionality
  - Resources management
  - Prompts/completions
  - Utilities (logging, progress, etc.)

### 2. Command Line Interface

#### 2.1 Primary Command
```
python mcp_validator.py test [options]
```

#### 2.2 Common Options
- `--transport`: Specify HTTP or STDIO
- `--url`: For HTTP servers
- `--server-command`: For STDIO servers
- `--docker-image`: For containerized servers
- `--protocol-version`: Specify the protocol version to test against
- `--test-modules`: Select specific test modules to run
- `--mount-dir`: Specify directory to mount (for Docker)
- `--report-format`: HTML or JSON output
- `--debug`: Enable detailed logging

#### 2.3 Version Comparison Tool
```
python mcp_validator.py compare --version1 2024-11-05 --version2 2025-03-26 [options]
```

### 3. Implementation Plan

#### Phase 1: Refactor Core Architecture (IN PROGRESS)
1. ✅ Create a unified `MCPTransport` interface with transport-specific implementations
   - ✅ Base abstract `MCPTransport` class
   - ✅ `HTTPTransport` implementation
   - ✅ `STDIOTransport` implementation
   - ✅ `DockerSTDIOTransport` implementation
   - ✅ Basic test script to verify implementations
2. Refactor test base classes to use the client interface
3. Implement protocol version adapters
4. Create consistent configuration handling

#### Phase 2: Test Suite Organization
1. Reorganize tests into logical feature modules
2. Ensure tests are properly tagged for compatibility
3. Implement test skip logic for incompatible combinations
4. Add comprehensive protocol version negotiation tests

#### Phase 3: CLI and Usability Improvements
1. Implement unified command line interface
2. Create comprehensive test reporting
3. Add detailed error handling and diagnostics
4. Update documentation with examples

#### Phase 4: Docker Integration
1. Improve Docker networking setup
2. Add container health checking
3. Support custom Docker images
4. Add test file preparation utilities

### 4. Directory Structure

```
mcp-protocol-validator/
├── mcp_validator.py              # Main entry point
├── compare_protocol_versions.py  # Version comparison tool
├── schema/                       # JSON schemas for protocol versions
│   ├── mcp_schema_2024-11-05.json
│   └── mcp_schema_2025-03-26.json
├── transport/                    # Transport implementations (COMPLETED)
│   ├── __init__.py
│   ├── base.py                   # Transport interface
│   ├── http_client.py
│   ├── stdio_client.py
│   └── docker_client.py
├── protocols/                    # Protocol version adapters
│   ├── __init__.py
│   ├── base.py
│   ├── v2024_11_05.py
│   └── v2025_03_26.py
├── tests/                        # Test modules
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_base.py              # Base test utilities
│   ├── test_base_protocol.py     # Basic protocol tests
│   ├── test_filesystem.py        # Filesystem tests
│   ├── test_tools.py             # Tools tests
│   ├── test_resources.py         # Resources tests
│   ├── test_prompts.py           # Prompts/completions tests
│   └── test_utilities.py         # Utility tests
├── docker/                       # Docker utilities
│   ├── Dockerfile                # Test server Dockerfile
│   └── docker_utils.py           # Docker helper functions
└── utils/                        # Utility functions
    ├── __init__.py
    ├── config.py                 # Configuration handling
    ├── report.py                 # Report generation
    └── logging.py                # Logging utilities
```

### 5. Test Case Organization

Each test module should include:
1. Core functionality tests (required for all versions)
2. Version-specific tests (tagged with appropriate markers)
3. Transport-specific tests (tagged with transport compatibility)

### 6. Documentation

#### 6.1 README Updates
- Installation instructions
- Basic usage examples
- Common configuration scenarios
- Troubleshooting guide

#### 6.2 Protocol Version Guide
- Differences between protocol versions
- Version-specific features and testing requirements
- Migration guide for server implementations

#### 6.3 Transport-Specific Documentation
- HTTP server testing guide
- STDIO server testing guide
- Docker container testing guide

### 7. Success Metrics

1. All tests pass against reference implementations
2. Test coverage > 90% for core protocol features
3. Successful comparison between protocol versions
4. Clear, comprehensive reporting output
5. Ease of use for both basic and advanced scenarios

## Implementation Timeline

1. Phase 1: Refactor Core Architecture (Week 1-2) - IN PROGRESS
2. Phase 2: Test Suite Organization (Week 3)
3. Phase 3: CLI and Usability Improvements (Week 4)
4. Phase 4: Docker Integration and Final Testing (Week 5)

## Deliverables

1. Unified MCP validator framework
2. Comprehensive test suite
3. Protocol version comparison tool
4. Enhanced documentation
5. Docker integration utilities

## Progress Update (Current Date)

### Completed
- ✅ Defined the unified architecture and project structure
- ✅ Created the transport layer with abstract interface
- ✅ Implemented HTTP, STDIO, and Docker transport clients
- ✅ Verified transport implementations with test script

### In Progress
- Protocol version adapters
- Refactoring test base classes

### Next Steps
1. Create the protocol version adapters to handle different MCP protocol versions
2. Refactor the test base classes to use our new transport layer
3. Create a configuration system for handling test options consistently
4. Begin reorganizing tests into the new modular structure 