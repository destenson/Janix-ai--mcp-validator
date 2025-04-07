#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base test classes for MCP test suites.
"""

import os
import json
import sys
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Import our transport layer
from transport import STDIOTransport, HTTPTransport, DockerSTDIOTransport
from transport.base import MCPTransport

# Import protocol adapters
from protocols import get_protocol_adapter, MCPProtocolAdapter

# Import utility modules
from utils.config import MCPValidatorConfig, get_config
from utils.logging import get_logger, configure_logging
from utils.report import TestReport

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")
MCP_TRANSPORT_TYPE = os.environ.get("MCP_TRANSPORT_TYPE", "http")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:3000")
MCP_DEBUG = os.environ.get("MCP_DEBUG", "false").lower() == "true"

# Configure logging
logger = get_logger("test_base")


class MCPBaseTest:
    """Base class for all MCP test suites."""
    
    def setup_method(self, method):
        """Initialize the base test class with common attributes.
        
        This uses pytest's setup_method which runs before each test method
        instead of __init__ which causes pytest collection issues.
        """
        # Initialize common test attributes
        self.server_capabilities = None
        self.negotiated_version = None
        self.protocol_version = MCP_PROTOCOL_VERSION
        
        # For HTTP transport, configure the server URL and port
        if MCP_TRANSPORT_TYPE == "http":
            self.server_url = MCP_SERVER_URL
            try:
                self.port = int(self.server_url.split(":")[-1].split("/")[0])
            except (ValueError, IndexError):
                self.port = 3000
        
        # For STDIO transport, would initialize transport here
        if MCP_TRANSPORT_TYPE == "stdio":
            # Simplified for this version
            pass
            
        if MCP_DEBUG:
            print(f"\nInitializing test with protocol version {self.protocol_version}")
            print(f"Transport type: {MCP_TRANSPORT_TYPE}")
    
    def teardown_method(self, method):
        """Clean up resources after each test method."""
        # If a test didn't properly clean up (e.g., due to an error),
        # try to send a shutdown request
        if hasattr(self, 'server_capabilities') and self.server_capabilities:
            try:
                self._send_request({
                    "jsonrpc": "2.0",
                    "id": "cleanup_shutdown",
                    "method": "shutdown",
                    "params": {}
                })
                self._send_request({
                    "jsonrpc": "2.0",
                    "method": "exit"
                })
            except Exception as e:
                if MCP_DEBUG:
                    print(f"Error during cleanup: {e}")
    
    def _send_request(self, request_data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                      wait_for_response: bool = True) -> requests.Response:
        """
        Send a JSON-RPC request to the server.
        
        Args:
            request_data: The JSON-RPC request object or array of request objects
            wait_for_response: Whether to wait for a response (defaults to True)
            
        Returns:
            The HTTP response object
            
        Raises:
            ConnectionError: If the request fails
        """
        if MCP_TRANSPORT_TYPE == "http":
            try:
                # For HTTP transport, send a POST request
                response = requests.post(
                    self.server_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                return response
            except Exception as e:
                raise ConnectionError(f"Failed to send request: {e}")
        else:
            # For other transport types, this would be implemented differently
            # This is a simplified mock response for now
            mock_response = MockResponse(200, {"result": {}})
            return mock_response
    
    def _create_transport(self) -> MCPTransport:
        """
        Create a transport instance based on the current configuration.
        
        Returns:
            An initialized MCPTransport instance
        
        Raises:
            ValueError: If the transport type is not supported
        """
        if MCP_TRANSPORT_TYPE == "http":
            return HTTPTransport(
                server_url=self.server_url, 
                debug=MCP_DEBUG
            )
        elif MCP_TRANSPORT_TYPE == "stdio":
            if self.config.server_command:
                return STDIOTransport(
                    server_command=self.config.server_command,
                    debug=MCP_DEBUG,
                    timeout=self.config.timeout
                )
            else:
                raise ValueError("server_command must be specified for STDIO transport")
        elif MCP_TRANSPORT_TYPE == "docker":
            if self.config.docker_image:
                return DockerSTDIOTransport(
                    docker_image=self.config.docker_image,
                    mount_dir=self.config.mount_dir,
                    debug=MCP_DEBUG,
                    timeout=self.config.timeout
                )
            else:
                raise ValueError("docker_image must be specified for Docker transport")
        else:
            raise ValueError(f"Unsupported transport type: {MCP_TRANSPORT_TYPE}")
    
    def _create_protocol_adapter(self) -> MCPProtocolAdapter:
        """
        Create a protocol adapter for the configured protocol version.
        
        Returns:
            An initialized MCPProtocolAdapter instance
        
        Raises:
            ValueError: If the protocol version is not supported
        """
        return get_protocol_adapter(
            version=self.protocol_version,
            transport=self._create_transport(),
            debug=MCP_DEBUG
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for the current protocol version.
        
        Returns:
            The loaded JSON schema as a dictionary.
        """
        schema_file = f"mcp_schema_{self.protocol_version}.json"
        schema_path = Path(__file__).parent.parent / "schema" / schema_file
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file for version {self.protocol_version} not found at {schema_path}")
        
        with open(schema_path) as f:
            return json.load(f)
    
    async def initialize_server(self, client_capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Initialize the connection with the server.
        
        Args:
            client_capabilities: Optional client capabilities to advertise
            
        Returns:
            The server's initialization response
            
        Raises:
            ConnectionError: If initialization fails
        """
        # Initialize the server
        start_time = time.time()
        try:
            result = await self._create_protocol_adapter().initialize(client_capabilities)
            await self._create_protocol_adapter().send_initialized()
            
            # Record result in report
            self.report.add_result(
                test_name="initialize_server",
                status="passed",
                duration=time.time() - start_time,
                details={"server_capabilities": result}
            )
            
            # Get server info if available
            try:
                server_info = await self._create_protocol_adapter().get_server_info()
                self.report.set_metadata(
                    transport_type=MCP_TRANSPORT_TYPE,
                    protocol_version=self.protocol_version,
                    server_info=server_info
                )
            except Exception as e:
                logger.warning(f"Could not get server info: {e}")
            
            return result
        except Exception as e:
            # Record failure in report
            self.report.add_result(
                test_name="initialize_server",
                status="failed",
                duration=time.time() - start_time,
                message=str(e)
            )
            raise
    
    async def shutdown_server(self) -> None:
        """
        Shutdown the connection with the server.
        
        Raises:
            ConnectionError: If shutdown fails
        """
        if self._create_protocol_adapter():
            await self._create_protocol_adapter().close()


class MockResponse:
    """Mock response object with similar interface to requests.Response for testing."""
    
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]]):
        """
        Initialize a mock response.
        
        Args:
            status_code: HTTP status code
            json_data: JSON response data
        """
        self.status_code = status_code
        self._json_data = json_data
        self.headers = {}
    
    def json(self) -> Dict[str, Any]:
        """
        Get the JSON response data.
        
        Returns:
            The JSON response data
        """
        return self._json_data 