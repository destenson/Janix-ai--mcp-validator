#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Utilities Tests

This module tests various utility aspects of the MCP protocol, focusing on:
1. Batch request handling
2. Error reporting and handling
3. Transport-specific behaviors
4. Protocol extensions
5. Performance characteristics

These tests ensure that the MCP protocol implementation handles edge cases
and provides utility functions as expected.
"""

import os
import pytest
import json
import time
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")
MCP_TRANSPORT_TYPE = os.environ.get("MCP_TRANSPORT_TYPE", "http")

class TestUtilitiesProtocol(MCPBaseTest):
    """Test suite for MCP protocol utility functionality."""
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_initialization(self):
        """Test the initialization process."""
        # Send initialize request
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_initialization",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "supports": {
                        "utilities": True
                    }
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
        assert "capabilities" in init_data["result"]
        
        # Store the capabilities for later tests
        self.server_capabilities = init_data["result"]["capabilities"]
        self.negotiated_version = init_data["result"]["protocolVersion"]
        
        print(f"\nNegotiated protocol version: {self.negotiated_version}")
        print(f"Server capabilities: {json.dumps(self.server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_batch_requests(self):
        """Test handling of JSON-RPC batch requests."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if using STDIO transport (some implementations may not support batching)
        if MCP_TRANSPORT_TYPE == "stdio":
            pytest.skip("Batch requests may not be supported in STDIO transport")
        
        # Create a batch of requests
        batch_requests = [
            {
                "jsonrpc": "2.0",
                "id": "batch_req_1",
                "method": "server/info",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": "batch_req_2",
                "method": "tools/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "method": "initialized"  # A notification (no id)
            }
        ]
        
        # Send batch request
        batch_response = self._send_request(batch_requests)
        
        # Check response
        assert batch_response.status_code == 200
        batch_data = batch_response.json()
        
        # Should be an array of responses
        assert isinstance(batch_data, list)
        
        # Should have responses for each request with an ID (not for notifications)
        assert len(batch_data) >= 2  # At least 2 responses for the 2 requests with IDs
        
        # Check that responses match request IDs
        response_ids = [resp["id"] for resp in batch_data if "id" in resp]
        assert "batch_req_1" in response_ids
        assert "batch_req_2" in response_ids
        
        # Each response should have a result or error
        for resp in batch_data:
            assert "jsonrpc" in resp
            assert resp["jsonrpc"] == "2.0"
            assert "id" in resp
            assert "result" in resp or "error" in resp
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_error_handling(self):
        """Test proper error handling for various scenarios."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # 1. Test with invalid method
        invalid_method_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_method",
            "method": "non_existent_method",
            "params": {}
        })
        
        # Should return 200 with a JSON-RPC error
        assert invalid_method_response.status_code == 200
        invalid_method_data = invalid_method_response.json()
        
        assert "error" in invalid_method_data
        assert "code" in invalid_method_data["error"]
        assert "message" in invalid_method_data["error"]
        assert invalid_method_data["error"]["code"] == -32601  # Method not found
        
        # 2. Test with invalid params
        invalid_params_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_params",
            "method": "tools/call",
            "params": {
                # Missing required parameters
            }
        })
        
        # Should return 200 with a JSON-RPC error
        assert invalid_params_response.status_code == 200
        invalid_params_data = invalid_params_response.json()
        
        assert "error" in invalid_params_data
        assert "code" in invalid_params_data["error"]
        assert "message" in invalid_params_data["error"]
        assert invalid_params_data["error"]["code"] in [-32602, -32700]  # Invalid params or parse error
        
        # 3. Test with invalid JSON
        # This requires direct HTTP access, may not work with all transports
        if MCP_TRANSPORT_TYPE == "http":
            import requests
            import urllib.parse
            server_url = f"http://localhost:{self.port}"
            
            try:
                invalid_json_response = requests.post(
                    server_url,
                    data="this is not valid JSON",
                    headers={"Content-Type": "application/json"}
                )
                
                # Should return 200 with a JSON-RPC error
                assert invalid_json_response.status_code == 200
                invalid_json_data = invalid_json_response.json()
                
                assert "error" in invalid_json_data
                assert "code" in invalid_json_data["error"]
                assert "message" in invalid_json_data["error"]
                assert invalid_json_data["error"]["code"] == -32700  # Parse error
            except Exception as e:
                print(f"Direct HTTP request failed: {e}")
                # Skip this part if direct HTTP access fails
                pass
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    @pytest.mark.http_only
    def test_http_specific_behaviors(self):
        """Test HTTP-specific behaviors (HTTP transport only)."""
        # Skip if not using HTTP transport
        if MCP_TRANSPORT_TYPE != "http":
            pytest.skip("Test only applicable for HTTP transport")
        
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        import requests
        server_url = f"http://localhost:{self.port}"
        
        # 1. Test content-type requirements
        try:
            content_type_response = requests.post(
                server_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "test_content_type",
                    "method": "server/info",
                    "params": {}
                },
                headers={"Content-Type": "text/plain"}  # Incorrect content type
            )
            
            # Should either:
            # - Return 415 Unsupported Media Type
            # - Return 200 with a JSON-RPC error
            assert content_type_response.status_code in [200, 415]
            
            if content_type_response.status_code == 200:
                content_type_data = content_type_response.json()
                if "error" in content_type_data:
                    print(f"\nContent type error handled with: {content_type_data['error']['message']}")
        except Exception as e:
            print(f"Content type test failed: {e}")
            # Skip this part if the request fails
            pass
        
        # 2. Test HTTP status codes for different error types
        # (Specific implementations may handle this differently)
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    @pytest.mark.stdio_only
    def test_stdio_specific_behaviors(self):
        """Test STDIO-specific behaviors (STDIO transport only)."""
        # Skip if not using STDIO transport
        if MCP_TRANSPORT_TYPE != "stdio":
            pytest.skip("Test only applicable for STDIO transport")
        
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # STDIO-specific tests would typically focus on:
        # - Line-by-line processing
        # - Handling of large inputs/outputs
        # - Proper JSON formatting
        #
        # However, these are difficult to test directly through the transport layer
        # Most STDIO behaviors are tested through the normal JSON-RPC tests
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_cancellation(self):
        """Test request cancellation if supported."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Check if cancellation is supported
        supports_cancellation = False
        if "supports" in self.server_capabilities:
            supports_cancellation = self.server_capabilities.get("supports", {}).get("cancellation", False)
        
        if not supports_cancellation:
            pytest.skip("Cancellation not supported by this server")
        
        # Start a long-running operation
        long_request_id = "long_running_request"
        long_response = self._send_request({
            "jsonrpc": "2.0",
            "id": long_request_id,
            "method": "tools/call",
            "params": {
                "name": "sleep",  # Assuming a sleep tool is available
                "parameters": {
                    "seconds": 10  # Sleep for 10 seconds
                }
            }
        }, wait_for_response=False)  # Don't wait for response
        
        # Send cancellation request
        cancel_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "cancel_request",
            "method": "$/cancelRequest",
            "params": {
                "id": long_request_id
            }
        })
        
        # Check cancellation response
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        
        # Cancellation should return a result (implementation-specific)
        if "result" in cancel_data:
            print(f"\nCancellation successful: {json.dumps(cancel_data['result'])}")
        elif "error" in cancel_data:
            error_code = cancel_data["error"].get("code")
            if error_code == -32601:  # Method not found
                pytest.skip("$/cancelRequest not implemented")
            else:
                print(f"\nCancellation failed: {cancel_data['error']['message']}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_performance(self):
        """Test basic performance characteristics."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Simple test of response time
        num_requests = 5
        method_times = {}
        
        # Test several common methods
        for method in ["server/info", "tools/list"]:
            start_time = time.time()
            
            # Send multiple requests
            for i in range(num_requests):
                response = self._send_request({
                    "jsonrpc": "2.0",
                    "id": f"perf_test_{i}",
                    "method": method,
                    "params": {}
                })
                assert response.status_code == 200
                
            end_time = time.time()
            avg_time = (end_time - start_time) / num_requests
            method_times[method] = avg_time
            
            print(f"\nAverage response time for {method}: {avg_time:.4f} seconds")
        
        # No specific assertions, just informational
        # A real performance test would have thresholds and more detailed metrics
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_custom_extensions(self):
        """Test for custom protocol extensions (if available)."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Look for any custom extensions in capabilities
        # These would typically be under a vendor-specific namespace
        custom_extensions = {}
        for key, value in self.server_capabilities.items():
            # Check for custom namespaces (typically with a $ prefix or vendor name)
            if key.startswith("$") or key.startswith("experimental/") or "/" in key:
                custom_extensions[key] = value
        
        if not custom_extensions:
            pytest.skip("No custom extensions detected")
        
        # Log the custom extensions found
        print(f"\nFound custom extensions: {json.dumps(custom_extensions, indent=2)}")
        
        # For each custom extension, try to call an associated method if it exists
        for ext_name in custom_extensions.keys():
            if "/" in ext_name:  # Likely a namespace with methods
                method_name = ext_name + "/info"  # Common pattern
                
                ext_response = self._send_request({
                    "jsonrpc": "2.0",
                    "id": f"custom_ext_{ext_name}",
                    "method": method_name,
                    "params": {}
                })
                
                if ext_response.status_code == 200:
                    ext_data = ext_response.json()
                    if "result" in ext_data:
                        print(f"\nCustom extension {method_name} response: {json.dumps(ext_data['result'], indent=2)}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_version_info(self):
        """Test detailed version information (if available)."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Send server/info request
        info_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_version_info",
            "method": "server/info",
            "params": {}
        })
        
        assert info_response.status_code == 200
        info_data = info_response.json()
        
        assert "result" in info_data
        server_info = info_data["result"]
        
        # Basic checks on server info
        assert "name" in server_info
        assert isinstance(server_info["name"], str)
        
        # Version info (optional but common)
        if "version" in server_info:
            assert isinstance(server_info["version"], str)
            print(f"\nServer version: {server_info['version']}")
        
        # Extended version info
        if "versionInfo" in server_info:
            version_info = server_info["versionInfo"]
            print(f"\nDetailed version info: {json.dumps(version_info, indent=2)}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_shutdown(self):
        """Test the shutdown method."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Send shutdown request
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