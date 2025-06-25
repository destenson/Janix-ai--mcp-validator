"""Dynamic tool testing for HTTP MCP servers.

This module provides comprehensive dynamic tool discovery and testing capabilities
for HTTP-based MCP servers, similar to the STDIO testing framework.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)

class McpHttpDynamicToolTester:
    """Dynamic tool testing for HTTP MCP servers."""
    
    def __init__(self, server_url: str, session_id: Optional[str] = None):
        """Initialize the tester.
        
        Args:
            server_url: Base URL of the MCP server
            session_id: Optional session ID for existing session
        """
        self.server_url = server_url.rstrip("/")
        self.session_id = session_id
        self.client = httpx.Client()
        self.discovered_tools: Dict[str, Any] = {}
        
    async def discover_tools(self) -> Dict[str, Any]:
        """Discover available tools from the server.
        
        Returns:
            Dictionary of tool names to tool specifications
        """
        headers = self._get_headers()
        
        # Request server capabilities
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "client_info": {"name": "HTTP Dynamic Tool Tester"},
                "client_capabilities": {
                    "protocol_versions": ["2025-06-18", "2025-03-26", "2024-11-05"]
                }
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/mcp",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to discover tools: {response.status_code}")
            
        data = response.json()
        if "result" not in data:
            raise Exception("Invalid response format")
            
        # Extract tools from capabilities
        self.discovered_tools = data["result"].get("server_capabilities", {}).get("tools", {})
        return self.discovered_tools
        
    async def test_tool(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific tool with generated test cases.
        
        Args:
            tool_name: Name of the tool to test
            tool_spec: Tool specification from server
            
        Returns:
            Test results for the tool
        """
        results = {
            "name": tool_name,
            "tests": []
        }
        
        # Generate test cases based on tool schema
        test_cases = self._generate_test_cases(tool_spec)
        
        for test_case in test_cases:
            test_result = await self._run_tool_test(tool_name, test_case)
            results["tests"].append(test_result)
            
        return results
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers
        
    def _generate_test_cases(self, tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test cases based on tool specification.
        
        Args:
            tool_spec: Tool specification from server
            
        Returns:
            List of test cases to run
        """
        test_cases = []
        
        # Get input schema
        input_schema = tool_spec.get("inputSchema", {})
        
        # Generate valid test case
        valid_case = self._generate_valid_params(input_schema)
        test_cases.append({
            "name": "valid_parameters",
            "params": valid_case,
            "expected_status": "success"
        })
        
        # Generate invalid test cases
        invalid_cases = self._generate_invalid_params(input_schema)
        for case in invalid_cases:
            test_cases.append({
                "name": f"invalid_{case['type']}",
                "params": case["params"],
                "expected_status": "error"
            })
            
        return test_cases
        
    async def _run_tool_test(self, tool_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case for a tool.
        
        Args:
            tool_name: Name of the tool
            test_case: Test case specification
            
        Returns:
            Test result
        """
        headers = self._get_headers()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": tool_name,
            "params": test_case["params"]
        }
        
        try:
            response = self.client.post(
                f"{self.server_url}/mcp",
                headers=headers,
                json=payload
            )
            
            result = {
                "name": test_case["name"],
                "status": "passed" if response.status_code == 200 else "failed",
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            # Validate response format
            if response.status_code == 200:
                self._validate_response(result, test_case["expected_status"])
                
            return result
            
        except Exception as e:
            return {
                "name": test_case["name"],
                "status": "error",
                "error": str(e)
            }
            
    def _validate_response(self, result: Dict[str, Any], expected_status: str):
        """Validate response format and update test result.
        
        Args:
            result: Test result to update
            expected_status: Expected status (success/error)
        """
        response = result["response"]
        
        # Check JSONRPC format
        if "jsonrpc" not in response or response["jsonrpc"] != "2.0":
            result["status"] = "failed"
            result["error"] = "Invalid JSONRPC format"
            return
            
        # Check ID field
        if "id" not in response or not isinstance(response["id"], (int, str)):
            result["status"] = "failed"
            result["error"] = "Missing or invalid ID"
            return
            
        # Check result/error based on expected status
        if expected_status == "success":
            if "result" not in response:
                result["status"] = "failed"
                result["error"] = "Missing result field"
        else:
            if "error" not in response:
                result["status"] = "failed"
                result["error"] = "Missing error field"
                
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
        
    def _generate_invalid_params(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate invalid test cases based on JSON schema.
        
        Args:
            schema: JSON schema for tool parameters
            
        Returns:
            List of invalid test cases
        """
        invalid_cases = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Missing required parameter
        for req_param in required:
            case = self._generate_valid_params(schema)
            del case[req_param]
            invalid_cases.append({
                "type": f"missing_{req_param}",
                "params": case
            })
            
        # Wrong type for parameters
        for prop_name, prop_spec in properties.items():
            case = self._generate_valid_params(schema)
            if prop_spec.get("type") == "string":
                case[prop_name] = 42  # Wrong type
            elif prop_spec.get("type") == "number":
                case[prop_name] = "not_a_number"
            invalid_cases.append({
                "type": f"wrong_type_{prop_name}",
                "params": case
            })
            
        return invalid_cases 