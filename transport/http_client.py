"""
HTTP transport implementation for MCP Protocol Validator.

This module provides an implementation of the MCPTransport interface
for communicating with MCP servers over HTTP.
"""

import json
import requests
from typing import Dict, Any, Optional, List, Union
from transport.base import MCPTransport


class HTTPTransport(MCPTransport):
    """
    HTTP transport implementation for communicating with MCP servers over HTTP.
    
    This class handles HTTP-specific connection and communication details.
    """
    
    def __init__(self, url: str, timeout: float = 10.0, debug: bool = False):
        """
        Initialize the HTTP transport.
        
        Args:
            url: The base URL of the MCP server
            timeout: Request timeout in seconds
            debug: Whether to enable debug logging
        """
        super().__init__(debug=debug)
        self.url = url
        self.timeout = timeout
        self.session = None
        self.is_running = False
        self.log_debug(f"Initialized HTTP transport with URL: {url}")
        
    def start(self) -> bool:
        """
        Start the HTTP connection to the server.
        
        Sets up a persistent session for communicating with the server.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            self.session = requests.Session()
            # Verify connection is possible
            response = self.session.get(
                self.url, 
                timeout=self.timeout
            )
            response.raise_for_status()
            self.is_running = True
            self.log_debug("HTTP transport started successfully")
            return True
        except requests.RequestException as e:
            self.log_error(f"Failed to start HTTP transport: {str(e)}")
            return False
        
    def stop(self) -> bool:
        """
        Stop the HTTP connection to the server.
        
        Closes the session and cleans up resources.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.session:
            self.session.close()
            self.session = None
        self.is_running = False
        self.log_debug("HTTP transport stopped")
        return True
        
    def send_request(self, request: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server over HTTP and get the response.
        
        Args:
            request: Either a complete request object or a method name string
            params: Parameters to pass to the method (if request is a method name)
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            The JSON-RPC response from the server
            
        Raises:
            RuntimeError: If the transport is not started
            requests.RequestException: If there's an HTTP error
        """
        if not self.is_running or not self.session:
            raise RuntimeError("HTTP transport not started")
            
        # Handle the case where request is a complete request object
        if isinstance(request, dict):
            request_obj = request
            request_id = request.get("id", request_id or self.next_request_id())
        # Handle the case where request is a method name
        else:
            # Use provided request ID or generate one
            request_id = request_id or self.next_request_id()
            # Format the request
            params = params or {}
            method = request
            request_obj = self.format_request(method, params, request_id)
        
        request_json = json.dumps(request_obj)
        
        # Log the request
        self.log_debug(f"Sending request: {request_json}")
        
        # Send the request
        try:
            response = self.session.post(
                self.url,
                json=request_obj,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            response_json = response.json()
            
            # Log the response
            self.log_debug(f"Received response: {json.dumps(response_json)}")
            
            return response_json
        except requests.RequestException as e:
            self.log_error(f"HTTP request failed: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"Transport error: {str(e)}"
                }
            }
        except json.JSONDecodeError as e:
            self.log_error(f"Failed to parse response as JSON: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON response"
                }
            }
            
    def send_notification(self, notification: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification to the server over HTTP (no response expected).
        
        Args:
            notification: Either a complete notification object or a method name string
            params: Parameters to pass to the method (if notification is a method name)
            
        Raises:
            RuntimeError: If the transport is not started
        """
        if not self.is_running or not self.session:
            raise RuntimeError("HTTP transport not started")
            
        # Handle the case where notification is a complete notification object
        if isinstance(notification, dict):
            notification_obj = notification
        # Handle the case where notification is a method name
        else:
            # Format the notification
            params = params or {}
            method = notification
            notification_obj = self.format_notification(method, params)
        
        notification_json = json.dumps(notification_obj)
        
        # Log the notification
        self.log_debug(f"Sending notification: {notification_json}")
        
        # Send the notification
        try:
            self.session.post(
                self.url,
                json=notification_obj,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        except requests.RequestException as e:
            self.log_error(f"Failed to send notification: {str(e)}")
            # No response to return for notifications 