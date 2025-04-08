# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

# MCP Testing Utilities

This directory contains common utility functions and classes used throughout the MCP testing framework.

## Components

- **runner.py**: Contains test runner functionality to execute test suites against MCP servers
- **reporter.py**: Implements reporting tools to generate test reports in various formats

## Test Runner

The test runner is responsible for executing test cases against MCP servers in a standardized way. It handles:

- Test discovery and filtering
- Test execution and result collection
- Error handling and reporting
- Test timing and performance metrics

Usage example:

```python
from mcp_testing.utils.runner import TestRunner
from mcp_testing.protocols import get_protocol
from mcp_testing.transports.stdio import STDIOTransport

# Create a transport
transport = STDIOTransport("python /path/to/server.py")

# Get protocol
protocol = get_protocol("2025-03-26")

# Create and run test runner
runner = TestRunner(transport, protocol)
results = runner.run_tests(categories=["initialization", "tools"])

# Access results
for test_name, result in results.items():
    print(f"{test_name}: {'PASS' if result.passed else 'FAIL'}")
```

## Reporter

The reporter module generates formatted test reports in different output formats (text, HTML, JSON, Markdown). Features include:

- Summary statistics (pass/fail counts, timing)
- Detailed test results
- Specification compliance reporting
- Visual indicators for pass/fail status

Usage example:

```python
from mcp_testing.utils.reporter import TestReporter
from mcp_testing.utils.runner import TestRunner

# Run tests
runner = TestRunner(transport, protocol)
results = runner.run_tests()

# Generate report
reporter = TestReporter(results)

# Generate different formats
reporter.generate_text_report("report.txt")
reporter.generate_html_report("report.html")
reporter.generate_json_report("report.json")
reporter.generate_markdown_report("report.md")
```

## Adding New Utilities

When adding new utility functions or classes:

1. Determine whether they belong in an existing file or warrant a new file
2. Ensure proper documentation with docstrings
3. Keep single responsibility principle in mind
4. Add appropriate error handling
5. Consider writing tests for the utility functions themselves

If creating a new utility file, follow this structure:

```python
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Brief description of the utility module.
"""

import necessary_modules

def utility_function(param1, param2):
    """
    Description of what the function does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    # Implementation
    pass

class UtilityClass:
    """
    Description of the utility class.
    """
    
    def __init__(self, ...):
        """Initialize the class."""
        pass
        
    def method(self, ...):
        """Description of method."""
        pass
``` 