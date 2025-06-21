#!/usr/bin/env python3
"""
MCP HTTP Compliance Test

A comprehensive compliance testing tool for MCP HTTP/SSE servers.
This script follows the MCP specification exactly to test server implementations.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    import httpx
    from httpx_sse import EventSource
except ImportError:
    print("Error: Required dependencies not found. Please install with:")
    print("pip install httpx httpx-sse")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mcp-http-tester")

# Constants
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

class TestResult:
    """Test result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"

class TestReport:
    """Test report class"""
    def __init__(self, name, result, message, details=None, elapsed_time=0.0):
        self.name = name
        self.result = result
        self.message = message
        self.details = details or {}
        self.elapsed_time = elapsed_time

class MCPHttpTester:
    """MCP HTTP/SSE Server Compliance Tester"""
    
    def __init__(self, server_url, protocol_version="2025-03-26", timeout=30, debug=False):
        """Initialize the tester"""
        # Ensure server_url doesn't end with slash
        self.server_url = server_url.rstrip('/')
        self.protocol_version = protocol_version
        self.timeout = timeout
        self.debug = debug
        self.session_id = None
        self.reports = []
        
        if debug:
            logger.setLevel(logging.DEBUG)
        
        # Define possible endpoints - prioritize SDK default paths
        self.endpoints = [
            f"{self.server_url}/mcp",           # SDK default message_path
            self.server_url,                    # Primary URL
            f"{self.server_url}/mcp",      # MCP endpoint
            f"{self.server_url}/mcp/",     # MCP endpoint with trailing slash
        ]
        
        # Also try with trailing slash for SDK path
        self.endpoints.insert(1, f"{self.server_url}/mcp/")
        
        # Also try without paths if URL includes path
        url_parts = self.server_url.split('/')
        if len(url_parts) > 3:  # More than http://hostname
            base_url = '/'.join(url_parts[:3])  # http://hostname
            self.endpoints.extend([
                f"{base_url}/mcp",              # SDK default path
                f"{base_url}/mcp/",             # SDK default path with trailing slash
                base_url,
                            f"{base_url}/mcp",
            f"{base_url}/mcp/"
            ])
        
        # For SSE connection, also check the SDK default notification path
        self.sse_paths = [
            f"{self.server_url}/notifications", # SDK default sse_path
            f"{self.server_url}/sse",           # Alternative SSE path
            f"{self.server_url}/events",        # Alternative events path
            self.server_url                     # Try the base URL as well
        ]
        
        self.working_endpoint = None
        self.working_sse_path = None
    
    async def run_tests(self):
        """Run all compliance tests"""
        start_time = time.time()
        logger.info(f"Starting MCP HTTP compliance tests for server: {self.server_url}")
        logger.info(f"Protocol version: {self.protocol_version}")
        
        # Find working endpoint and initialize session
        init_report = await self.test_initialization()
        self.reports.append(init_report)
        
        if init_report.result == TestResult.FAIL:
            logger.error("Failed to initialize connection to server.")
            return self.reports
        
        # Run capability-specific tests
        cap_report = await self.test_capabilities()
        self.reports.append(cap_report)
        
        if "tools" in cap_report.details.get("capabilities", {}):
            tools_report = await self.test_tools_list()
            self.reports.append(tools_report)
            
            if tools_report.result == TestResult.PASS:
                if any(t.get("name") == "echo" for t in tools_report.details.get("tools", [])):
                    self.reports.append(await self.test_echo_tool())
                if any(t.get("name") == "add" for t in tools_report.details.get("tools", [])):
                    self.reports.append(await self.test_add_tool())
        
        # Test SSE connection
        self.reports.append(await self.test_sse_connection())
        
        # Generate summary
        total_time = time.time() - start_time
        logger.info(f"Tests completed in {total_time:.2f} seconds")
        
        passed = sum(1 for r in self.reports if r.result == TestResult.PASS)
        total = len(self.reports)
        logger.info(f"Passed {passed} of {total} tests")
        
        return self.reports
    
    async def test_initialization(self) -> TestReport:
        """Test initialization and find working endpoint"""
        start_time = time.time()
        test_name = "initialization"
        logger.info(f"Testing server initialization...")
        
        # Try all potential endpoints
        for endpoint in self.endpoints:
            try:
                logger.debug(f"Trying endpoint: {endpoint}")
                
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    # Prepare init request
                    init_request = {
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "mcp.init",
                        "params": {
                            "protocol_version": self.protocol_version,
                            "client_info": {
                                "name": "MCP HTTP Compliance Tester",
                                "version": "1.0.0"
                            },
                            "client_capabilities": {
                                "tools": {},
                                "resources": {},
                                "prompts": {}
                            }
                        }
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    response = await client.post(endpoint, json=init_request, headers=headers)
                    
                    if response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} returned 404, trying next...")
                        continue
                    
                    # For any other error status codes
                    if response.status_code >= 400:
                        logger.debug(f"Endpoint {endpoint} returned {response.status_code}, trying next...")
                        continue
                    
                    # Try to parse JSON response
                    try:
                        data = response.json()
                    except Exception as e:
                        logger.debug(f"Failed to parse JSON from {endpoint}: {e}")
                        # Check if this might be a redirect to an SSE endpoint
                        content_type = response.headers.get("content-type", "")
                        if "text/event-stream" in content_type or "application/x-ndjson" in content_type:
                            logger.debug(f"Endpoint {endpoint} appears to be an SSE endpoint, not a JSON-RPC endpoint")
                            # Save as potential SSE endpoint
                            if endpoint not in self.sse_paths:
                                self.sse_paths.insert(0, endpoint)
                        continue
                    
                    # Check for success
                    if data.get("result") and data["result"].get("session_id"):
                        self.session_id = data["result"]["session_id"]
                        self.working_endpoint = endpoint
                        
                        logger.info(f"Successfully connected to {endpoint}")
                        logger.info(f"Session ID: {self.session_id}")
                        
                        # Test sending initialized notification
                        notify_request = {
                            "jsonrpc": "2.0",
                            "method": "mcp.initialized",
                            "params": {
                                "session_id": self.session_id
                            }
                        }
                        
                        try:
                            notify_response = await client.post(endpoint, json=notify_request, headers=headers)
                            # Success is a 2xx status with no response data (notification)
                            notification_success = 200 <= notify_response.status_code < 300
                        except Exception:
                            notification_success = False
                        
                        return TestReport(
                            name=test_name,
                            result=TestResult.PASS,
                            message=f"Successfully initialized session (ID: {self.session_id})",
                            details={
                                "endpoint": endpoint,
                                "session_id": self.session_id,
                                "server_info": data["result"].get("server_info", {}),
                                "protocol_version": data["result"].get("protocol_version", ""),
                                "initialized_notification": notification_success
                            },
                            elapsed_time=time.time() - start_time
                        )
                    
                    # SDK might use a different response format or return an Accepted (202) status
                    # with the session ID in a header
                    if response.status_code == 202:
                        session_id = response.headers.get("mcp-session-id")
                        if session_id:
                            self.session_id = session_id
                            self.working_endpoint = endpoint
                            
                            logger.info(f"Successfully connected to {endpoint} with 202 response")
                            logger.info(f"Session ID: {self.session_id}")
                            
                            return TestReport(
                                name=test_name,
                                result=TestResult.PASS,
                                message=f"Successfully initialized session (ID: {self.session_id}) with 202 response",
                                details={
                                    "endpoint": endpoint,
                                    "session_id": self.session_id,
                                    "server_info": data.get("result", {}).get("server_info", {}),
                                    "response_code": response.status_code
                                },
                                elapsed_time=time.time() - start_time
                            )
            except Exception as e:
                logger.debug(f"Error connecting to {endpoint}: {str(e)}")
        
        # If we get here, all endpoints failed
        return TestReport(
            name=test_name,
            result=TestResult.FAIL,
            message="Failed to connect to any MCP endpoint",
            details={"tried_endpoints": self.endpoints},
            elapsed_time=time.time() - start_time
        )
    
    async def test_capabilities(self) -> TestReport:
        """Test capabilities endpoint"""
        start_time = time.time()
        test_name = "capabilities"
        logger.info(f"Testing server capabilities...")
        
        if not self.session_id or not self.working_endpoint:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Session not initialized, skipping capabilities test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "mcp.get_capabilities",
                    "params": {
                        "session_id": self.session_id
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = await client.post(self.working_endpoint, json=request, headers=headers)
                
                if response.status_code >= 400:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Server returned error: {response.status_code}",
                        details={"response": response.text},
                        elapsed_time=time.time() - start_time
                    )
                
                data = response.json()
                
                if not data.get("result"):
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Server did not return capabilities",
                        details={"response": data},
                        elapsed_time=time.time() - start_time
                    )
                
                capabilities = data["result"]
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Server capabilities: {', '.join(capabilities.keys())}",
                    details={"capabilities": capabilities},
                    elapsed_time=time.time() - start_time
                )
                
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during capabilities test: {str(e)}",
                elapsed_time=time.time() - start_time
            )
    
    async def test_tools_list(self) -> TestReport:
        """Test tools list endpoint"""
        start_time = time.time()
        test_name = "tools_list"
        logger.info(f"Testing tools list...")
        
        if not self.session_id or not self.working_endpoint:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Session not initialized, skipping tools list test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "mcp.list_tools",
                    "params": {
                        "session_id": self.session_id
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = await client.post(self.working_endpoint, json=request, headers=headers)
                
                if response.status_code >= 400:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Server returned error: {response.status_code}",
                        details={"response": response.text},
                        elapsed_time=time.time() - start_time
                    )
                
                data = response.json()
                
                if "result" not in data:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Server did not return tools list",
                        details={"response": data},
                        elapsed_time=time.time() - start_time
                    )
                
                tools = data["result"]
                
                if not isinstance(tools, list):
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Server returned invalid tools format",
                        details={"response": data},
                        elapsed_time=time.time() - start_time
                    )
                
                # Check tool schema
                valid_schemas = all("input_schema" in tool for tool in tools)
                valid_names = all("name" in tool for tool in tools)
                
                if not valid_schemas or not valid_names:
                    return TestReport(
                        name=test_name,
                        result=TestResult.WARN,
                        message="Some tools have invalid schema",
                        details={"tools": tools},
                        elapsed_time=time.time() - start_time
                    )
                
                tool_names = [t.get("name") for t in tools]
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Available tools: {', '.join(tool_names)}",
                    details={"tools": tools},
                    elapsed_time=time.time() - start_time
                )
                
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during tools list test: {str(e)}",
                elapsed_time=time.time() - start_time
            )
    
    async def test_echo_tool(self) -> TestReport:
        """Test echo tool"""
        start_time = time.time()
        test_name = "echo_tool"
        logger.info(f"Testing echo tool...")
        
        if not self.session_id or not self.working_endpoint:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Session not initialized, skipping echo tool test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                test_message = f"Hello MCP Server! Testing at {datetime.now().isoformat()}"
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "mcp.run_tool",
                    "params": {
                        "session_id": self.session_id,
                        "name": "echo",
                        "inputs": {
                            "message": test_message
                        }
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = await client.post(self.working_endpoint, json=request, headers=headers)
                
                if response.status_code >= 400:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Server returned error: {response.status_code}",
                        details={"response": response.text},
                        elapsed_time=time.time() - start_time
                    )
                
                data = response.json()
                
                if "result" not in data:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Server did not return echo result",
                        details={"response": data},
                        elapsed_time=time.time() - start_time
                    )
                
                result = data["result"]
                output = result.get("output", "")
                
                if output != test_message:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Echo tool returned incorrect output: {output}",
                        details={
                            "expected": test_message,
                            "actual": output
                        },
                        elapsed_time=time.time() - start_time
                    )
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message="Echo tool returned correct output",
                    details={
                        "message": test_message,
                        "output": output,
                        "response_time_ms": (time.time() - start_time) * 1000
                    },
                    elapsed_time=time.time() - start_time
                )
                
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during echo tool test: {str(e)}",
                elapsed_time=time.time() - start_time
            )
    
    async def test_add_tool(self) -> TestReport:
        """Test add tool"""
        start_time = time.time()
        test_name = "add_tool"
        logger.info(f"Testing add tool...")
        
        if not self.session_id or not self.working_endpoint:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Session not initialized, skipping add tool test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                a, b = 42.5, 13.25
                expected = a + b
                
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "mcp.run_tool",
                    "params": {
                        "session_id": self.session_id,
                        "name": "add",
                        "inputs": {
                            "a": a,
                            "b": b
                        }
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = await client.post(self.working_endpoint, json=request, headers=headers)
                
                if response.status_code >= 400:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Server returned error: {response.status_code}",
                        details={"response": response.text},
                        elapsed_time=time.time() - start_time
                    )
                
                data = response.json()
                
                if "result" not in data:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Server did not return add result",
                        details={"response": data},
                        elapsed_time=time.time() - start_time
                    )
                
                result = data["result"]
                output = result.get("output")
                
                if output != expected:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message=f"Add tool returned incorrect output: {output}",
                        details={
                            "a": a,
                            "b": b,
                            "expected": expected,
                            "actual": output
                        },
                        elapsed_time=time.time() - start_time
                    )
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Add tool correctly computed {a} + {b} = {output}",
                    details={
                        "a": a,
                        "b": b,
                        "result": output,
                        "response_time_ms": (time.time() - start_time) * 1000
                    },
                    elapsed_time=time.time() - start_time
                )
                
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during add tool test: {str(e)}",
                elapsed_time=time.time() - start_time
            )
    
    async def test_sse_connection(self) -> TestReport:
        """Test SSE connection"""
        start_time = time.time()
        test_name = "sse_connection"
        logger.info(f"Testing SSE connection...")
        
        if not self.session_id or not self.working_endpoint:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Session not initialized, skipping SSE test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Prepare standard mcp.subscribe request
                request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "mcp.subscribe",
                    "params": {
                        "session_id": self.session_id
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                
                # If we already know the working SSE path, use it
                if self.working_sse_path:
                    sse_paths_to_try = [self.working_sse_path]
                else:
                    sse_paths_to_try = self.sse_paths

                # Try each potential SSE path
                for sse_path in sse_paths_to_try:
                    logger.debug(f"Trying SSE connection to: {sse_path}")
                    try:
                        async with client.stream("POST", sse_path, json=request, headers=headers) as response:
                            if response.status_code >= 400:
                                logger.debug(f"SSE path {sse_path} returned {response.status_code}, trying next...")
                                continue
                            
                            # Check if it's an event stream
                            content_type = response.headers.get("content-type", "")
                            if "text/event-stream" not in content_type and "application/x-ndjson" not in content_type:
                                logger.debug(f"SSE path {sse_path} returned non-SSE content type: {content_type}")
                                continue
                            
                            # Try to parse as SSE
                            async with EventSource(response) as event_source:
                                event_received = False
                                try:
                                    # Wait for a short time for any events (keepalive, etc.)
                                    for _ in range(5):  # Try for 5 seconds max
                                        try:
                                            # Wait for an event with a 1s timeout
                                            event = await asyncio.wait_for(
                                                event_source.aiter_events().__anext__(), 
                                                timeout=1.0
                                            )
                                            event_received = True
                                            logger.info(f"Received SSE event: {event.event} - {event.data}")
                                            break
                                        except asyncio.TimeoutError:
                                            # No event received in 1s, continue
                                            pass
                                except Exception as e:
                                    logger.debug(f"Error receiving SSE events from {sse_path}: {str(e)}")
                                    continue
                                
                                if event_received:
                                    # Save the working SSE path for future use
                                    self.working_sse_path = sse_path
                                    return TestReport(
                                        name=test_name,
                                        result=TestResult.PASS,
                                        message=f"Successfully established SSE connection to {sse_path} and received events",
                                        details={"sse_path": sse_path},
                                        elapsed_time=time.time() - start_time
                                    )
                            
                            # If we get here, we connected but didn't receive any events
                            self.working_sse_path = sse_path
                            return TestReport(
                                name=test_name,
                                result=TestResult.WARN,
                                message=f"SSE connection to {sse_path} established but no events received in 5s",
                                details={"sse_path": sse_path},
                                elapsed_time=time.time() - start_time
                            )
                    except Exception as e:
                        logger.debug(f"Failed to establish SSE connection to {sse_path}: {str(e)}")
                        continue
                
                # If we get here, all SSE paths failed
                return TestReport(
                    name=test_name,
                    result=TestResult.FAIL,
                    message="Failed to establish SSE connection to any endpoint",
                    details={"tried_paths": sse_paths_to_try},
                    elapsed_time=time.time() - start_time
                )
                
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during SSE test: {str(e)}",
                elapsed_time=time.time() - start_time
            )

def generate_report(reports, server_url: str, output_file: Optional[str] = None) -> str:
    """Generate a markdown report from test results"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    if not output_file:
        # Create a safe filename from server_url
        safe_url = ''.join(c if c.isalnum() else '_' for c in server_url)
        output_file = REPORTS_DIR / f"http_compliance_{safe_url}_{timestamp}.md"
    else:
        output_file = Path(output_file)
    
    # Calculate stats
    total = len(reports)
    passed = sum(1 for r in reports if r.result == TestResult.PASS)
    failed = sum(1 for r in reports if r.result == TestResult.FAIL)
    skipped = sum(1 for r in reports if r.result == TestResult.SKIP)
    warned = sum(1 for r in reports if r.result == TestResult.WARN)
    
    compliance = (passed / total) * 100 if total > 0 else 0
    
    # Generate report content
    lines = [
        f"# MCP HTTP/SSE Server Compliance Report\n",
        f"**Server:** `{server_url}`  ",
        f"**Date:** {date_str}  ",
        f"**MCP Version:** 2025-03-26\n",
        f"## Summary\n",
        f"- **Compliance Score:** {compliance:.1f}%",
        f"- **Total Tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        f"- **Skipped:** {skipped}",
        f"- **Warnings:** {warned}\n",
        f"## Test Results\n",
        "| Test | Result | Time (s) | Message |",
        "|------|--------|----------|---------|"
    ]
    
    # Add test results in order
    for report in reports:
        # Escape | in messages for markdown tables
        safe_message = report.message.replace("|", "\\|")
        lines.append(f"| {report.name} | {report.result} | {report.elapsed_time:.2f} | {safe_message} |")
    
    # Add details section for each test
    if any(report.details for report in reports):
        lines.append("\n## Test Details\n")
        
        for report in reports:
            if report.details:
                lines.append(f"### {report.name}\n")
                
                # Format details as JSON with indentation
                details_json = json.dumps(report.details, indent=2)
                lines.append("```json")
                lines.append(details_json)
                lines.append("```\n")
    
    # Write to file
    content = "\n".join(lines)
    with open(output_file, "w") as f:
        f.write(content)
    
    return str(output_file)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="MCP HTTP/SSE Server Compliance Tester")
    parser.add_argument("--server-url", required=True, help="URL of the MCP server")
    parser.add_argument("--protocol-version", default="2025-03-26", help="MCP protocol version")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--report", help="Path for the markdown report file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        print(f"Debug mode enabled")
    
    logger.info(f"Starting MCP HTTP compliance test for {args.server_url}")
    
    tester = MCPHttpTester(
        server_url=args.server_url,
        protocol_version=args.protocol_version,
        timeout=args.timeout,
        debug=args.debug
    )
    
    reports = await tester.run_tests()
    
    # Generate report
    report_file = generate_report(reports, args.server_url, args.report)
    logger.info(f"Report saved to: {report_file}")
    
    # Exit with success if all tests passed
    failed = sum(1 for r in reports if r.result == TestResult.FAIL)
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    asyncio.run(main()) 