#!/usr/bin/env python3
"""
SSE MCP Server Compliance Test Runner

This script wraps the sse_testing_client.py to provide a user-friendly CLI for running compliance tests
against any HTTP/SSE MCP server and generating a Markdown report in the reports/ directory.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Import the SSE compliance tester
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sse.sse_testing_client import MCPSSEComplianceTester

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

def generate_markdown_report(reports, server_url, protocol_version, output_file):
    total = len(reports)
    passed = sum(1 for r in reports if r.result.value == "PASS")
    failed = sum(1 for r in reports if r.result.value == "FAIL")
    skipped = sum(1 for r in reports if r.result.value == "SKIP")
    warned = sum(1 for r in reports if r.result.value == "WARN")
    compliance = (passed / total) * 100 if total > 0 else 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# SSE MCP Server Compliance Report\n",
        f"**Server URL:** `{server_url}`  ",
        f"**Protocol Version:** `{protocol_version}`  ",
        f"**Test Date:** {now}\n",
        f"## Summary\n",
        f"- **Total Tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        f"- **Skipped:** {skipped}",
        f"- **Warnings:** {warned}",
        f"- **Compliance:** {compliance:.1f}%\n",
        f"## Detailed Results\n",
        "| Test | Result | Message | Time (s) |",
        "|------|--------|---------|----------|",
    ]
    for r in reports:
        lines.append(f"| {r.name} | {r.result.value} | {r.message.replace('|', ' ')} | {r.elapsed_time:.2f} |")
    lines.append("")
    if failed > 0:
        lines.append("## Failed Tests\n")
        for r in reports:
            if r.result.value == "FAIL":
                lines.append(f"- **{r.name}**: {r.message}")
    with open(output_file, "w") as f:
        f.write("\n".join(lines))
    print(f"\nMarkdown compliance report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Run compliance tests against an HTTP/SSE MCP server.")
    parser.add_argument("--server-url", required=True, help="URL of the MCP HTTP/SSE server (e.g. http://localhost:8085/mcp)")
    parser.add_argument("--protocol-version", default="2025-03-26", choices=["2025-03-26", "2024-11-05"], help="Protocol version to use")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for each test (seconds)")
    parser.add_argument("--report-file", help="Filename for the Markdown report (default: auto-generated)")
    args = parser.parse_args()

    # Auto-generate report filename if not provided
    if args.report_file:
        report_path = Path(args.report_file)
    else:
        safe_url = args.server_url.replace('://', '_').replace('/', '_').replace(':', '_')
        report_path = REPORTS_DIR / f"sse_compliance_{safe_url}_{args.protocol_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    # Run the compliance tests
    async def run():
        tester = MCPSSEComplianceTester(
            server_url=args.server_url,
            protocol_version=args.protocol_version,
            timeout=args.timeout
        )
        reports = await tester.run_tests()
        generate_markdown_report(reports, args.server_url, args.protocol_version, report_path)
        # Print summary to stdout
        total = len(reports)
        passed = sum(1 for r in reports if r.result.value == "PASS")
        failed = sum(1 for r in reports if r.result.value == "FAIL")
        print(f"\nSummary: {passed}/{total} tests passed. {failed} failed.")
        if failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    asyncio.run(run())

if __name__ == "__main__":
    main() 