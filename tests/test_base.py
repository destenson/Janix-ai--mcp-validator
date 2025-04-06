#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base Test Module

Provides common utilities and base classes for MCP compliance testing,
including requirement level handling for MUST, SHOULD, and MAY requirements.
"""

import os
import json
import pytest
import requests
from enum import Enum
from typing import List, Dict, Any, Optional, Union

# Constants for requirement types
class RequirementLevel(Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

class RequirementSeverity(Enum):
    CRITICAL = "Critical"
    MEDIUM = "Medium"
    LOW = "Low"

class MCPBaseTest:
    """Base class for all MCP test suites."""
    
    def __init__(self):
        """Initialize the base test class with common attributes."""
        self.server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
        self.client_url = os.environ.get("MCP_CLIENT_URL", "http://localhost:8081")
        self.server_capabilities = {}
        self.client_capabilities = {}
        self.session_id = None
        
    def _send_request(self, data: Dict[str, Any]) -> requests.Response:
        """Send a request to the MCP server.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            The HTTP response object.
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.session_id:
            headers["MCP-Session-ID"] = self.session_id
            
        response = requests.post(
            self.server_url,
            headers=headers,
            json=data
        )
        
        # Check for and store session ID if provided
        if "MCP-Session-ID" in response.headers:
            self.session_id = response.headers["MCP-Session-ID"]
            
        return response
    
    def _send_request_to_client(self, data: Dict[str, Any]) -> requests.Response:
        """Send a request to the MCP client.
        
        Args:
            data: The JSON-RPC request data.
            
        Returns:
            The HTTP response object.
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.session_id:
            headers["MCP-Session-ID"] = self.session_id
            
        response = requests.post(
            self.client_url,
            headers=headers,
            json=data
        )
        
        # Check for and store session ID if provided
        if "MCP-Session-ID" in response.headers:
            self.session_id = response.headers["MCP-Session-ID"]
            
        return response
    
    def get_requirement_level(self, req_id: str) -> RequirementLevel:
        """Determine the requirement level (MUST, SHOULD, MAY) from requirement ID.
        
        Args:
            req_id: The requirement ID (e.g., "M001", "S019", "A005").
            
        Returns:
            The requirement level enum.
        """
        if req_id.startswith("M"):
            return RequirementLevel.MUST
        elif req_id.startswith("S"):
            return RequirementLevel.SHOULD
        elif req_id.startswith("A"):
            return RequirementLevel.MAY
        else:
            # Default to MUST for any unknown format
            return RequirementLevel.MUST
    
    def get_requirement_severity(self, req_id: str) -> RequirementSeverity:
        """Get the severity level based on requirement ID.
        
        Args:
            req_id: The requirement ID.
            
        Returns:
            The severity level enum.
        """
        level = self.get_requirement_level(req_id)
        
        if level == RequirementLevel.MUST:
            return RequirementSeverity.CRITICAL
        elif level == RequirementLevel.SHOULD:
            return RequirementSeverity.MEDIUM
        else:
            return RequirementSeverity.LOW
    
    def skip_if_not_supported(self, capability: str, subcapability: Optional[str] = None) -> None:
        """Skip a test if the required capability is not supported.
        
        Args:
            capability: The main capability name.
            subcapability: Optional subcapability name.
        """
        if not self.server_capabilities:
            pytest.skip("Server capabilities not yet determined")
            
        if capability not in self.server_capabilities:
            pytest.skip(f"Server does not support {capability} capability")
            
        if subcapability and (
            not isinstance(self.server_capabilities[capability], dict) or
            subcapability not in self.server_capabilities[capability]
        ):
            pytest.skip(f"Server does not support {capability}.{subcapability} capability")
    
    def skip_client_if_not_supported(self, capability: str, subcapability: Optional[str] = None) -> None:
        """Skip a test if the required client capability is not supported.
        
        Args:
            capability: The main capability name.
            subcapability: Optional subcapability name.
        """
        if not self.client_capabilities:
            pytest.skip("Client capabilities not yet determined")
            
        if capability not in self.client_capabilities:
            pytest.skip(f"Client does not support {capability} capability")
            
        if subcapability and (
            not isinstance(self.client_capabilities[capability], dict) or
            subcapability not in self.client_capabilities[capability]
        ):
            pytest.skip(f"Client does not support {capability}.{subcapability} capability")
    
    def report_requirement_failure(self, req_ids: Union[str, List[str]], message: str) -> None:
        """Report a detailed requirement failure.
        
        This method enhances test failures with requirement information for better reporting.
        
        Args:
            req_ids: One or more requirement IDs that failed.
            message: Failure message.
        """
        if isinstance(req_ids, str):
            req_ids = [req_ids]
            
        severity_levels = {self.get_requirement_severity(req_id).value for req_id in req_ids}
        requirement_levels = {self.get_requirement_level(req_id).value for req_id in req_ids}
        
        failure_message = (
            f"FAILED REQUIREMENTS: {', '.join(req_ids)}\n"
            f"SEVERITY: {', '.join(severity_levels)}\n"
            f"TYPE: {', '.join(requirement_levels)}\n"
            f"DETAILS: {message}"
        )
        
        pytest.fail(failure_message)
        
# Helper functions for pytest markers
def must_requirement(req_id: str) -> Dict[str, Any]:
    """Create a pytest marker for a MUST requirement.
    
    Args:
        req_id: The requirement ID (e.g., "M001").
        
    Returns:
        Dictionary with marker info.
    """
    return {
        "requirement": req_id,
        "level": "MUST",
        "severity": "Critical"
    }

def should_requirement(req_id: str) -> Dict[str, Any]:
    """Create a pytest marker for a SHOULD requirement.
    
    Args:
        req_id: The requirement ID (e.g., "S019").
        
    Returns:
        Dictionary with marker info.
    """
    return {
        "requirement": req_id,
        "level": "SHOULD",
        "severity": "Medium"
    }

def may_requirement(req_id: str) -> Dict[str, Any]:
    """Create a pytest marker for a MAY requirement.
    
    Args:
        req_id: The requirement ID (e.g., "A005").
        
    Returns:
        Dictionary with marker info.
    """
    return {
        "requirement": req_id,
        "level": "MAY",
        "severity": "Low"
    }

# Pytest marker registration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "requirement: mark test with specific MCP requirements")
    config.addinivalue_line("markers", "must_requirement: mark test with MUST requirements")
    config.addinivalue_line("markers", "should_requirement: mark test with SHOULD requirements")
    config.addinivalue_line("markers", "may_requirement: mark test with MAY requirements") 