"""Async tool testing for HTTP MCP servers.

This module provides comprehensive testing for asynchronous tools in HTTP-based MCP servers,
including SSE handling, cancellation, and timeout scenarios.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import httpx
from sseclient import SSEClient

logger = logging.getLogger(__name__)

class McpHttpAsyncToolTester:
    """Async tool testing for HTTP MCP servers."""
    
    def __init__(self, server_url: str, session_id: Optional[str] = None):
        """Initialize the tester.
        
        Args:
            server_url: Base URL of the MCP server
            session_id: Optional session ID for existing session
        """
        self.server_url = server_url.rstrip("/")
        self.session_id = session_id
        self.client = httpx.AsyncClient()
        
    async def test_async_tool(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test an async tool with various scenarios.
        
        Args:
            tool_name: Name of the tool to test
            tool_spec: Tool specification from server
            
        Returns:
            Test results for the async tool
        """
        results = {
            "name": tool_name,
            "tests": []
        }
        
        # Test normal completion
        completion_result = await self._test_normal_completion(tool_name, tool_spec)
        results["tests"].append(completion_result)
        
        # Test cancellation
        cancel_result = await self._test_cancellation(tool_name, tool_spec)
        results["tests"].append(cancel_result)
        
        # Test timeout handling
        timeout_result = await self._test_timeout(tool_name, tool_spec)
        results["tests"].append(timeout_result)
        
        # Test SSE streaming
        sse_result = await self._test_sse_streaming(tool_name, tool_spec)
        results["tests"].append(sse_result)
        
        return results
        
    def _get_headers(self, include_sse: bool = False) -> Dict[str, str]:
        """Get headers for requests.
        
        Args:
            include_sse: Whether to include SSE accept header
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if include_sse else "application/json"
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers
        
    async def _test_normal_completion(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test normal completion of async tool.
        
        Args:
            tool_name: Name of the tool
            tool_spec: Tool specification
            
        Returns:
            Test result
        """
        headers = self._get_headers()
        
        # Generate valid parameters
        params = self._generate_valid_params(tool_spec.get("inputSchema", {}))
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": tool_name,
            "params": params
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.server_url}/mcp",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    return {
                        "name": "normal_completion",
                        "status": "failed",
                        "error": f"Unexpected status code: {response.status_code}"
                    }
                    
                final_response = None
                async for line in response.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        if "result" in data:
                            final_response = data
                            break
                            
                if not final_response:
                    return {
                        "name": "normal_completion",
                        "status": "failed",
                        "error": "No final result received"
                    }
                    
                return {
                    "name": "normal_completion",
                    "status": "passed",
                    "response": final_response
                }
                
        except Exception as e:
            return {
                "name": "normal_completion",
                "status": "error",
                "error": str(e)
            }
            
    async def _test_cancellation(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test cancellation of async tool.
        
        Args:
            tool_name: Name of the tool
            tool_spec: Tool specification
            
        Returns:
            Test result
        """
        headers = self._get_headers()
        params = self._generate_valid_params(tool_spec.get("inputSchema", {}))
        
        # Start the async operation
        start_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": tool_name,
            "params": params
        }
        
        try:
            # Start async operation
            response = await self.client.post(
                f"{self.server_url}/mcp",
                headers=headers,
                json=start_payload
            )
            
            if response.status_code != 200:
                return {
                    "name": "cancellation",
                    "status": "failed",
                    "error": f"Failed to start async operation: {response.status_code}"
                }
                
            data = response.json()
            operation_id = data.get("result", {}).get("operation_id")
            
            if not operation_id:
                return {
                    "name": "cancellation",
                    "status": "failed",
                    "error": "No operation ID received"
                }
                
            # Send cancellation request
            cancel_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "cancel",
                "params": {"operation_id": operation_id}
            }
            
            cancel_response = await self.client.post(
                f"{self.server_url}/mcp",
                headers=headers,
                json=cancel_payload
            )
            
            if cancel_response.status_code != 200:
                return {
                    "name": "cancellation",
                    "status": "failed",
                    "error": f"Cancellation failed: {cancel_response.status_code}"
                }
                
            return {
                "name": "cancellation",
                "status": "passed",
                "response": cancel_response.json()
            }
            
        except Exception as e:
            return {
                "name": "cancellation",
                "status": "error",
                "error": str(e)
            }
            
    async def _test_timeout(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test timeout handling of async tool.
        
        Args:
            tool_name: Name of the tool
            tool_spec: Tool specification
            
        Returns:
            Test result
        """
        headers = self._get_headers()
        params = self._generate_valid_params(tool_spec.get("inputSchema", {}))
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": tool_name,
            "params": params
        }
        
        try:
            # Set a very short timeout
            async with self.client.stream(
                "POST",
                f"{self.server_url}/mcp",
                headers=headers,
                json=payload,
                timeout=1.0  # Short timeout
            ) as response:
                if response.status_code != 200:
                    return {
                        "name": "timeout",
                        "status": "failed",
                        "error": f"Unexpected status code: {response.status_code}"
                    }
                    
                try:
                    async for line in response.aiter_lines():
                        pass
                except httpx.TimeoutException:
                    return {
                        "name": "timeout",
                        "status": "passed",
                        "message": "Timeout handled correctly"
                    }
                    
                return {
                    "name": "timeout",
                    "status": "failed",
                    "error": "Expected timeout did not occur"
                }
                
        except Exception as e:
            if isinstance(e, httpx.TimeoutException):
                return {
                    "name": "timeout",
                    "status": "passed",
                    "message": "Timeout handled correctly"
                }
            return {
                "name": "timeout",
                "status": "error",
                "error": str(e)
            }
            
    async def _test_sse_streaming(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test SSE streaming of async tool.
        
        Args:
            tool_name: Name of the tool
            tool_spec: Tool specification
            
        Returns:
            Test result
        """
        headers = self._get_headers(include_sse=True)
        params = self._generate_valid_params(tool_spec.get("inputSchema", {}))
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": tool_name,
            "params": params
        }
        
        try:
            response = await self.client.post(
                f"{self.server_url}/mcp",
                headers=headers,
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                return {
                    "name": "sse_streaming",
                    "status": "failed",
                    "error": f"Unexpected status code: {response.status_code}"
                }
                
            client = SSEClient(response.aiter_lines())
            events = []
            
            async for event in client.events():
                if event.data:
                    try:
                        data = json.loads(event.data)
                        events.append(data)
                    except json.JSONDecodeError:
                        return {
                            "name": "sse_streaming",
                            "status": "failed",
                            "error": "Invalid JSON in SSE event"
                        }
                        
            return {
                "name": "sse_streaming",
                "status": "passed",
                "events": events
            }
            
        except Exception as e:
            return {
                "name": "sse_streaming",
                "status": "error",
                "error": str(e)
            }
            
    def _generate_valid_params(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate valid parameters based on JSON schema.
        
        Args:
            schema: JSON schema for tool parameters
            
        Returns:
            Valid parameter values
        """
        params = {}
        properties = schema.get("properties", {})
        
        for prop_name, prop_spec in properties.items():
            # Generate appropriate test value based on type
            if prop_spec.get("type") == "string":
                params[prop_name] = "test_value"
            elif prop_spec.get("type") == "number":
                params[prop_name] = 42
            elif prop_spec.get("type") == "boolean":
                params[prop_name] = True
            elif prop_spec.get("type") == "array":
                params[prop_name] = []
            elif prop_spec.get("type") == "object":
                params[prop_name] = {}
                
        return params 