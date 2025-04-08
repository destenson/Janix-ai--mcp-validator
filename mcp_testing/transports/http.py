# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
HTTP Transport Adapter for MCP Testing.

This module implements an HTTP transport adapter for the MCP testing framework,
allowing tests to be run against HTTP-based MCP servers.
"""

import json
import subprocess
import time
import requests
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin
import sseclient

from mcp_testing.transports.base import MCPTransportAdapter


class HttpTransportAdapter(MCPTransportAdapter):
    """Transport adapter for HTTP-based MCP servers."""
    
    def __init__(self, 
                 server_command: Optional[str] = None,
                 server_url: Optional[str] = None, 
                 headers: Optional[Dict[str, str]] = None,
                 debug: bool = False,
                 timeout: float = 30.0,
                 use_sse: bool = False):
        """
        Initialize the HTTP transport adapter.
        
        This adapter can either start a server subprocess (if server_command is provided)
        or connect to an existing server (if server_url is provided).
        
        Args:
            server_command: Command to start the server subprocess (optional)
            server_url: URL of the server to connect to (optional)
            headers: HTTP headers to include in all requests
            debug: Whether to enable debug output
            timeout: Request timeout in seconds
            use_sse: Whether to use Server-Sent Events for notifications
            
        Note:
            Either server_command or server_url must be provided.
        """
        super().__init__(debug)
        
        if not server_command and not server_url:
            raise ValueError("Either server_command or server_url must be provided")
            
        self.server_command = server_command
        self.server_url = server_url
        self.headers = headers or {
            "Content-Type": "application/json"
        }
        self.timeout = timeout
        self.use_sse = use_sse
        self.process = None
        self.session = requests.Session()
        self.sse_client = None
        self.notification_queue = asyncio.Queue()
        self.logger = logging.getLogger("HttpTransportAdapter")
        
        if debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
    
    def start(self) -> bool:
        """
        Start the HTTP transport.
        
        If server_command is provided, starts a server subprocess.
        Otherwise, verifies connectivity to the provided server_url.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_started:
            return True
            
        try:
            if self.server_command:
                self.logger.debug(f"Starting server with command: {self.server_command}")
                # Start the server subprocess
                self.process = subprocess.Popen(
                    self.server_command.split(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False  # Binary mode
                )
                
                # Wait a moment for the server to start
                time.sleep(2)
                
                # The server URL must be specified after starting if not explicitly provided
                if not self.server_url:
                    self.server_url = "http://localhost:8000"  # Default URL
                    
            # Verify connectivity
            self.logger.debug(f"Verifying connectivity to {self.server_url}")
            response = self.session.options(self.server_url, timeout=self.timeout)
            response.raise_for_status()
            
            # If using SSE, set up the SSE client
            if self.use_sse:
                self.logger.debug("Setting up SSE client")
                sse_url = urljoin(self.server_url, "/notifications")
                headers = {**self.headers, "Accept": "text/event-stream"}
                self._start_sse_listener(sse_url, headers)
            
            self.is_started = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start HTTP transport: {str(e)}")
            self.stop()  # Clean up any resources
            return False
    
    def stop(self) -> bool:
        """
        Stop the HTTP transport.
        
        Terminates the server subprocess if it was started by this adapter.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            # Close the SSE client if it exists
            if self.sse_client:
                self.logger.debug("Closing SSE client")
                # SSE client doesn't typically have a close method, but we can cleanup the connection
                self.sse_client = None
            
            # Close the session
            self.logger.debug("Closing HTTP session")
            self.session.close()
            
            # Terminate the process if it was started by this adapter
            if self.process:
                self.logger.debug("Terminating server process")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Server process did not terminate, forcing kill")
                    self.process.kill()
                self.process = None
                
            self.is_started = False
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop HTTP transport: {str(e)}")
            return False
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and wait for a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object
            
        Raises:
            ConnectionError: If the transport is not started or the request fails
        """
        if not self.is_started:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert request to JSON
            request_str = json.dumps(request)
            
            if self.debug:
                self.logger.debug(f"Sending request: {request_str}")
            
            # Send the HTTP request
            response = self.session.post(
                self.server_url,
                data=request_str,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            response_json = response.json()
            
            if self.debug:
                self.logger.debug(f"Received response: {json.dumps(response_json)}")
            
            return response_json
            
        except requests.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Failed to send request: {str(e)}")
    
    def send_notification(self, notification: Dict[str, Any]) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            notification: The JSON-RPC notification object
            
        Raises:
            ConnectionError: If the transport is not started or the notification fails
        """
        if not self.is_started:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert notification to JSON
            notification_str = json.dumps(notification)
            
            if self.debug:
                self.logger.debug(f"Sending notification: {notification_str}")
            
            # Send the HTTP request (no response expected)
            response = self.session.post(
                self.server_url,
                data=notification_str,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
        except requests.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Failed to send notification: {str(e)}")
    
    def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Send a batch of JSON-RPC requests and wait for responses.
        
        Args:
            requests: A list of JSON-RPC request objects
            
        Returns:
            A list of JSON-RPC response objects
            
        Raises:
            ConnectionError: If the transport is not started or the batch request fails
        """
        if not self.is_started:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert batch to JSON
            batch_str = json.dumps(requests)
            
            if self.debug:
                self.logger.debug(f"Sending batch request: {batch_str}")
            
            # Send the HTTP request
            response = self.session.post(
                self.server_url,
                data=batch_str,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse the response
            responses = response.json()
            
            if self.debug:
                self.logger.debug(f"Received batch response: {json.dumps(responses)}")
            
            # Ensure the response is a list
            if not isinstance(responses, list):
                raise ConnectionError("Expected batch response to be an array")
                
            return responses
            
        except requests.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Failed to send batch request: {str(e)}")
    
    def _start_sse_listener(self, sse_url: str, headers: Dict[str, str]) -> None:
        """
        Start a background thread to listen for SSE events.
        
        Args:
            sse_url: The URL to connect to for SSE events
            headers: HTTP headers to use for the SSE connection
        """
        try:
            # This would typically be implemented with a background thread
            # that listens for SSE events and adds them to the notification queue.
            # For simplicity, we're not implementing the full background thread here.
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to start SSE listener: {str(e)}")
    
    async def get_next_notification(self) -> Optional[Dict[str, Any]]:
        """
        Get the next notification from the notification queue.
        
        Returns:
            The next notification, or None if the queue is empty
            
        Note:
            This is an async method that waits for the next notification.
        """
        if not self.is_started or not self.use_sse:
            return None
            
        try:
            # Wait for the next notification (with timeout)
            notification = await asyncio.wait_for(
                self.notification_queue.get(),
                timeout=self.timeout
            )
            return notification
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get next notification: {str(e)}")
            return None 