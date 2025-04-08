#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Server adapter module for MCP testing.

This module provides adapters for different server types.
"""

import asyncio
import subprocess
import os
import sys
import shlex
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Tuple

from mcp_testing.transports.base import MCPTransportAdapter
from mcp_testing.transports.stdio import StdioTransportAdapter
from mcp_testing.protocols.base import MCPProtocolAdapter

logger = logging.getLogger(__name__)

class ServerAdapter(ABC):
    """Base class for server adapters."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the server and prepare it for communication."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the server and clean up resources."""
        pass
    
    @abstractmethod
    def get_transport(self) -> MCPTransportAdapter:
        """Get the transport adapter for this server."""
        pass


class StdioServerAdapter(ServerAdapter):
    """Adapter for STDIO-based MCP servers."""
    
    def __init__(self, server_command: str, protocol_factory: Callable[[MCPTransportAdapter, bool], MCPProtocolAdapter], 
                 protocol_version: str, debug: bool = False, use_shell: bool = False):
        """
        Initialize a STDIO server adapter.
        
        Args:
            server_command: Command to start the server
            protocol_factory: Factory function to create a protocol adapter
            protocol_version: Protocol version to use
            debug: Whether to enable debug output
            use_shell: Whether to use shell=True when executing the server command
        """
        self.server_command = server_command
        self.protocol_factory = protocol_factory
        self.protocol_version = protocol_version
        self.debug = debug
        self.use_shell = use_shell
        self.process = None
        self.transport = None
        self.protocol = None
    
    async def start(self) -> None:
        """Start the server process and initialize the transport."""
        if self.debug:
            logger.info(f"Starting server with command: {self.server_command}")
        
        # Start the server process
        self.process = await asyncio.create_subprocess_exec(
            *shlex.split(self.server_command),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
            shell=self.use_shell
        )
        
        if self.debug:
            logger.info(f"Server process started with PID: {self.process.pid}")
        
        # Create transport adapter
        self.transport = StdioTransportAdapter(self.process.stdin, self.process.stdout, self.debug, use_shell=self.use_shell)
        
        # Create protocol adapter
        self.protocol = self.protocol_factory(self.protocol_version, self.transport, self.debug)
    
    async def stop(self) -> None:
        """Stop the server process and clean up resources."""
        if self.debug:
            logger.info("Stopping server")
        
        if self.process:
            try:
                # Try to send a shutdown request if the protocol supports it
                if self.protocol:
                    try:
                        await self.protocol.shutdown()
                    except Exception as e:
                        if self.debug:
                            logger.warning(f"Failed to send shutdown request: {e}")
                
                # Terminate the process
                self.process.terminate()
                
                # Wait for process to exit with timeout
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    if self.debug:
                        logger.warning("Process did not terminate within timeout, killing")
                    self.process.kill()
                    await self.process.wait()
                
                # Collect any remaining stderr output for debugging
                if self.debug:
                    stderr_data = await self.process.stderr.read()
                    if stderr_data:
                        logger.debug(f"Server stderr output: {stderr_data.decode('utf-8', errors='replace')}")
                
            except Exception as e:
                if self.debug:
                    logger.error(f"Error stopping server: {e}")
            
            self.process = None
            self.transport = None
            self.protocol = None
    
    def get_transport(self) -> MCPTransportAdapter:
        """Get the transport adapter for this server."""
        return self.transport


class HTTPServerAdapter(ServerAdapter):
    """Adapter for HTTP-based MCP servers."""
    
    def __init__(self, server_url: str, protocol_factory: Callable[[MCPTransportAdapter, bool], MCPProtocolAdapter], 
                 protocol_version: str, debug: bool = False):
        """
        Initialize an HTTP server adapter.
        
        Args:
            server_url: URL of the server
            protocol_factory: Factory function to create a protocol adapter
            protocol_version: Protocol version to use
            debug: Whether to enable debug output
        """
        self.server_url = server_url
        self.protocol_factory = protocol_factory
        self.protocol_version = protocol_version
        self.debug = debug
        self.transport = None
        self.protocol = None
        
        # TODO: Implement HTTP transport adapter and related functionality
        raise NotImplementedError("HTTP server adapter not implemented yet")
    
    async def start(self) -> None:
        """Initialize connection to the HTTP server."""
        # TODO: Implement HTTP transport initialization
        raise NotImplementedError("HTTP server adapter not implemented yet")
    
    async def stop(self) -> None:
        """Clean up resources."""
        # TODO: Implement cleanup for HTTP transport
        raise NotImplementedError("HTTP server adapter not implemented yet")
    
    def get_transport(self) -> MCPTransportAdapter:
        """Get the transport adapter for this server."""
        return self.transport


def create_server_adapter(server_command: str, protocol_factory: Callable[[MCPTransportAdapter, bool], MCPProtocolAdapter], 
                         protocol_version: str, server_type: Optional[str] = None, debug: bool = False,
                         use_shell: bool = False) -> ServerAdapter:
    """
    Create a server adapter for the specified server type.
    
    Args:
        server_command: Command to start the server or server URL
        protocol_factory: Factory function to create a protocol adapter
        protocol_version: Protocol version to use
        server_type: Type of server (stdio, http, etc.)
        debug: Whether to enable debug output
        use_shell: Whether to use shell=True when executing the server command
        
    Returns:
        A server adapter
        
    Raises:
        ValueError: If an unsupported server type is specified
    """
    # Default to stdio server if not specified
    if not server_type or server_type.lower() == "stdio":
        # Check if this command needs shell=True
        if not use_shell:
            if "&&" in server_command or ";" in server_command or ">" in server_command:
                use_shell = True
            # Check for Python module imports which usually need shell=True
            elif "-m" in server_command and "python" in server_command:
                use_shell = True
            # Check if it's a fetch or arxiv server
            elif "fetch" in server_command.lower() or "arxiv" in server_command.lower():
                use_shell = True
            
        return StdioServerAdapter(server_command, protocol_factory, protocol_version, debug, use_shell=use_shell)
    elif server_type.lower() == "http":
        return HTTPServerAdapter(server_command, protocol_factory, protocol_version, debug)
    else:
        raise ValueError(f"Unsupported server type: {server_type}") 