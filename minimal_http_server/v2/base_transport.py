#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Base Transport Classes for MCP HTTP Server

This module defines the abstract base classes for transport mechanisms used by the MCP HTTP server.
"""

import abc
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger('MCPHTTPServer.Transport')

class BaseTransport(abc.ABC):
    """
    Abstract base class for all transport mechanisms.
    
    This class defines the interface that all transport implementations must follow.
    """
    
    def __init__(self):
        """Initialize the transport."""
        self.initialized = False
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the transport.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def send_response(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Send a response to the client.
        
        Args:
            session_id: The ID of the session to send the response to.
            data: The data to send.
            
        Returns:
            bool: True if the response was sent successfully, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def send_notification(self, session_id: str, notification: Dict[str, Any]) -> bool:
        """
        Send a notification to the client.
        
        Args:
            session_id: The ID of the session to send the notification to.
            notification: The notification to send.
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def close(self, session_id: Optional[str] = None) -> None:
        """
        Close the transport connection.
        
        Args:
            session_id: The ID of the session to close, or None to close all connections.
        """
        pass


class HTTPJSONRPCTransport(BaseTransport):
    """
    Transport implementation for standard HTTP/JSON-RPC.
    
    This transport mechanism uses standard HTTP requests and responses with JSON-RPC.
    """
    
    def __init__(self):
        """Initialize the HTTP/JSON-RPC transport."""
        super().__init__()
        # Map of session_id -> pending_responses
        self.pending_responses = {}
    
    def initialize(self) -> bool:
        """
        Initialize the HTTP/JSON-RPC transport.
        
        Returns:
            bool: True if initialization was successful.
        """
        self.initialized = True
        return True
    
    def send_response(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Store a response to be sent when the client makes a request.
        
        Args:
            session_id: The ID of the session to send the response to.
            data: The data to send.
            
        Returns:
            bool: True if the response was stored successfully.
        """
        if session_id not in self.pending_responses:
            self.pending_responses[session_id] = []
        
        self.pending_responses[session_id].append(data)
        return True
    
    def get_pending_response(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the next pending response for a session.
        
        Args:
            session_id: The ID of the session to get a response for.
            
        Returns:
            Optional[Dict[str, Any]]: The next pending response, or None if there are no pending responses.
        """
        if session_id not in self.pending_responses or not self.pending_responses[session_id]:
            return None
        
        return self.pending_responses[session_id].pop(0)
    
    def send_notification(self, session_id: str, notification: Dict[str, Any]) -> bool:
        """
        Store a notification to be sent when the client polls.
        
        Args:
            session_id: The ID of the session to send the notification to.
            notification: The notification to send.
            
        Returns:
            bool: True if the notification was stored successfully.
        """
        # For HTTP/JSON-RPC, notifications are stored and sent when the client polls
        if session_id not in self.pending_responses:
            self.pending_responses[session_id] = []
        
        self.pending_responses[session_id].append({
            "type": "notification",
            "data": notification
        })
        return True
    
    def close(self, session_id: Optional[str] = None) -> None:
        """
        Close connections for a session.
        
        Args:
            session_id: The ID of the session to close, or None to close all connections.
        """
        if session_id is None:
            # Close all connections
            self.pending_responses = {}
        elif session_id in self.pending_responses:
            # Close a specific session
            del self.pending_responses[session_id]


class HTTPSSETransport(BaseTransport):
    """
    Transport implementation for HTTP with Server-Sent Events (SSE).
    
    This transport mechanism uses HTTP for client requests and SSE for server notifications.
    """
    
    def __init__(self):
        """Initialize the HTTP/SSE transport."""
        super().__init__()
        # Map of session_id -> list of connection info dicts
        self.connections = {}
        # Map of session_id -> list of pending notifications
        self.pending_notifications = {}
    
    def initialize(self) -> bool:
        """
        Initialize the HTTP/SSE transport.
        
        Returns:
            bool: True if initialization was successful.
        """
        self.initialized = True
        return True
    
    def register_connection(self, session_id: str, connection_info: Dict[str, Any]) -> str:
        """
        Register a new SSE connection.
        
        Args:
            session_id: The ID of the session the connection belongs to.
            connection_info: Information about the connection.
            
        Returns:
            str: The ID of the new connection.
        """
        if session_id not in self.connections:
            self.connections[session_id] = []
        
        connection_id = connection_info.get("id")
        self.connections[session_id].append(connection_info)
        
        # Send any pending notifications
        if session_id in self.pending_notifications:
            for notification in self.pending_notifications[session_id]:
                self._send_sse_message(connection_info, notification, "notification")
            
            # Clear pending notifications
            self.pending_notifications[session_id] = []
        
        return connection_id
    
    def send_response(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Send a response to the client.
        
        Args:
            session_id: The ID of the session to send the response to.
            data: The data to send.
            
        Returns:
            bool: True if the response was sent successfully.
        """
        # For SSE, responses are sent via regular HTTP responses
        # This method is primarily for notification delivery
        return True
    
    def send_notification(self, session_id: str, notification: Dict[str, Any]) -> bool:
        """
        Send a notification to all SSE connections for a session.
        
        Args:
            session_id: The ID of the session to send the notification to.
            notification: The notification to send.
            
        Returns:
            bool: True if the notification was sent successfully.
        """
        if session_id not in self.connections or not self.connections[session_id]:
            # Store notification for later delivery
            if session_id not in self.pending_notifications:
                self.pending_notifications[session_id] = []
            
            self.pending_notifications[session_id].append(notification)
            return True
        
        # Send to all connections for this session
        success = True
        for conn in self.connections[session_id]:
            if not self._send_sse_message(conn, notification, "notification"):
                success = False
        
        return success
    
    def _send_sse_message(self, connection: Dict[str, Any], data: Dict[str, Any], event_type: str = "message") -> bool:
        """
        Send an SSE message to a specific connection.
        
        Args:
            connection: The connection information.
            data: The data to send.
            event_type: The SSE event type.
            
        Returns:
            bool: True if the message was sent successfully.
        """
        try:
            # Convert data to JSON
            message_json = json.dumps(data)
            
            # Format as SSE message
            sse_data = f"event: {event_type}\ndata: {message_json}\n\n"
            sse_bytes = sse_data.encode('utf-8')
            
            # Send to the connection
            connection["wfile"].write(sse_bytes)
            connection["wfile"].flush()
            connection["last_active"] = time.time()
            
            return True
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"Connection broken while sending SSE message: {str(e)}")
            # Connection is broken, will be cleaned up by maintenance
            return False
        except Exception as e:
            logger.error(f"Error sending SSE message: {str(e)}")
            return False
    
    def close(self, session_id: Optional[str] = None) -> None:
        """
        Close connections for a session.
        
        Args:
            session_id: The ID of the session to close, or None to close all connections.
        """
        if session_id is None:
            # Close all connections
            for session_connections in self.connections.values():
                for conn in session_connections:
                    try:
                        conn["connection"].close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {str(e)}")
            
            self.connections = {}
            self.pending_notifications = {}
        elif session_id in self.connections:
            # Close a specific session's connections
            for conn in self.connections[session_id]:
                try:
                    conn["connection"].close()
                except Exception as e:
                    logger.warning(f"Error closing connection for session {session_id}: {str(e)}")
            
            del self.connections[session_id]
            if session_id in self.pending_notifications:
                del self.pending_notifications[session_id] 