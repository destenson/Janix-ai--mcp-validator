# Archived Files

This directory contains files that have been archived from the main repository structure. These files may be deprecated or superseded by newer implementations, but they are preserved here for reference until we're certain they're no longer needed.

## Contents

### Planning Documents
- `planning/plan.md`: Original planning document for the MCP implementation
- `planning/opensource_plan.md`: Open-source planning document

### Scripts
- `scripts/apply_fastmcp_improvements.sh`: Script containing improvements to the FastMCP server (now already applied)
- `scripts/custom_http_tester.py`: Original HTTP test script (superseded by fastmcp_compliance.py)
- `scripts/custom_http_test.py`: Custom HTTP test script (superseded by more comprehensive implementations)
- `scripts/fastmcp_test.py`: Original FastMCP test script (superseded by fastmcp_compliance.py)
- `scripts/http_compliance.py`: HTTP compliance testing script (overlaps with fastmcp_compliance.py)
- `scripts/http_test.py`: Basic HTTP testing script (superseded by fastmcp_compliance.py)
- `scripts/session_test.py`: Session validation script (functionality now in main compliance tests)
- `scripts/http_compliance_report.py`: HTTP-specific compliance report generator (superseded by compliance_report.py)

### Testing 
- `testing/fastmcp_test.py`: Duplicate of the test script from scripts directory

## Reason for Archiving

These files were identified in the repository analysis (see `report.md` in the main directory) as potentially redundant or deprecated. They have been moved here rather than deleted to ensure we don't lose any important functionality during the cleanup process.

Files can be restored to their original locations if needed, or permanently removed once we're confident they're no longer required.

## Most Recently Archived

On 2025-05-06, the following scripts were moved to the archive:
- `mcp_testing/scripts/http_compliance.py`
- `mcp_testing/scripts/http_test.py`
- `mcp_testing/scripts/session_test.py`
- `mcp_testing/scripts/http_compliance_report.py`

These scripts had overlapping functionality with more comprehensive implementations and were consolidated as part of the repository cleanup effort. See `archive_candidates.md` for the detailed analysis. 