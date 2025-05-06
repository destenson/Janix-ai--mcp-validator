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
import uuid

from mcp_testing.transports.base import MCPTransportAdapter


class HttpTransportAdapter(MCPTransportAdapter):
    """Transport adapter for HTTP-based MCP servers."""
    
    # JSON-RPC error codes to HTTP status codes mapping
    ERROR_CODE_MAP = {
        -32700: 400,  # Parse error
        -32600: 400,  # Invalid Request
        -32601: 404,  # Method not found
        -32602: 400,  # Invalid params
        -32603: 500,  # Internal error
        -32001: 401,  # Authentication error
        -32002: 409,  # Server already initialized
    }
    
    # HTTP status codes to JSON-RPC error codes mapping
    HTTP_CODE_MAP = {
        400: -32600,  # Bad Request -> Invalid Request
        401: -32001,  # Unauthorized -> Authentication error
        404: -32601,  # Not Found -> Method not found
        409: -32002,  # Conflict -> Server already initialized
        500: -32603,  # Internal Server Error -> Internal error
    }
    
    def __init__(self, 
                 server_command: Optional[str] = None,
                 server_url: Optional[str] = None, 
                 headers: Optional[Dict[str, str]] = None,
                 debug: bool = False,
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
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
            max_retries: Number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            
        Note:
            Either server_command or server_url must be provided.
        """
        super().__init__(debug)
        
        # For compatibility with the test runner, treat server_command as server_url if it's a URL
        if server_command and (server_command.startswith("http://") or server_command.startswith("https://")):
            server_url = server_command
            server_command = None
        
        if not server_command and not server_url:
            raise ValueError("Either server_command or server_url must be provided")
            
        self.server_command = server_command
        self.server_url = server_url
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.process = None
        self.session = self._create_session()
        self.notification_queue = asyncio.Queue()
        self.logger = logging.getLogger("HttpTransportAdapter")
        self._notification_task = None
        self._should_stop = False
        
        # Generate a session ID immediately and include it in headers to avoid 400 errors
        self.session_id = str(uuid.uuid4())
        self.headers["Mcp-Session-Id"] = self.session_id
        
        if debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.debug(f"Created adapter with session ID: {self.session_id}")
    
    def _create_session(self) -> requests.Session:
        """Create and configure a requests Session."""
        session = requests.Session()
        
        # Configure retries
        retry = requests.adapters.Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
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
                    
            # Verify connectivity with an initialize request
            self.logger.debug(f"Verifying connectivity to {self.server_url}")
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": "connection-test",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "MCPTestingFramework",
                        "version": "1.0.0"
                    }
                }
            }
            response = self.session.post(
                self.server_url,
                json=init_request,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract session ID from response
            response_json = response.json()
            self.session_id = self._extract_session_id(response, response_json)
            if self.session_id:
                self.headers["Mcp-Session-Id"] = self.session_id
            
            # Send initialized notification
            init_notification = {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            }
            self.send_notification(init_notification)
            
            # Start background task to poll for notifications
            self._should_stop = False
            loop = asyncio.get_event_loop()
            self._notification_task = loop.create_task(self._notification_listener())
            
            self.is_started = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start HTTP transport: {str(e)}")
            self.stop()  # Clean up any resources
            return False
    
    def stop(self) -> None:
        """Stop the transport and clean up resources."""
        self.logger.debug("Stopping HTTP transport")
        
        # Signal notification listener to stop
        self._should_stop = True
        
        # Wait for notification task to complete
        if self._notification_task:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.run_until_complete(self._notification_task)
                self._notification_task = None
            except Exception as e:
                self.logger.error(f"Error stopping notification task: {str(e)}")
        
        # Close session
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                self.logger.error(f"Error closing session: {str(e)}")
        
        # Stop server if we started it
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                self.logger.error(f"Error stopping server process: {str(e)}")
            finally:
                self.process = None
        
        self.is_started = False
        self.session_id = None
        self.logger.debug("HTTP transport stopped")
    
    async def _notification_listener(self):
        """Listen for SSE notifications from the server."""
        if not self.server_url:
            self.logger.error("No server URL configured")
            return
            
        headers = self.headers.copy()
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            
        self.logger.debug("Starting notification listener")
        
        while not self._should_stop:
            try:
                # Create SSE client
                response = self.session.get(
                    urljoin(self.server_url, "notifications"),
                    headers=headers,
                    stream=True,
                    timeout=None  # Long polling
                )
                response.raise_for_status()
                
                client = sseclient.SSEClient(response)
                
                # Process events
                for event in client.events():
                    if self._should_stop:
                        break
                        
                    try:
                        # Parse notification
                        notification = json.loads(event.data)
                        
                        # Validate notification format
                        if not isinstance(notification, dict):
                            self.logger.warning(f"Invalid notification format: {notification}")
                            continue
                            
                        if "jsonrpc" not in notification or notification["jsonrpc"] != "2.0":
                            self.logger.warning(f"Invalid JSON-RPC version in notification: {notification}")
                            continue
                            
                        if "method" not in notification:
                            self.logger.warning(f"Missing method in notification: {notification}")
                            continue
                            
                        # Queue notification for processing
                        await self.notification_queue.put(notification)
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse notification: {str(e)}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing notification: {str(e)}")
                        continue
                        
            except requests.exceptions.ConnectionError as e:
                if not self._should_stop:
                    self.logger.warning(f"SSE connection error, reconnecting: {str(e)}")
                    await asyncio.sleep(1)  # Wait before retry
            except requests.exceptions.RequestException as e:
                if not self._should_stop:
                    self.logger.error(f"SSE request error: {str(e)}")
                    await asyncio.sleep(5)  # Longer wait for request errors
            except Exception as e:
                if not self._should_stop:
                    self.logger.error(f"Unexpected error in notification listener: {str(e)}")
                    await asyncio.sleep(5)
                    
        self.logger.debug("Notification listener stopped")
    
    async def get_next_notification(self) -> Optional[Dict[str, Any]]:
        """
        Get the next notification from the notification queue.
        
        Returns:
            The next notification, or None if notifications are not enabled or times out
            
        Note:
            This is an async method that waits for the next notification.
        """
        if not self.is_started:
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
    
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.session_id

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response and convert to JSON-RPC format."""
        try:
            # Try to parse JSON response
            json_response = response.json()
            
            # If it's already a valid JSON-RPC response, return it
            if isinstance(json_response, dict) and "jsonrpc" in json_response:
                return json_response
            
            # Convert HTTP error to JSON-RPC error
            if not response.ok:
                error_code = self.HTTP_CODE_MAP.get(response.status_code, -32603)
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": error_code,
                        "message": response.reason or "Unknown error",
                        "data": json_response
                    },
                    "id": None
                }
            
            # Wrap successful response
            return {
                "jsonrpc": "2.0",
                "result": json_response,
                "id": None
            }
            
        except requests.exceptions.JSONDecodeError:
            # Handle non-JSON responses
            if not response.ok:
                error_code = self.HTTP_CODE_MAP.get(response.status_code, -32603)
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": error_code,
                        "message": response.reason or "Unknown error",
                        "data": response.text
                    },
                    "id": None
                }
            
            return {
                "jsonrpc": "2.0",
                "result": response.text,
                "id": None
            }
    
    def _extract_session_id(self, response: requests.Response, response_json: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from response headers or body."""
        # First try headers (case-insensitive)
        for header in response.headers:
            if header.lower() == "mcp-session-id":
                return response.headers[header]
        
        # Then try response body
        if isinstance(response_json, dict):
            # Try result.session.id path
            if "result" in response_json:
                result = response_json["result"]
                if isinstance(result, dict):
                    if "session" in result and isinstance(result["session"], dict):
                        if "id" in result["session"]:
                            return result["session"]["id"]
            
            # Try direct sessionId field
            if "sessionId" in response_json:
                return response_json["sessionId"]
        
        return None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        if not self.is_started:
            raise TransportError("Transport not started")
            
        # Build request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id or str(uuid.uuid4())
        }
        if params is not None:
            request["params"] = params
            
        # Always ensure we have a session ID
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
            self.logger.debug(f"Created new session ID: {self.session_id}")
            
        # Add session ID to headers
        headers = self.headers.copy()
        headers["Mcp-Session-Id"] = self.session_id
            
        self.logger.debug(f"Sending request: {request}")
        self.logger.debug(f"Headers: {headers}")
        
        try:
            # Send request with retry handling
            response = self.session.post(
                self.server_url,
                json=request,
                headers=headers,
                timeout=self.timeout
            )
            
            # Process response
            json_response = self._handle_response(response)
            
            # Extract session ID if this is an initialization response
            if method == "initialize" and response.ok:
                session_id = self._extract_session_id(response, json_response)
                if session_id:
                    self.session_id = session_id
                    self.logger.debug(f"Extracted session ID: {session_id}")
            
            return json_response
            
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32003,
                    "message": "Connection error",
                    "data": str(e)
                },
                "id": request.get("id")
            }
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request timeout: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32004,
                    "message": "Request timeout",
                    "data": str(e)
                },
                "id": request.get("id")
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": request.get("id")
            }
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": request.get("id")
            }
    
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
            if self.debug:
                self.logger.debug(f"Sending notification: {json.dumps(notification)}")
            
            # Always ensure we have a session ID
            if not self.session_id:
                self.session_id = str(uuid.uuid4())
                self.logger.debug(f"Created new session ID for notification: {self.session_id}")
            
            # Add session ID header
            headers = self.headers.copy()
            headers["Mcp-Session-Id"] = self.session_id
            
            # Send the HTTP request (no response expected)
            response = self.session.post(
                self.server_url,
                json=notification,
                headers=headers,
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
            if self.debug:
                self.logger.debug(f"Sending batch request: {json.dumps(requests)}")
            
            # Always ensure we have a session ID
            if not self.session_id:
                self.session_id = str(uuid.uuid4())
                self.logger.debug(f"Created new session ID for batch: {self.session_id}")
            
            # Add session ID header
            headers = self.headers.copy()
            headers["Mcp-Session-Id"] = self.session_id
            
            # Send the HTTP request
            response = self.session.post(
                self.server_url,
                json=requests,
                headers=headers,
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