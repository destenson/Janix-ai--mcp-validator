#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
MCP 2024-11-05 Protocol Server Implementation.

This server implements only the 2024-11-05 protocol version.
It is designed to be a clean, compliant implementation of that specific version.
"""

import os
import sys
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp-2024-11-05-stdio-server")

# Get environment variables
DEBUG = os.environ.get("MCP_DEBUG", "").lower() in ("1", "true", "yes")

# Enable debug logging if requested
if DEBUG:
    logger.setLevel(logging.DEBUG)

class MethodNotFoundError(Exception):
    """Raised when a method is not found."""
    pass

class InvalidParamsError(Exception):
    """Raised when parameters are invalid."""
    pass

class MCPServer2024_11_05:
    """MCP 2024-11-05 protocol server implementation."""
    
    def __init__(self):
        """Initialize the server."""
        self.running = True
        self.initialized = False
        self.client_capabilities = {}
        self.server_capabilities = {
            "tools": True  # Simple boolean for 2024-11-05
        }
        
        logger.info(f"MCP 2024-11-05 STDIO Server initializing")
    
    def run(self):
        """Run the server, processing stdin requests."""
        logger.info("Server started. Waiting for input...")
        
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("End of input stream, shutting down")
                    break
                self.process_request(line.strip())
            except KeyboardInterrupt:
                logger.info("Interrupted, shutting down")
                break
            except Exception as e:
                logger.error(f"Unhandled exception: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                sys.exit(1)

    def process_request(self, request_str: str):
        """Process a JSON-RPC request."""
        if not request_str:
            return
            
        try:
            if DEBUG:
                logger.debug(f"Received: {request_str}")
                
            request = json.loads(request_str)
            
            if isinstance(request, list):
                self.process_batch_request(request)
                return
            
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            logger.info(f"Method call: {method}")
            
            if request_id is not None:
                try:
                    result = self.handle_method(method, params)
                    if result is not None:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        }
                        self.send_response(response)
                except Exception as e:
                    logger.error(f"Error handling method {method}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
                    error_code = -32000
                    if isinstance(e, MethodNotFoundError):
                        error_code = -32601
                    elif isinstance(e, InvalidParamsError):
                        error_code = -32602
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": error_code,
                            "message": str(e)
                        }
                    }
                    self.send_response(response)
            else:
                try:
                    self.handle_method(method, params)
                except Exception as e:
                    logger.error(f"Error handling notification {method}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {request_str}")
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            self.send_response(response)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def send_response(self, response: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """Send a JSON-RPC response."""
        try:
            response_str = json.dumps(response)
            if DEBUG:
                logger.debug(f"Sending: {response_str}")
            print(response_str, flush=True)
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")

    def handle_method(self, method: str, params: Dict[str, Any]) -> Any:
        """Handle an MCP method call."""
        # Core protocol methods
        if method == "initialize":
            return self.handle_initialize(params)
        elif method == "initialized":
            return None
        elif method == "shutdown":
            self.running = False
            return {}
        elif method == "exit":
            self.running = False
            return None
            
        # Tools methods - using 2024-11-05 method names
        elif method == "tools/list":
            return self.handle_tools_list()
        elif method == "tools/call":
            return self.handle_tools_call(params)
            
        # Server info method
        elif method == "server/info":
            return self.handle_server_info()
            
        else:
            raise MethodNotFoundError(f"Method not found: {method}")

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the initialize method."""
        if "protocolVersion" not in params:
            raise InvalidParamsError("Missing required parameter: protocolVersion")
            
        client_version = params.get("protocolVersion", "")
        self.client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        if client_info:
            client_name = client_info.get("name", "Unknown")
            client_version_info = client_info.get("version", "Unknown")
            logger.info(f"Client: {client_name} {client_version_info}")
        
        logger.info(f"Client requested protocol version: {client_version}")
        
        if client_version != "2024-11-05":
            raise InvalidParamsError("This server only supports protocol version 2024-11-05")
        
        # Build server capabilities based on 2024-11-05 spec
        capabilities = {
            "tools": True  # Simple boolean for 2024-11-05
        }
        
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "MCP 2024-11-05 STDIO Server",
                "version": "1.0.0",
                "supportedVersions": ["2024-11-05"]
            },
            "capabilities": capabilities
        }
        
        logger.info(f"Initialize response: {json.dumps(result)}")
        return result

    def handle_server_info(self) -> Dict[str, Any]:
        """Handle the server/info method."""
        return {
            "name": "MCP 2024-11-05 STDIO Server",
            "version": "1.0.0",
            "supportedVersions": ["2024-11-05"]
        }

    def handle_tools_list(self) -> Dict[str, Any]:
        """Handle the tools/list method."""
        tools = [
            {
                "name": "echo",
                "description": "Echo the input text",
                "inputSchema": {  # Using inputSchema for 2024-11-05
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to echo"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number"
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number"
                        }
                    },
                    "required": ["a", "b"]
                }
            }
        ]
        
        return {"tools": tools}

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the tools/call method."""
        if "name" not in params:
            raise InvalidParamsError("Missing required parameter: name")
        if "arguments" not in params:
            raise InvalidParamsError("Missing required parameter: arguments")
            
        tool_name = params["name"]
        arguments = params["arguments"]
        
        # Find the tool
        tool = None
        for t in self.handle_tools_list()["tools"]:
            if t["name"] == tool_name:
                tool = t
                break
                
        if not tool:
            raise InvalidParamsError(f"Unknown tool: {tool_name}")
            
        # Validate arguments against schema
        required_args = tool["inputSchema"].get("required", [])
        for arg in required_args:
            if arg not in arguments:
                raise InvalidParamsError(f"Missing required argument: {arg}")
                
        # Call the appropriate tool function and format response according to 2024-11-05 spec
        if tool_name == "echo":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": arguments["text"]
                    }
                ]
            }
        elif tool_name == "add":
            result = float(arguments["a"]) + float(arguments["b"])
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        else:
            raise InvalidParamsError(f"Tool not implemented: {tool_name}")

def main():
    """Main entry point."""
    server = MCPServer2024_11_05()
    server.run()

if __name__ == "__main__":
    main() 