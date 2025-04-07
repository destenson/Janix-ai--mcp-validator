#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Version Negotiation Tests

This module tests the protocol version negotiation aspects of MCP, including:
1. Protocol version selection
2. Version mismatch handling
3. Capability negotiation
4. Handling of unsupported protocol versions
"""

import os
import pytest
import json
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")

class TestProtocolNegotiation(MCPBaseTest):
    """Test suite for MCP protocol version negotiation."""
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_exact_version_match(self):
        """Test initialization with the exact supported protocol version."""
        # Use the protocol version set in the environment or default
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_exact_version",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        
        # The negotiated version should match what we requested
        negotiated_version = init_data["result"]["protocolVersion"]
        assert negotiated_version == self.protocol_version, \
            f"Expected negotiated version {self.protocol_version}, got {negotiated_version}"
            
        print(f"\nSuccessfully negotiated exact version: {negotiated_version}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_newer_client_version(self):
        """Test when client requests a newer version than what we're testing."""
        # This simulates a client requesting a future version
        # Server should downgrade to its highest supported version
        future_version = "2026-01-01"  # A version from the future
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_newer_client",
            "method": "initialize",
            "params": {
                "protocolVersion": future_version,
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        # Server should still accept the request
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        
        # Server should have negotiated down to a supported version
        negotiated_version = init_data["result"]["protocolVersion"]
        known_versions = ["2024-11-05", "2025-03-26"]
        assert negotiated_version in known_versions, \
            f"Expected server to negotiate to a known version, got {negotiated_version}"
            
        print(f"\nClient requested future version {future_version}, server negotiated to {negotiated_version}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2025_03_26_only
    def test_older_client_version(self):
        """Test when client requests an older version than latest."""
        # Only run this test when testing with newer protocol versions
        if self.protocol_version == "2024-11-05":
            pytest.skip("This test only applies when testing with newer protocol versions")
        
        # Request the older protocol version
        older_version = "2024-11-05"
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_older_client",
            "method": "initialize",
            "params": {
                "protocolVersion": older_version,
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        # Server should accept the request
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        
        # For backward compatibility, server should accept the older version
        negotiated_version = init_data["result"]["protocolVersion"]
        assert negotiated_version == older_version, \
            f"Expected server to accept older version {older_version}, got {negotiated_version}"
            
        print(f"\nClient requested older version {older_version}, server accepted it")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_invalid_version_format(self):
        """Test initialization with an invalid protocol version format."""
        invalid_version = "invalid-version-format"
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_version",
            "method": "initialize",
            "params": {
                "protocolVersion": invalid_version,
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        # Server should return an error or negotiate to a valid version
        assert init_response.status_code in [200, 400]
        init_data = init_response.json()
        
        if "error" in init_data:
            # Server rejected the invalid format with an error
            assert "code" in init_data["error"]
            assert "message" in init_data["error"]
            print(f"\nServer rejected invalid version format with error: {init_data['error']['message']}")
        else:
            # Server somehow accepted it and negotiated to a valid version
            assert "result" in init_data
            assert "protocolVersion" in init_data["result"]
            negotiated_version = init_data["result"]["protocolVersion"]
            known_versions = ["2024-11-05", "2025-03-26"]
            assert negotiated_version in known_versions
            print(f"\nServer handled invalid version format by negotiating to {negotiated_version}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_missing_version(self):
        """Test initialization with missing protocol version."""
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_missing_version",
            "method": "initialize",
            "params": {
                # protocolVersion deliberately omitted
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        # Server should return an error or use a default version
        assert init_response.status_code in [200, 400]
        init_data = init_response.json()
        
        if "error" in init_data:
            # Server rejected the missing version with an error
            assert "code" in init_data["error"]
            assert "message" in init_data["error"]
            print(f"\nServer rejected missing version with error: {init_data['error']['message']}")
        else:
            # Server used a default version
            assert "result" in init_data
            assert "protocolVersion" in init_data["result"]
            negotiated_version = init_data["result"]["protocolVersion"]
            known_versions = ["2024-11-05", "2025-03-26"]
            assert negotiated_version in known_versions
            print(f"\nServer used default version {negotiated_version} when version was missing")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_capabilities_negotiation(self):
        """Test capabilities negotiation during initialization."""
        # Request initialization with all possible capabilities
        all_capabilities = {
            "supports": {
                "filesystem": True,
                "tools": True
            },
            "tools": {
                "listChanged": True
            },
            "resources": {}
        }
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_capabilities",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": all_capabilities,
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "capabilities" in init_data["result"]
        
        # The server should have returned its supported capabilities
        server_capabilities = init_data["result"]["capabilities"]
        assert isinstance(server_capabilities, dict)
        
        print(f"\nServer capabilities: {json.dumps(server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_minimal_capabilities(self):
        """Test initialization with minimal capabilities."""
        # Request initialization with minimal capabilities
        minimal_capabilities = {}
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_minimal_capabilities",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": minimal_capabilities,
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "capabilities" in init_data["result"]
        
        server_capabilities = init_data["result"]["capabilities"]
        assert isinstance(server_capabilities, dict)
        
        print(f"\nServer response to minimal capabilities: {json.dumps(server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_version_specific_capabilities(self):
        """Test version-specific capabilities."""
        capabilities = {}
        
        # Add capabilities based on protocol version
        if self.protocol_version == "2024-11-05":
            capabilities = {
                "supports": {
                    "filesystem": True,
                    "tools": True
                }
            }
        else:  # 2025-03-26 or later
            capabilities = {
                "tools": {
                    "listChanged": True
                },
                "resources": {}
            }
            
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_version_capabilities",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": capabilities,
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "capabilities" in init_data["result"]
        assert "protocolVersion" in init_data["result"]
        
        negotiated_version = init_data["result"]["protocolVersion"]
        server_capabilities = init_data["result"]["capabilities"]
        
        print(f"\nNegotiated version: {negotiated_version}")
        print(f"Server capabilities for version {negotiated_version}: {json.dumps(server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_shutdown(self):
        """Test the shutdown method after version negotiation."""
        # First initialize with the protocol version
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_shutdown_init",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "supports": {}
                },
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        assert init_notification.status_code in [200, 202, 204]
        
        # Now test shutdown
        shutdown_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_shutdown",
            "method": "shutdown",
            "params": {}
        })
        
        assert shutdown_response.status_code == 200
        shutdown_data = shutdown_response.json()
        
        # Shutdown should return an empty result object
        assert "result" in shutdown_data
        
        # Send exit notification
        exit_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "exit"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert exit_notification.status_code in [200, 202, 204] 