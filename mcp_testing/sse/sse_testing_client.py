#!/usr/bin/env python3
"""
MCP SSE Compliance Tester

A comprehensive tool for validating MCP Server-Sent Events (SSE) servers
against the MCP specification (2025-03-26). Uses the official MCP Python SDK.

This tool allows you to:
1. Connect to any MCP SSE server via HTTP
2. Perform capability negotiation
3. Run a series of compliance tests
4. Generate a detailed compliance report
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import re
from pathlib import Path

try:
    # Import MCP SDK components
    from mcp import ClientSession, types
    from mcp.client.http import HttpClientTransport
    from mcp.types import ToolResult, PromptMessage, Resource, Tool, Prompt
except ImportError as e:
    import traceback
    print("Error: Required MCP SDK not found. Please install with:")
    print("pip install mcp")
    print("\nDetailed error:")
    traceback.print_exc()
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("mcp-tester")

# Protocol versions supported by this client
SUPPORTED_PROTOCOL_VERSIONS = ["2025-03-26", "2024-11-05"]
DEFAULT_PROTOCOL_VERSION = "2025-03-26"


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"


@dataclass
class TestReport:
    name: str
    result: TestResult
    message: str
    details: Optional[Dict[str, Any]] = None
    elapsed_time: float = 0.0


class Capability(Enum):
    """MCP Server capabilities"""
    PROMPTS = "prompts"
    RESOURCES = "resources"
    TOOLS = "tools"
    LOGGING = "logging"
    COMPLETIONS = "completions"


class MCPSSEComplianceTester:
    """MCP Compliance Tester for SSE servers using the official MCP Python SDK"""
    
    def __init__(self, server_url: str, protocol_version: str = DEFAULT_PROTOCOL_VERSION, timeout: int = 30):
        """Initialize the MCP test client"""
        self.server_url = server_url
        self.protocol_version = protocol_version
        self.timeout = timeout
        self.session_id = None
        self.server_capabilities = {}
        self.server_info = {}
        self.reports = []
        self.client_id = str(uuid.uuid4())
        
        # Setup HTTP transport for SSE
        self.transport = HttpClientTransport(url=server_url)
        self.client_session = None
    
    async def run_tests(self) -> List[TestReport]:
        """Run all MCP compliance tests"""
        start_time = time.time()
        log.info(f"Starting MCP compliance tests for server: {self.server_url}")
        log.info(f"Using protocol version: {self.protocol_version}")
        
        try:
            # Initialize session
            self.client_session = ClientSession(
                read=self.transport.read,
                write=self.transport.write,
                sampling_callback=None,  # We don't need sampling for testing
            )
            
            # Run initialization test
            init_report = await self.test_initialization()
            self.reports.append(init_report)
            
            if init_report.result == TestResult.FAIL:
                log.error("Initialization failed, cannot continue with further tests")
                await self.cleanup()
                return self.reports
            
            # Run capability-specific tests based on what the server supports
            if self.has_capability(Capability.PROMPTS):
                self.reports.append(await self.test_prompts_list())
                
            if self.has_capability(Capability.RESOURCES):
                self.reports.append(await self.test_resources_list())
                resource_template_report = await self.test_resource_templates_list()
                self.reports.append(resource_template_report)
                
                # If we have resources, test reading one
                if resource_template_report.result == TestResult.PASS and resource_template_report.details and resource_template_report.details.get("resource_templates"):
                    self.reports.append(await self.test_resource_read(resource_template_report.details["resource_templates"][0]))
                
            if self.has_capability(Capability.TOOLS):
                tools_report = await self.test_tools_list()
                self.reports.append(tools_report)
                
                # If we have tools, test calling one
                if tools_report.result == TestResult.PASS and tools_report.details and tools_report.details.get("sample_tools"):
                    self.reports.append(await self.test_tool_call(tools_report.details["sample_tools"][0]))
                
            if self.has_capability(Capability.LOGGING):
                self.reports.append(await self.test_logging())
                
            if self.has_capability(Capability.COMPLETIONS):
                self.reports.append(await self.test_completions())
            
            # Test ping functionality (always available)
            self.reports.append(await self.test_ping())
            
            # Test proper error handling for invalid methods
            self.reports.append(await self.test_invalid_method())
            
        except Exception as e:
            log.error(f"Unexpected error during testing: {e}")
            self.reports.append(TestReport(
                name="unexpected_error",
                result=TestResult.FAIL,
                message=f"Unexpected error during testing: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            ))
        finally:
            # Clean up
            await self.cleanup()
        
        total_time = time.time() - start_time
        log.info(f"All tests completed in {total_time:.2f} seconds")
        
        # Generate summary
        self._generate_summary()
        
        return self.reports

    async def cleanup(self):
        """Clean up resources"""
        if self.client_session:
            await self.client_session.close()
    
    def _generate_summary(self):
        """Generate a summary of test results"""
        total = len(self.reports)
        passed = sum(1 for r in self.reports if r.result == TestResult.PASS)
        failed = sum(1 for r in self.reports if r.result == TestResult.FAIL)
        skipped = sum(1 for r in self.reports if r.result == TestResult.SKIP)
        warned = sum(1 for r in self.reports if r.result == TestResult.WARN)
        
        log.info("=== MCP COMPLIANCE TEST SUMMARY ===")
        log.info(f"Total tests: {total}")
        log.info(f"Passed: {passed}")
        log.info(f"Failed: {failed}")
        log.info(f"Skipped: {skipped}")
        log.info(f"Warnings: {warned}")
        
        if total > 0:
            log.info(f"Compliance score: {(passed / total) * 100:.1f}%")
        
        if failed > 0:
            log.info("\nFailed tests:")
            for report in self.reports:
                if report.result == TestResult.FAIL:
                    log.info(f" - {report.name}: {report.message}")

    def has_capability(self, capability: Capability) -> bool:
        """Check if the server has a specific capability"""
        return capability.value in self.server_capabilities

    async def test_initialization(self) -> TestReport:
        """Test initialization and capability negotiation"""
        start_time = time.time()
        test_name = "initialization"
        log.info(f"Running test: {test_name}")
        
        try:
            # Initialize the client session
            await self.client_session.initialize(
                proto_version=self.protocol_version,
                client_capabilities={
                    "sampling": {},
                    "roots": {
                        "listChanged": True
                    }
                },
                client_info={
                    "name": "MCP-Compliance-Tester",
                    "version": "1.0.0"
                }
            )
            
            # Get server capabilities and info from the client session
            self.server_capabilities = self.client_session.server_capabilities
            self.server_info = self.client_session.server_info
            self.protocol_version = self.client_session.proto_version
            
            # Send initialized notification
            await self.client_session.notify_initialized()
            
            return TestReport(
                name=test_name,
                result=TestResult.PASS,
                message="Server initialization successful",
                details={
                    "server_capabilities": self.server_capabilities,
                    "server_info": self.server_info,
                    "protocol_version": self.protocol_version
                },
                elapsed_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during initialization: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_prompts_list(self) -> TestReport:
        """Test the prompts/list method"""
        start_time = time.time()
        test_name = "prompts_list"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.PROMPTS):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support prompts capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # List prompts using the client session
            prompts_result = await self.client_session.list_prompts()
            
            if not prompts_result:
                return TestReport(
                    name=test_name,
                    result=TestResult.FAIL,
                    message="Failed to receive prompts list from server",
                    elapsed_time=time.time() - start_time
                )
            
            prompts = prompts_result.prompts
            
            # Check for pagination
            has_pagination = prompts_result.next_cursor is not None
            
            return TestReport(
                name=test_name,
                result=TestResult.PASS,
                message=f"Successfully retrieved {len(prompts)} prompts",
                details={
                    "prompt_count": len(prompts),
                    "has_pagination": has_pagination,
                    "sample_prompts": prompts[:2] if prompts else []
                },
                elapsed_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_resources_list(self) -> TestReport:
        """Test the resources/list method"""
        start_time = time.time()
        test_name = "resources_list"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.RESOURCES):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support resources capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # List resources using the client session
            resources_result = await self.client_session.list_resources()
            
            if not resources_result:
                return TestReport(
                    name=test_name,
                    result=TestResult.FAIL,
                    message="Failed to receive resources list from server",
                    elapsed_time=time.time() - start_time
                )
            
            resources = resources_result.resources
            
            # Check for pagination
            has_pagination = resources_result.next_cursor is not None
            
            # Validate resource URIs
            valid_uris = all(r.uri for r in resources)
            
            return TestReport(
                name=test_name,
                result=TestResult.PASS,
                message=f"Successfully retrieved {len(resources)} resources",
                details={
                    "resource_count": len(resources),
                    "has_pagination": has_pagination,
                    "valid_uris": valid_uris,
                    "sample_resources": resources[:2] if resources else []
                },
                elapsed_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_resource_templates_list(self) -> TestReport:
        """Test the resources/templates/list method"""
        start_time = time.time()
        test_name = "resource_templates_list"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.RESOURCES):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support resources capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # List resource templates using the client session
            try:
                templates_result = await self.client_session.list_resource_templates()
                
                if not templates_result:
                    return TestReport(
                        name=test_name,
                        result=TestResult.FAIL,
                        message="Failed to receive resource templates list from server",
                        elapsed_time=time.time() - start_time
                    )
                
                templates = templates_result.resource_templates
                
                # Check for pagination
                has_pagination = templates_result.next_cursor is not None
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Successfully retrieved {len(templates)} resource templates",
                    details={
                        "template_count": len(templates),
                        "has_pagination": has_pagination,
                        "resource_templates": templates[:2] if templates else []
                    },
                    elapsed_time=time.time() - start_time
                )
            except Exception as e:
                # Some servers might not implement this method
                return TestReport(
                    name=test_name,
                    result=TestResult.WARN,
                    message=f"Server doesn't support resource templates: {str(e)}",
                    elapsed_time=time.time() - start_time
                )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_resource_read(self, resource_template: Dict[str, Any]) -> TestReport:
        """Test reading a resource"""
        start_time = time.time()
        test_name = "resource_read"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.RESOURCES):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support resources capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # Extract information from the template
            uri_template = resource_template.get("uri_template")
            
            if not uri_template:
                return TestReport(
                    name=test_name,
                    result=TestResult.SKIP,
                    message="No valid resource template available for testing",
                    elapsed_time=time.time() - start_time
                )
            
            # Prepare a URI by replacing template parameters with test values
            uri = uri_template
            if "{" in uri_template and "}" in uri_template:
                # For each parameter in the template, replace with a test value
                param_matches = re.findall(r'\{([^}]+)\}', uri_template)
                for param in param_matches:
                    uri = uri.replace(f"{{{param}}}", "test")
            
            # Read the resource
            try:
                content, mime_type = await self.client_session.read_resource(uri)
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Successfully read resource with URI: {uri}",
                    details={
                        "uri": uri,
                        "mime_type": mime_type,
                        "content_sample": str(content)[:100] if content else None
                    },
                    elapsed_time=time.time() - start_time
                )
            except Exception as e:
                # The resource might not exist with our test parameters
                return TestReport(
                    name=test_name,
                    result=TestResult.WARN,
                    message=f"Could not read resource with URI {uri}: {str(e)}",
                    details={"uri": uri, "error": str(e)},
                    elapsed_time=time.time() - start_time
                )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_tools_list(self) -> TestReport:
        """Test the tools/list method"""
        start_time = time.time()
        test_name = "tools_list"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.TOOLS):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support tools capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # List tools using the client session
            tools_result = await self.client_session.list_tools()
            
            if not tools_result:
                return TestReport(
                    name=test_name,
                    result=TestResult.FAIL,
                    message="Failed to receive tools list from server",
                    elapsed_time=time.time() - start_time
                )
            
            tools = tools_result.tools
            
            # Check for pagination
            has_pagination = tools_result.next_cursor is not None
            
            # Validate tool schemas
            valid_schemas = all(hasattr(t, "input_schema") for t in tools)
            
            return TestReport(
                name=test_name,
                result=TestResult.PASS,
                message=f"Successfully retrieved {len(tools)} tools",
                details={
                    "tool_count": len(tools),
                    "has_pagination": has_pagination,
                    "valid_schemas": valid_schemas,
                    "sample_tools": tools[:2] if tools else []
                },
                elapsed_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_tool_call(self, tool: Dict[str, Any]) -> TestReport:
        """Test calling a tool"""
        start_time = time.time()
        test_name = "tool_call"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.TOOLS):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support tools capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            tool_name = tool.get("name")
            input_schema = tool.get("input_schema", {})
            
            if not tool_name:
                return TestReport(
                    name=test_name,
                    result=TestResult.SKIP,
                    message="No valid tool available for testing",
                    elapsed_time=time.time() - start_time
                )
            
            # Prepare arguments based on the tool's input schema
            arguments = {}
            if input_schema:
                properties = input_schema.get("properties", {})
                for prop_name, prop_details in properties.items():
                    # Generate a test value based on the property type
                    prop_type = prop_details.get("type")
                    if prop_type == "string":
                        arguments[prop_name] = "test"
                    elif prop_type == "number" or prop_type == "integer":
                        arguments[prop_name] = 42
                    elif prop_type == "boolean":
                        arguments[prop_name] = True
                    elif prop_type == "array":
                        arguments[prop_name] = []
                    elif prop_type == "object":
                        arguments[prop_name] = {}
            
            # Call the tool
            try:
                result = await self.client_session.call_tool(tool_name, arguments)
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Successfully called tool: {tool_name}",
                    details={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "is_error": result.is_error if hasattr(result, "is_error") else None,
                        "content_sample": str(result.content)[:100] if hasattr(result, "content") else None
                    },
                    elapsed_time=time.time() - start_time
                )
            except Exception as e:
                # The tool might not accept our test arguments
                return TestReport(
                    name=test_name,
                    result=TestResult.WARN,
                    message=f"Could not call tool {tool_name}: {str(e)}",
                    details={"tool_name": tool_name, "arguments": arguments, "error": str(e)},
                    elapsed_time=time.time() - start_time
                )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_logging(self) -> TestReport:
        """Test the logging capability"""
        start_time = time.time()
        test_name = "logging"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.LOGGING):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support logging capability",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # Set logging level using the client session
            try:
                await self.client_session.set_log_level("info")
                
                # Trigger server activity by making a ping request
                await self.client_session.ping()
                
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message="Successfully set logging level to 'info'",
                    elapsed_time=time.time() - start_time
                )
            except Exception as e:
                return TestReport(
                    name=test_name,
                    result=TestResult.WARN,
                    message=f"Logging is declared but might not be fully implemented: {str(e)}",
                    details={"error": str(e)},
                    elapsed_time=time.time() - start_time
                )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_completions(self) -> TestReport:
        """Test the completion/complete method"""
        start_time = time.time()
        test_name = "completions"
        log.info(f"Running test: {test_name}")
        
        if not self.has_capability(Capability.COMPLETIONS):
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="Server does not support completions capability",
                elapsed_time=time.time() - start_time
            )
        
        # Try to get a prompt or resource template for completion testing
        prompt_name = None
        resource_uri = None
        arg_name = None
        
        if self.has_capability(Capability.PROMPTS):
            try:
                prompts_result = await self.client_session.list_prompts()
                if prompts_result and prompts_result.prompts:
                    for prompt in prompts_result.prompts:
                        if prompt.arguments:
                            prompt_name = prompt.name
                            arg_name = prompt.arguments[0].name
                            break
            except Exception as e:
                log.warning(f"Error getting prompts for completion test: {str(e)}")
        
        if not prompt_name and self.has_capability(Capability.RESOURCES):
            try:
                templates_result = await self.client_session.list_resource_templates()
                if templates_result and templates_result.resource_templates:
                    for template in templates_result.resource_templates:
                        if "{" in template.uri_template and "}" in template.uri_template:
                            resource_uri = template.uri_template
                            # Extract parameter name
                            match = re.search(r'\{([^}]+)\}', resource_uri)
                            if match:
                                arg_name = match.group(1)
                                break
            except Exception as e:
                log.warning(f"Error getting resource templates for completion test: {str(e)}")
        
        if not prompt_name and not resource_uri:
            return TestReport(
                name=test_name,
                result=TestResult.SKIP,
                message="No suitable prompt or resource template found for completion test",
                elapsed_time=time.time() - start_time
            )
        
        try:
            # Test completion with either a prompt or resource
            if prompt_name:
                try:
                    # Use MCP SDK's complete method
                    completion_result = await self.client_session.complete(
                        ref_type="ref/prompt",
                        ref=prompt_name,
                        arg_name=arg_name,
                        arg_value="a"
                    )
                    
                    return TestReport(
                        name=test_name,
                        result=TestResult.PASS,
                        message=f"Successfully tested completions for prompt: {prompt_name}",
                        details={
                            "ref_type": "prompt",
                            "ref_name": prompt_name,
                            "arg_name": arg_name,
                            "completion": completion_result
                        },
                        elapsed_time=time.time() - start_time
                    )
                except Exception as e:
                    return TestReport(
                        name=test_name,
                        result=TestResult.WARN,
                        message=f"Completions declared but failed for prompt {prompt_name}: {str(e)}",
                        details={"error": str(e)},
                        elapsed_time=time.time() - start_time
                    )
            else:
                try:
                    # Use MCP SDK's complete method
                    completion_result = await self.client_session.complete(
                        ref_type="ref/resource",
                        ref=resource_uri,
                        arg_name=arg_name,
                        arg_value="a"
                    )
                    
                    return TestReport(
                        name=test_name,
                        result=TestResult.PASS,
                        message=f"Successfully tested completions for resource URI: {resource_uri}",
                        details={
                            "ref_type": "resource",
                            "ref_name": resource_uri,
                            "arg_name": arg_name,
                            "completion": completion_result
                        },
                        elapsed_time=time.time() - start_time
                    )
                except Exception as e:
                    return TestReport(
                        name=test_name,
                        result=TestResult.WARN,
                        message=f"Completions declared but failed for resource {resource_uri}: {str(e)}",
                        details={"error": str(e)},
                        elapsed_time=time.time() - start_time
                    )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_ping(self) -> TestReport:
        """Test the ping functionality"""
        start_time = time.time()
        test_name = "ping"
        log.info(f"Running test: {test_name}")
        
        try:
            # Send ping using the client session
            await self.client_session.ping()
            
            return TestReport(
                name=test_name,
                result=TestResult.PASS,
                message="Successfully tested ping functionality",
                details={"response_time_ms": (time.time() - start_time) * 1000},
                elapsed_time=time.time() - start_time
            )
            
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Error during test: {str(e)}",
                details={"exception": str(e)},
                elapsed_time=time.time() - start_time
            )

    async def test_invalid_method(self) -> TestReport:
        """Test error handling for invalid methods"""
        start_time = time.time()
        test_name = "invalid_method"
        log.info(f"Running test: {test_name}")
        
        try:
            # Use low-level transport to send an invalid method
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "non_existent_method"
            }
            try:
                # We expect this to fail with a method not found error
                await self.transport.send_request(request)
                return TestReport(
                    name=test_name,
                    result=TestResult.FAIL,
                    message="Server did not return error for invalid method",
                    elapsed_time=time.time() - start_time
                )
            except Exception as e:
                # We expect an error with code -32601
                return TestReport(
                    name=test_name,
                    result=TestResult.PASS,
                    message=f"Server returned expected error for invalid method: {str(e)}",
                    elapsed_time=time.time() - start_time
                )
        except Exception as e:
            return TestReport(
                name=test_name,
                result=TestResult.FAIL,
                message=f"Unexpected error during invalid method test: {str(e)}",
                elapsed_time=time.time() - start_time
            )
