# Scripts to Archive

Based on analysis of the `mcp_testing/scripts` directory, here are files that can be moved to the archive:

## 1. Redundant HTTP Testing Scripts

- **`http_compliance.py`** - This appears to overlap with `fastmcp_compliance.py` and has very similar functionality. The HTTP testing is now primarily handled by `fastmcp_compliance.py` which is more comprehensive.

- **`http_test.py`** - This is a simpler version of HTTP testing which has been superseded by `fastmcp_compliance.py`. It uses older testing modules and lacks many of the more recent features.

## 2. Specialized Scripts with Limited Use

- **`session_test.py`** - This is a specialized script for testing session handling in HTTP servers. Its functionality has likely been integrated into the main compliance testing framework.

## 3. Overlap with Established Scripts

- **`http_compliance_report.py`** - This appears to generate HTTP-specific compliance reports, but its functionality has been incorporated into the more generic `compliance_report.py` which handles both HTTP and STDIO testing.

## Reasons for Archive Recommendations:

1. **Functional Overlap**: The scripts identified have significant functionality overlap with more comprehensive and maintained scripts.

2. **Consolidated Testing**: The testing framework has evolved to use more centralized and consistent testing approaches.

3. **Simplified Script Ecosystem**: Having fewer, more comprehensive scripts is easier to maintain and document than many specialized scripts.

## Scripts to Keep:

1. **`fastmcp_compliance.py`** - Primary tool for testing HTTP servers with SSE transport.

2. **`compliance_report.py`** - Comprehensive compliance reporting tool that works across transport types.

3. **`run_stdio_tests.py`** - Essential for testing STDIO server implementations.

4. **`basic_interaction.py`** - Useful for manual/interactive testing of MCP servers.

## Implementation Plan:

1. Move identified scripts to `archive/scripts/` directory
2. Update any documentation that references these scripts
3. Ensure no regression in testing capabilities 