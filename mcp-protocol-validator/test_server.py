#!/usr/bin/env python
"""
Simple MCP Test Server

This is a minimal implementation of an MCP server for testing and debugging
the MCP Protocol Validator. It supports both STDIO and HTTP transport and
can be configured to behave in specific ways for testing edge cases.

Usage:
    python test_server.py [--http] [--port PORT] [--version VERSION] [--fail-rate RATE]
                          [--delay DELAY] [--debug] [--max-depth DEPTH]

Options:
    --http          Run as HTTP server instead of STDIO (default: STDIO)
    --port PORT     Port to use for HTTP server (default: 8080)
    --version VER   Protocol version to implement (default: 2025-03-26)
    --fail-rate N   Make every Nth request fail (default: 0, no failures)
    --delay SEC     Add delay to responses in seconds (default: 0)
    --debug         Enable debug output
    --max-depth N   Maximum directory recursion depth (default: 5)
"""

import argparse
import json
import logging
import random
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, Union, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("mcp_test_server")

# Default settings
DEFAULT_VERSION = "2025-03-26"
DEFAULT_HTTP_PORT = 8080
REQUEST_COUNT = 0  # Global counter for tracking requests
MAX_RECURSION_DEPTH = 5  # Maximum recursion depth for directories
                         # Note: The actual MCP filesystem server (Node.js implementation)
                         # doesn't have an explicit recursion depth limit, but can hit
                         # node's call stack limit for deeply nested directories.
                         # This test server simulates that behavior with a configurable limit.

class MCPTestServer:
    """
    A simple MCP server implementation for testing purposes.
    """
    
    def __init__(
        self, 
        protocol_version: str = DEFAULT_VERSION,
        fail_rate: int = 0,
        response_delay: float = 0.0,
        debug: bool = False,
        max_recursion_depth: int = MAX_RECURSION_DEPTH
    ):
        """
        Initialize the MCP test server.
        
        Args:
            protocol_version: MCP protocol version to implement
            fail_rate: Make every Nth request fail (0 for no failures)
            response_delay: Add delay to responses in seconds
            debug: Enable debug output
            max_recursion_depth: Maximum recursion depth for directories
        """
        self.protocol_version = protocol_version
        self.fail_rate = fail_rate
        self.response_delay = response_delay
        self.max_recursion_depth = max_recursion_depth
        
        if debug:
            logger.setLevel(logging.DEBUG)
        
        # Protocol-specific configurations
        self.supports = {
            "filesystem": True,
            "chat": True,
            "terminal": True
        }
        
        logger.info(f"MCP Test Server initialized with version {protocol_version}")
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an MCP request and return a response.
        
        Args:
            request_data: The MCP JSON-RPC request
            
        Returns:
            The MCP JSON-RPC response
        """
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        
        # Log the request
        logger.debug(f"Received request ({REQUEST_COUNT}): {json.dumps(request_data)}")
        
        # Extract request information
        method = request_data.get("method", "")
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        # Add artificial delay if configured
        if self.response_delay > 0:
            logger.debug(f"Adding artificial delay of {self.response_delay}s")
            time.sleep(self.response_delay)
        
        # Simulate failures if configured
        if self.fail_rate > 0 and REQUEST_COUNT % self.fail_rate == 0:
            logger.info(f"Simulating failure for request {REQUEST_COUNT} (every {self.fail_rate}th request)")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"Simulated failure (request {REQUEST_COUNT})"
                }
            }
        
        # Handle MCP methods
        if method == "initialize":
            return self._handle_initialize(params, request_id)
        elif method == "filesystem.ls":
            return self._handle_filesystem_ls(params, request_id)
        elif method == "filesystem.stat":
            return self._handle_filesystem_stat(params, request_id)
        elif method == "filesystem.read":
            return self._handle_filesystem_read(params, request_id)
        elif method == "filesystem.write":
            return self._handle_filesystem_write(params, request_id)
        elif method == "filesystem.mkdir":
            return self._handle_filesystem_mkdir(params, request_id)
        elif method == "filesystem.rm":
            return self._handle_filesystem_rm(params, request_id)
        else:
            logger.warning(f"Unsupported method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def _handle_initialize(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle initialize request"""
        logger.info("Handling initialize request")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "capabilities": {
                    "supports": self.supports,
                    "version": self.protocol_version
                }
            }
        }
    
    def _handle_filesystem_ls(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.ls request"""
        path = params.get("path", "/")
        logger.info(f"Handling filesystem.ls for path: {path}")
        
        # Check if the path is too deep (by counting directory separators)
        path_depth = path.count("/")
        if path_depth > self.max_recursion_depth:
            logger.warning(f"Recursion depth exceeded for path: {path} (depth: {path_depth}, max: {self.max_recursion_depth})")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Maximum recursion depth exceeded ({path_depth} > {self.max_recursion_depth})",
                    "data": {
                        "path": path,
                        "current_depth": path_depth,
                        "max_depth": self.max_recursion_depth,
                        "recommendation": "Use a more specific path or increase the server's recursion depth limit"
                    }
                }
            }
        
        # Simulate a virtual filesystem
        entries = []
        
        if path == "/":
            entries = [
                {"name": "folder1", "type": "directory"},
                {"name": "folder2", "type": "directory"},
                {"name": "file1.txt", "type": "file", "size": 1024},
                {"name": "file2.txt", "type": "file", "size": 2048}
            ]
        elif path == "/folder1":
            entries = [
                {"name": "subfolder", "type": "directory"},
                {"name": "test.txt", "type": "file", "size": 512}
            ]
        elif path == "/folder2":
            entries = [
                {"name": "config.json", "type": "file", "size": 256}
            ]
        elif path == "/folder1/subfolder":
            entries = [
                {"name": "deep1", "type": "directory"},
                {"name": "deep_file.txt", "type": "file", "size": 128}
            ]
        elif path.startswith("/folder1/subfolder/deep") and path.count("/") <= self.max_recursion_depth:
            # Generate deeper structures for testing
            entries = [
                {"name": f"level_{path.count('/')}", "type": "directory"},
                {"name": f"level_file_{path.count('/')}.txt", "type": "file", "size": 64}
            ]
        else:
            # Path not found
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Path not found: {path}"
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "entries": entries
            }
        }
    
    def _handle_filesystem_stat(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.stat request"""
        path = params.get("path", "")
        logger.info(f"Handling filesystem.stat for path: {path}")
        
        # Check for recursion depth
        path_depth = path.count("/")
        if path_depth > self.max_recursion_depth:
            logger.warning(f"Recursion depth exceeded for stat on path: {path}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Maximum recursion depth exceeded ({path_depth} > {self.max_recursion_depth})",
                    "data": {
                        "path": path,
                        "current_depth": path_depth,
                        "max_depth": self.max_recursion_depth,
                        "recommendation": "Use a more specific path or increase the server's recursion depth limit"
                    }
                }
            }
        
        # Simulate file stats
        if path == "/file1.txt":
            stat_result = {
                "type": "file",
                "size": 1024,
                "mtime": "2023-01-01T12:00:00Z"
            }
        elif path == "/file2.txt":
            stat_result = {
                "type": "file",
                "size": 2048,
                "mtime": "2023-01-02T12:00:00Z"
            }
        elif path == "/folder1":
            stat_result = {
                "type": "directory",
                "mtime": "2023-01-03T12:00:00Z"
            }
        elif path == "/folder2":
            stat_result = {
                "type": "directory",
                "mtime": "2023-01-04T12:00:00Z"
            }
        else:
            # Path not found
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Path not found: {path}"
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": stat_result
        }
    
    def _handle_filesystem_read(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.read request"""
        path = params.get("path", "")
        logger.info(f"Handling filesystem.read for path: {path}")
        
        # Simulate file contents
        if path == "/file1.txt":
            content = "This is the content of file1.txt"
        elif path == "/file2.txt":
            content = "This is the content of file2.txt"
        elif path == "/folder1/test.txt":
            content = "This is a test file in folder1"
        elif path == "/folder2/config.json":
            content = '{"name": "config", "version": "1.0"}'
        else:
            # Path not found
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Path not found: {path}"
                }
            }
        
        # Handle read with offset and limit
        offset = params.get("offset", 0)
        limit = params.get("limit", len(content))
        
        # Ensure offset and limit are valid
        if offset < 0 or offset > len(content):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid offset: {offset}"
                }
            }
        
        # Apply offset and limit
        content_slice = content[offset:offset + limit]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": content_slice
            }
        }
    
    def _handle_filesystem_write(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.write request"""
        path = params.get("path", "")
        content = params.get("content", "")
        logger.info(f"Handling filesystem.write for path: {path} (content length: {len(content)})")
        
        # Simulate successful write
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "success": True
            }
        }
    
    def _handle_filesystem_mkdir(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.mkdir request"""
        path = params.get("path", "")
        logger.info(f"Handling filesystem.mkdir for path: {path}")
        
        # Simulate successful directory creation
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "success": True
            }
        }
    
    def _handle_filesystem_rm(self, params: Dict[str, Any], request_id: Union[str, int]) -> Dict[str, Any]:
        """Handle filesystem.rm request"""
        path = params.get("path", "")
        recursive = params.get("recursive", False)
        logger.info(f"Handling filesystem.rm for path: {path} (recursive: {recursive})")
        
        # Simulate successful removal
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "success": True
            }
        }


class HttpHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the MCP server"""
    
    def __init__(self, *args, **kwargs):
        self.server_instance = kwargs.pop('server_instance', None)
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request_data = json.loads(post_data)
            response_data = self.server_instance.handle_request(request_data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response_json = json.dumps(response_data)
            self.wfile.write(response_json.encode('utf-8'))
            
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32000,
                    "message": f"Internal server error: {str(e)}"
                }
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))


def run_http_server(server_instance, port=DEFAULT_HTTP_PORT):
    """Run the MCP server over HTTP"""
    
    # Create a custom handler class that has access to our server instance
    def handler_factory(*args, **kwargs):
        return HttpHandler(*args, server_instance=server_instance, **kwargs)
    
    # Start the HTTP server
    http_server = HTTPServer(('localhost', port), handler_factory)
    logger.info(f"Starting HTTP server on port {port}")
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        http_server.server_close()


def run_stdio_server(server_instance):
    """Run the MCP server over STDIO"""
    logger.info("Starting STDIO server")
    
    try:
        for line in sys.stdin:
            # Skip empty lines
            if not line.strip():
                continue
            
            try:
                # Parse the JSON-RPC request
                request_data = json.loads(line)
                
                # Process the request
                response_data = server_instance.handle_request(request_data)
                
                # Send the response with a newline
                response_json = json.dumps(response_data)
                print(response_json, flush=True)
                
            except json.JSONDecodeError as e:
                # Handle JSON parsing errors
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except Exception as e:
                # Handle any other errors
                logger.error(f"Error processing request: {str(e)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32000,
                        "message": f"Internal server error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except BrokenPipeError:
        logger.error("Broken pipe detected. Client disconnected.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")


def main():
    """Main entry point for the test server"""
    parser = argparse.ArgumentParser(description="Simple MCP Test Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server instead of STDIO")
    parser.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT, help=f"HTTP server port (default: {DEFAULT_HTTP_PORT})")
    parser.add_argument("--version", type=str, default=DEFAULT_VERSION, help=f"Protocol version to implement (default: {DEFAULT_VERSION})")
    parser.add_argument("--fail-rate", type=int, default=0, help="Make every Nth request fail (default: 0, no failures)")
    parser.add_argument("--delay", type=float, default=0.0, help="Add delay to responses in seconds (default: 0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--max-depth", type=int, default=MAX_RECURSION_DEPTH, 
                       help=f"Maximum directory recursion depth for filesystem operations (default: {MAX_RECURSION_DEPTH})")
    
    args = parser.parse_args()
    
    # Create server instance
    server = MCPTestServer(
        protocol_version=args.version,
        fail_rate=args.fail_rate,
        response_delay=args.delay,
        debug=args.debug,
        max_recursion_depth=args.max_depth
    )
    
    # Run the appropriate server type
    if args.http:
        run_http_server(server, args.port)
    else:
        run_stdio_server(server)


if __name__ == "__main__":
    main() 