#!/usr/bin/env python3
"""
Simple STDIO-based MCP server for testing the MCP protocol validator.

This server implements the MCP protocol over STDIO and provides basic filesystem operations.
It's designed to be run in a Docker container for testing purposes.
"""

import os
import sys
import json
import logging
import base64
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mcp-stdio-server")

# Get environment variables
PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2025-03-26")
DEBUG = os.environ.get("MCP_DEBUG", "").lower() in ("1", "true", "yes")
BASE_DIR = Path(os.environ.get("MCP_BASE_DIR", "/projects"))

# Enable debug logging if requested
if DEBUG:
    logger.setLevel(logging.DEBUG)


class MCPStdioServer:
    """STDIO-based MCP server implementation."""
    
    def __init__(self):
        """Initialize the server."""
        self.request_id_counter = 1
        self.running = True
        
        logger.info(f"MCP STDIO Server initializing")
        logger.info(f"Protocol version: {PROTOCOL_VERSION}")
        logger.info(f"Base directory: {BASE_DIR}")
    
    def run(self):
        """Run the server, processing stdin requests."""
        logger.info("Server started. Waiting for input...")
        
        # Main loop
        while self.running:
            try:
                # Read a line from stdin
                line = sys.stdin.readline()
                
                # Check for EOF
                if not line:
                    logger.info("End of input stream, shutting down")
                    break
                
                # Process the request
                self.process_request(line.strip())
                
            except KeyboardInterrupt:
                logger.info("Interrupted, shutting down")
                break
            except Exception as e:
                logger.error(f"Unhandled exception: {str(e)}")
                logger.error(traceback.format_exc())
    
    def process_request(self, request_str: str):
        """
        Process a JSON-RPC request.
        
        Args:
            request_str: The JSON-RPC request string
        """
        if not request_str:
            return
            
        try:
            # Parse the request
            request = json.loads(request_str)
            
            if DEBUG:
                logger.debug(f"Received request: {json.dumps(request, indent=2)}")
            
            # Extract the request components
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            # Log the method call
            logger.info(f"Method call: {method}")
            
            # Process the request
            if request_id is not None:
                # This is a request (not a notification)
                try:
                    result = self.handle_method(method, params)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                    self.send_response(response)
                except Exception as e:
                    logger.error(f"Error handling method {method}: {str(e)}")
                    logger.error(traceback.format_exc())
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": f"Error: {str(e)}"
                        }
                    }
                    self.send_response(response)
            else:
                # This is a notification
                try:
                    self.handle_method(method, params)
                except Exception as e:
                    logger.error(f"Error handling notification {method}: {str(e)}")
                    logger.error(traceback.format_exc())
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {request_str}")
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
    
    def send_response(self, response: Dict[str, Any]):
        """
        Send a JSON-RPC response.
        
        Args:
            response: The JSON-RPC response object
        """
        response_str = json.dumps(response)
        if DEBUG:
            logger.debug(f"Sending response: {response_str}")
        
        # Write the response to stdout
        print(response_str, flush=True)
    
    def handle_method(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Handle an MCP method call.
        
        Args:
            method: The method name
            params: The method parameters
            
        Returns:
            The method result
            
        Raises:
            ValueError: If the method is not supported
        """
        # Basic protocol methods
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
            
        # Information methods
        elif method == "server/info":
            return self.handle_server_info()
            
        # Tools methods
        elif method == "tools/list":
            return self.handle_tools_list()
        elif method == "tools/call":
            return self.handle_tools_call(params)
            
        # Unsupported method
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the initialize method.
        
        Args:
            params: The method parameters
            
        Returns:
            The initialization result
        """
        client_version = params.get("protocolVersion", "")
        client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        logger.info(f"Client info: {client_info.get('name')} {client_info.get('version')}")
        logger.info(f"Client requested protocol version: {client_version}")
        
        # Determine negotiated version (use client's requested version if supported)
        negotiated_version = PROTOCOL_VERSION
        if client_version in ["2024-11-05", "2025-03-26"]:
            negotiated_version = client_version
        
        logger.info(f"Negotiated protocol version: {negotiated_version}")
        
        # Return server information and capabilities
        return {
            "protocolVersion": negotiated_version,
            "serverInfo": {
                "name": "MCP STDIO Test Server",
                "version": "1.0.0",
                "supportedVersions": ["2024-11-05", "2025-03-26"]
            },
            "capabilities": {
                "filesystem": True,
                "tools": {
                    "listChanged": True
                }
            }
        }
    
    def handle_server_info(self) -> Dict[str, Any]:
        """
        Handle the server/info method.
        
        Returns:
            Server information
        """
        return {
            "name": "MCP STDIO Test Server",
            "version": "1.0.0",
            "supportedVersions": ["2024-11-05", "2025-03-26"]
        }
    
    def handle_tools_list(self) -> Dict[str, Any]:
        """
        Handle the tools/list method.
        
        Returns:
            List of available tools
        """
        tools = [
            {
                "name": "list_directory",
                "description": "List the contents of a directory",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    }
                },
                "returnType": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "size": {"type": "integer"}
                        }
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "array"}
                    }
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"}
                    }
                }
            }
        ]
        
        return {"tools": tools}
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/call method.
        
        Args:
            params: The method parameters
            
        Returns:
            The tool call result
            
        Raises:
            ValueError: If the tool is not supported or parameters are invalid
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Tool call: {tool_name}")
        
        if tool_name == "list_directory":
            return self.handle_list_directory(arguments)
        elif tool_name == "read_file":
            return self.handle_read_file(arguments)
        elif tool_name == "write_file":
            return self.handle_write_file(arguments)
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")
    
    def handle_list_directory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the list_directory tool.
        
        Args:
            arguments: The tool arguments
            
        Returns:
            Directory listing
            
        Raises:
            ValueError: If the path is invalid
        """
        path = arguments.get("path")
        if not path:
            raise ValueError("Path is required")
        
        # Check if the path is allowed
        full_path = BASE_DIR / path.lstrip("/")
        if not str(full_path).startswith(str(BASE_DIR)):
            raise ValueError(f"Path {path} is outside the allowed directory")
        
        if not full_path.exists():
            raise ValueError(f"Path {path} does not exist")
        
        if not full_path.is_dir():
            raise ValueError(f"Path {path} is not a directory")
        
        # List the directory contents
        entries = []
        for entry in full_path.iterdir():
            entry_type = "directory" if entry.is_dir() else "file"
            size = entry.stat().st_size if entry.is_file() else 0
            entries.append({
                "name": entry.name,
                "type": entry_type,
                "size": size
            })
        
        return {"content": entries}
    
    def handle_read_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the read_file tool.
        
        Args:
            arguments: The tool arguments
            
        Returns:
            File content
            
        Raises:
            ValueError: If the path is invalid
        """
        path = arguments.get("path")
        if not path:
            raise ValueError("Path is required")
        
        # Check if the path is allowed
        full_path = BASE_DIR / path.lstrip("/")
        if not str(full_path).startswith(str(BASE_DIR)):
            raise ValueError(f"Path {path} is outside the allowed directory")
        
        if not full_path.exists():
            raise ValueError(f"Path {path} does not exist")
        
        if not full_path.is_file():
            raise ValueError(f"Path {path} is not a file")
        
        # Read the file
        content = []
        try:
            # Check if the file is binary
            is_binary = False
            with open(full_path, "rb") as f:
                sample = f.read(1024)
                try:
                    sample.decode("utf-8")
                except UnicodeDecodeError:
                    is_binary = True
            
            if is_binary:
                # Binary file - return as base64
                with open(full_path, "rb") as f:
                    data = f.read()
                    base64_data = base64.b64encode(data).decode("ascii")
                    content.append({"type": "base64", "data": base64_data})
            else:
                # Text file - return as text
                with open(full_path, "r") as f:
                    text = f.read()
                    content.append({"type": "text", "text": text})
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
        
        return {"content": content}
    
    def handle_write_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the write_file tool.
        
        Args:
            arguments: The tool arguments
            
        Returns:
            Success status
            
        Raises:
            ValueError: If the path is invalid
        """
        path = arguments.get("path")
        content = arguments.get("content")
        
        if not path:
            raise ValueError("Path is required")
        
        if content is None:
            raise ValueError("Content is required")
        
        # Check if the path is allowed
        full_path = BASE_DIR / path.lstrip("/")
        if not str(full_path).startswith(str(BASE_DIR)):
            raise ValueError(f"Path {path} is outside the allowed directory")
        
        # Create parent directories if needed
        os.makedirs(full_path.parent, exist_ok=True)
        
        # Write the file
        try:
            with open(full_path, "w") as f:
                f.write(content)
        except Exception as e:
            raise ValueError(f"Error writing file: {str(e)}")
        
        return {"success": True}


def main():
    """Run the STDIO server."""
    server = MCPStdioServer()
    server.run()


if __name__ == "__main__":
    main() 