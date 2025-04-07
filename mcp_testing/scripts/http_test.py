#!/usr/bin/env python3
"""
HTTP Test Script for MCP protocol.

This script runs tests against an MCP server using the HTTP transport.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add root directory to sys.path to import mcp_testing
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from mcp_testing.transports.http import HttpTransportAdapter
from mcp_testing.scripts.compliance_report import run_compliance_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('http_test')


async def main():
    """Run the HTTP test."""
    parser = argparse.ArgumentParser(
        description="Run MCP protocol tests using HTTP transport"
    )
    parser.add_argument(
        "--server-command",
        help="Command to start the server (if not already running)",
        required=False
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="URL of the MCP HTTP server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--protocol-version",
        choices=["2024-11-05", "2025-03-26"],
        default="2025-03-26",
        help="Protocol version to use (default: 2025-03-26)"
    )
    parser.add_argument(
        "--test-mode",
        choices=["spec", "capability"],
        default="spec",
        help="Test mode: spec for specification tests, capability for capability tests (default: spec)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--use-sse",
        action="store_true",
        help="Use Server-Sent Events for notifications"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('mcp_testing').setLevel(logging.DEBUG)
    
    # Create the HTTP transport adapter
    transport = HttpTransportAdapter(
        server_command=args.server_command,
        server_url=args.server_url,
        debug=args.debug,
        use_sse=args.use_sse
    )
    
    # Run the compliance report
    await run_compliance_report(
        transport=transport,
        protocol_version=args.protocol_version,
        test_mode=args.test_mode
    )


if __name__ == "__main__":
    asyncio.run(main()) 