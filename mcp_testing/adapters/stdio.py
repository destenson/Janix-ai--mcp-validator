#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
STDIO server adapter for MCP testing.

This module defines a server adapter that starts a subprocess and
communicates with it over standard input/output using JSON-RPC.
"""

import asyncio
import logging
import os
import shlex
import signal
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple, Union

from ..transports.stdio import StdioTransportAdapter
from .base import MCPServerAdapter

logger = logging.getLogger(__name__)


class StdioServerAdapter(MCPServerAdapter):
    """
    Adapter for MCP servers that communicate over standard input/output.
    
    This adapter starts a server as a subprocess and communicates with it
    using the STDIO transport.
    """
    
    def __init__(
        self,
        server_command: str,
        protocol_version: str,
        debug: bool = False,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize a STDIO server adapter.
        
        Args:
            server_command: The command to start the server
            protocol_version: The MCP protocol version to use
            debug: Whether to enable debug logging
            env: Additional environment variables to set when running the server
        """
        super().__init__(protocol_version, debug)
        self.server_command = server_command
        self.env = env or {}
        self.process = None
        self.transport = None
        
    async def start(self) -> bool:
        """
        Start the server as a subprocess.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.process is not None:
            logger.warning("Server is already running")
            return True
            
        # Create environment for the subprocess
        env = os.environ.copy()
        env.update(self.env)
        
        if self.debug:
            logger.debug(f"Starting server with command: {self.server_command}")
            logger.debug(f"Environment: {env}")
            
        try:
            # Start the server process
            args = shlex.split(self.server_command)
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=False,  # We want binary I/O
            )
            
            # Create a transport adapter for communicating with the server
            self.transport = StdioTransportAdapter(
                self.process.stdin,
                self.process.stdout,
                self.debug,
            )
            
            # Start a background task to log stderr output
            if self.debug:
                asyncio.create_task(self._log_stderr())
                
            return True
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            return False
            
    async def stop(self) -> bool:
        """
        Stop the server.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.process is None:
            logger.warning("Server is not running")
            return True
            
        try:
            if self.debug:
                logger.debug("Stopping server")
                
            # Try to send a shutdown request first
            await self.shutdown()
            
            # Close the transport
            if self.transport:
                await self.transport.close()
                self.transport = None
                
            # If the process is still running, terminate it
            if self.process.poll() is None:
                logger.debug("Server still running, sending SIGTERM")
                self.process.terminate()
                
                # Wait for the process to terminate
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Server didn't terminate, sending SIGKILL")
                    self.process.kill()
                    
            # Clean up
            self.process = None
            return True
        except Exception as e:
            logger.error(f"Failed to stop server: {str(e)}")
            return False
            
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a request to the server and wait for a response.
        
        Args:
            method: The JSON-RPC method name
            params: The method parameters
            
        Returns:
            The server's response
            
        Raises:
            RuntimeError: If the server is not started or the request fails
        """
        if self.process is None or self.transport is None:
            raise RuntimeError("Server is not running")
            
        if params is None:
            params = {}
            
        request_id = self._get_next_request_id()
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        
        if self.debug:
            logger.debug(f"Sending request: {request}")
            
        try:
            await self.transport.send_message(request)
            response = await self.transport.receive_message()
            
            if self.debug:
                logger.debug(f"Received response: {response}")
                
            if not isinstance(response, dict):
                raise RuntimeError(f"Expected dict response, got {type(response)}")
                
            if "id" not in response or response["id"] != request_id:
                raise RuntimeError(f"Response ID mismatch: expected {request_id}, got {response.get('id')}")
                
            return response
        except Exception as e:
            logger.error(f"Failed to send request: {str(e)}")
            raise RuntimeError(f"Failed to send request: {str(e)}")
            
    async def send_notification(self, method: str, params: Dict[str, Any] = None) -> None:
        """
        Send a notification to the server (no response expected).
        
        Args:
            method: The JSON-RPC method name
            params: The method parameters
            
        Raises:
            RuntimeError: If the server is not started or the notification fails
        """
        if self.process is None or self.transport is None:
            raise RuntimeError("Server is not running")
            
        if params is None:
            params = {}
            
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        
        if self.debug:
            logger.debug(f"Sending notification: {notification}")
            
        try:
            await self.transport.send_message(notification)
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise RuntimeError(f"Failed to send notification: {str(e)}")
            
    async def _log_stderr(self) -> None:
        """
        Log the stderr output from the server process.
        """
        if self.process is None or self.process.stderr is None:
            return
            
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stderr.readline
                )
                
                if not line:
                    break
                    
                try:
                    stderr_line = line.decode('utf-8').rstrip()
                    logger.debug(f"Server stderr: {stderr_line}")
                except UnicodeDecodeError:
                    logger.debug(f"Server stderr (binary): {line}")
            except Exception as e:
                logger.error(f"Error reading stderr: {str(e)}")
                break 