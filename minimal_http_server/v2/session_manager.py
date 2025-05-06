#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Session Manager for MCP HTTP Server

This module provides session management functionality for the MCP HTTP server.
"""

import json
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger('MCPHTTPServer.Session')

# Session constants
SESSION_TIMEOUT = 3600  # 1 hour in seconds
SESSION_CLEANUP_INTERVAL = 300  # 5 minutes in seconds

class Session:
    """
    Class representing a single client session.
    """
    
    def __init__(self, session_id: str, protocol_version: str = None):
        """
        Initialize a new session.
        
        Args:
            session_id: The unique identifier for this session.
            protocol_version: The MCP protocol version for this session.
        """
        self.id = session_id
        self.created_at = time.time()
        self.last_active = time.time()
        self.initialized = False
        self.protocol_version = protocol_version
        self.capabilities = {}
        self.client_info = {}
        
        # Storage for pending async tool calls
        self.pending_async_calls = {}
        
        # Storage for client-specific data
        self.data = {}
        
        # Flag to indicate test mode (used for compliance testing)
        self.is_test_session = False
        
        # Flag to indicate if this session is handling any requests
        self.handling_request = False
        
        # Track request count for diagnostics
        self.request_count = 0
    
    def update_activity(self):
        """Update the last activity timestamp for this session."""
        self.last_active = time.time()
        
    def start_request(self):
        """Mark this session as handling a request."""
        self.handling_request = True
        self.request_count += 1
        self.update_activity()
        
    def end_request(self):
        """Mark this session as no longer handling a request."""
        self.handling_request = False
        self.update_activity()
    
    def is_expired(self, timeout: int = SESSION_TIMEOUT) -> bool:
        """
        Check if this session has expired.
        
        Args:
            timeout: The timeout period in seconds.
            
        Returns:
            bool: True if the session has expired, False otherwise.
        """
        # Test sessions have a longer timeout
        if self.is_test_session:
            # Use a longer timeout for test sessions
            timeout = max(timeout * 2, 7200)  # At least 2 hours for test sessions
        
        # Don't expire a session that's currently handling a request
        if self.handling_request:
            return False
            
        return time.time() - self.last_active > timeout
    
    def mark_as_test_session(self):
        """Mark this session as a test session with special handling."""
        self.is_test_session = True
        logger.debug(f"Session {self.id} marked as test session")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the session to a dictionary.
        
        Returns:
            Dict[str, Any]: The session data as a dictionary.
        """
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "initialized": self.initialized,
            "protocol_version": self.protocol_version,
            "capabilities": self.capabilities,
            "client_info": self.client_info,
            "is_test_session": self.is_test_session,
            "request_count": self.request_count
        }


class SessionManager:
    """
    Manager for client sessions.
    
    This class is responsible for creating, tracking, and cleaning up client sessions.
    """
    
    def __init__(self, cleanup_interval: int = SESSION_CLEANUP_INTERVAL):
        """
        Initialize the session manager.
        
        Args:
            cleanup_interval: The interval in seconds between session cleanup runs.
        """
        self.sessions: Dict[str, Session] = {}
        self.cleanup_interval = cleanup_interval
        self.cleanup_thread = None
        self.shutdown_flag = threading.Event()
        self.lock = threading.RLock()
    
    def start(self):
        """Start the session manager and background cleanup thread."""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.shutdown_flag.clear()
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="SessionCleanupThread"
            )
            self.cleanup_thread.start()
            logger.info("Session manager started")
    
    def stop(self):
        """Stop the session manager and background cleanup thread."""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.shutdown_flag.set()
            self.cleanup_thread.join(timeout=5.0)
            logger.info("Session manager stopped")
    
    def create_session(self, protocol_version: Optional[str] = None) -> Session:
        """
        Create a new session.
        
        Args:
            protocol_version: The MCP protocol version for this session.
            
        Returns:
            Session: The newly created session.
        """
        with self.lock:
            session_id = str(uuid.uuid4())
            session = Session(session_id, protocol_version)
            self.sessions[session_id] = session
            logger.info(f"Created new session: {session_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by its ID.
        
        Args:
            session_id: The ID of the session to retrieve.
            
        Returns:
            Optional[Session]: The session, or None if not found.
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.update_activity()
            return session
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session.
        
        Args:
            session_id: The ID of the session to remove.
            
        Returns:
            bool: True if the session was removed, False otherwise.
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Removed session: {session_id}")
                return True
            return False
    
    def initialize_session(self, session_id: str, protocol_version: str, 
                           client_info: Dict[str, Any], capabilities: Dict[str, Any]) -> bool:
        """
        Initialize a session with client info and capabilities.
        
        Args:
            session_id: The ID of the session to initialize.
            protocol_version: The MCP protocol version for this session.
            client_info: Information about the client.
            capabilities: The client's capabilities.
            
        Returns:
            bool: True if the session was initialized, False otherwise.
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Cannot initialize non-existent session: {session_id}")
                return False
            
            session.protocol_version = protocol_version
            session.client_info = client_info
            session.capabilities = capabilities
            session.initialized = True
            session.update_activity()
            
            logger.info(f"Initialized session {session_id} with protocol version {protocol_version}")
            return True
    
    def get_all_sessions(self) -> Dict[str, Session]:
        """
        Get all active sessions.
        
        Returns:
            Dict[str, Session]: A dictionary of all active sessions.
        """
        with self.lock:
            return self.sessions.copy()
    
    def cleanup_expired_sessions(self, timeout: int = SESSION_TIMEOUT) -> Set[str]:
        """
        Clean up expired sessions.
        
        Args:
            timeout: The timeout period in seconds.
            
        Returns:
            Set[str]: The IDs of the sessions that were removed.
        """
        removed_sessions = set()
        with self.lock:
            for session_id, session in list(self.sessions.items()):
                if session.is_expired(timeout):
                    del self.sessions[session_id]
                    removed_sessions.add(session_id)
                    logger.info(f"Removed expired session: {session_id}")
        
        return removed_sessions
    
    def _cleanup_loop(self):
        """Background thread that periodically cleans up expired sessions."""
        logger.info("Session cleanup thread started")
        
        while not self.shutdown_flag.is_set():
            try:
                removed = self.cleanup_expired_sessions()
                if removed:
                    logger.info(f"Cleaned up {len(removed)} expired sessions")
                
                # Wait for the next cleanup interval or until shutdown is requested
                self.shutdown_flag.wait(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")
                # Wait a bit before trying again
                time.sleep(60)
        
        logger.info("Session cleanup thread stopped") 