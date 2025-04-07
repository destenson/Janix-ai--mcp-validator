#!/usr/bin/env python3
"""
Minimal MCP-compliant server implementation.

This server is designed to be a minimal reference implementation that passes all validator tests.
It supports both 2024-11-05 and 2025-03-26 protocol versions.
"""

import os
import sys
import json
import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("minimal-mcp-stdio-server")

# Get environment variables
DEFAULT_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2025-03-26")
DEBUG = os.environ.get("MCP_DEBUG", "").lower() in ("1", "true", "yes")

# Enable debug logging if requested
if DEBUG:
    logger.setLevel(logging.DEBUG)


class MinimalMCPServer:
    """Minimal MCP-compliant server implementation."""
    
    def __init__(self):
        """Initialize the server."""
        self.running = True
        self.negotiated_version = DEFAULT_PROTOCOL_VERSION
        self.client_capabilities = {}
        self.resources = {}
        
        logger.info(f"Minimal MCP STDIO Server initializing")
        logger.info(f"Default protocol version: {DEFAULT_PROTOCOL_VERSION}")
    
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
                import traceback
                logger.error(traceback.format_exc())
                sys.exit(1)
    
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
            if DEBUG:
                logger.debug(f"Received: {request_str}")
                
            request = json.loads(request_str)
            
            # Check if it's a batch request
            if isinstance(request, list):
                self.process_batch_request(request)
                return
            
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
                    if result is not None:  # Only send response for non-None results
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
                    
                    # Create error response
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
                # This is a notification
                try:
                    self.handle_method(method, params)
                except Exception as e:
                    logger.error(f"Error handling notification {method}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {request_str}")
            # Send parse error for requests
            response = {
                "jsonrpc": "2.0",
                "id": None,  # We don't know the ID for invalid JSON
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
    
    def process_batch_request(self, requests: List[Dict[str, Any]]):
        """
        Process a batch of JSON-RPC requests.
        
        Args:
            requests: List of request objects
        """
        responses = []
        
        for request in requests:
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})
            
            # Only process requests with IDs (not notifications)
            if request_id is not None:
                try:
                    result = self.handle_method(method, params)
                    if result is not None:  # Only include response for non-None results
                        responses.append({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result
                        })
                except Exception as e:
                    # Create error response
                    error_code = -32000
                    if isinstance(e, MethodNotFoundError):
                        error_code = -32601
                    elif isinstance(e, InvalidParamsError):
                        error_code = -32602
                    
                    responses.append({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": error_code,
                            "message": str(e)
                        }
                    })
            else:
                # Handle notification (no response needed)
                try:
                    self.handle_method(method, params)
                except Exception as e:
                    logger.error(f"Error handling notification {method}: {str(e)}")
        
        # Send batch response if there are any responses
        if responses:
            self.send_response(responses)
    
    def send_response(self, response: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """
        Send a JSON-RPC response.
        
        Args:
            response: The JSON-RPC response object or batch of responses
        """
        response_str = json.dumps(response)
        if DEBUG:
            logger.debug(f"Sending: {response_str}")
        
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
            MethodNotFoundError: If the method is not supported
            InvalidParamsError: If the parameters are invalid
        """
        # Core protocol methods
        if method == "initialize":
            return self.handle_initialize(params)
        elif method == "initialized":
            return None  # Notification, no response needed
        elif method == "shutdown":
            self.running = False
            return {}
        elif method == "exit":
            self.running = False
            return None  # Notification, no response needed
            
        # Tools methods
        elif method == "tools/list":
            return self.handle_tools_list(params)
        elif method == "tools/call":
            return self.handle_tools_call(params)
            
        # Server info method
        elif method == "server/info":
            return self.handle_server_info()
            
        # Resources methods (for 2025-03-26)
        elif method == "resources/list":
            return self.handle_resources_list()
        elif method == "resources/get":
            return self.handle_resources_get(params)
        elif method == "resources/create":
            return self.handle_resources_create(params)
            
        # Prompt methods (for testing prompt capabilities)
        elif method == "prompt/completion":
            return self.handle_prompt_completion(params)
        elif method == "prompt/models":
            return self.handle_prompt_models()
            
        # Unsupported method
        else:
            raise MethodNotFoundError(f"Method not found: {method}")
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the initialize method.
        
        Args:
            params: The method parameters
            
        Returns:
            The initialization result
        """
        if "protocolVersion" not in params:
            raise InvalidParamsError("Missing required parameter: protocolVersion")
            
        client_version = params.get("protocolVersion", "")
        self.client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        # Log client info
        if client_info:
            client_name = client_info.get("name", "Unknown")
            client_version_info = client_info.get("version", "Unknown")
            logger.info(f"Client: {client_name} {client_version_info}")
        
        logger.info(f"Client requested protocol version: {client_version}")
        
        # Version negotiation
        supported_versions = ["2024-11-05", "2025-03-26"]
        
        if client_version not in supported_versions:
            # If client requests an unsupported version, use the latest supported version
            self.negotiated_version = DEFAULT_PROTOCOL_VERSION
            logger.info(f"Using default version: {self.negotiated_version}")
        else:
            # Use the client's requested version
            self.negotiated_version = client_version
            logger.info(f"Using client's requested version: {self.negotiated_version}")
        
        # Build server capabilities based on negotiated version
        capabilities = {
            "tools": {
                "listChanged": self.negotiated_version == "2025-03-26"
            }
        }
        
        # Only include resources capability for 2025-03-26
        if self.negotiated_version == "2025-03-26":
            capabilities["resources"] = True
        elif self.negotiated_version == "2024-11-05" and "supports" in self.client_capabilities:
            # For 2024-11-05, use the "supports" field
            if self.client_capabilities["supports"].get("resources", False):
                capabilities["supports"] = {
                    "resources": True
                }
        
        # Determine other capabilities based on client capabilities
        if "supports" in self.client_capabilities:
            if self.client_capabilities["supports"].get("prompt", False):
                capabilities["supports"] = capabilities.get("supports", {})
                capabilities["supports"]["prompt"] = {
                    "streaming": True
                }
                
            if self.client_capabilities["supports"].get("utilities", False):
                capabilities["supports"] = capabilities.get("supports", {})
                capabilities["supports"]["utilities"] = True
                
            if self.client_capabilities["supports"].get("filesystem", False):
                capabilities["supports"] = capabilities.get("supports", {})
                capabilities["supports"]["filesystem"] = True
        
        # Return initialization result with PROPER STRUCTURE
        result = {
            "protocolVersion": self.negotiated_version,
            "serverInfo": {
                "name": "Minimal MCP STDIO Server",
                "version": "1.0.0",
                "supportedVersions": supported_versions
            },
            "capabilities": capabilities
        }
        
        logger.info(f"Initialize response: {json.dumps(result)}")
        return result
    
    def handle_server_info(self) -> Dict[str, Any]:
        """
        Handle the server/info method.
        
        Returns:
            Server information
        """
        return {
            "name": "Minimal MCP STDIO Server",
            "version": "1.0.0",
            "supportedVersions": ["2024-11-05", "2025-03-26"]
        }
    
    def handle_tools_list(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle the tools/list method.
        
        Args:
            params: Optional parameters (listChanged flag in 2025-03-26)
            
        Returns:
            List of available tools
        """
        tools = [
            {
                "name": "echo",
                "description": "Echo the input text",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "echo": {
                            "type": "string"
                        }
                    }
                }
            },
            {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "sum": {
                            "type": "number"
                        }
                    }
                }
            },
            {
                "name": "list_directory",
                "description": "List files in a directory",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "Directory path"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    },
                                    "type": {
                                        "type": "string",
                                        "enum": ["file", "directory"]
                                    }
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string"
                        }
                    }
                }
            },
            {
                "name": "write_file",
                "description": "Write a file",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content"
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "success": {
                            "type": "boolean"
                        }
                    }
                }
            }
        ]
        
        return {
            "tools": tools
        }
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the tools/call method.
        
        Args:
            params: The method parameters
            
        Returns:
            The tool result
            
        Raises:
            InvalidParamsError: If the parameters are invalid
        """
        if "name" not in params:
            raise InvalidParamsError("Missing required parameter: name")
            
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if tool_name == "echo":
            if "text" not in arguments:
                raise InvalidParamsError("Missing required argument: text")
            return {
                "content": {
                    "echo": arguments["text"]
                }
            }
        elif tool_name == "add":
            if "a" not in arguments or "b" not in arguments:
                raise InvalidParamsError("Missing required arguments: a, b")
            try:
                a = float(arguments["a"])
                b = float(arguments["b"])
                return {
                    "content": {
                        "sum": a + b
                    }
                }
            except ValueError:
                raise InvalidParamsError("Arguments must be numbers")
        elif tool_name == "list_directory":
            if "path" not in arguments:
                raise InvalidParamsError("Missing required argument: path")
            # Simulate directory listing
            path = arguments["path"]
            # In a real server, this would list actual directory contents
            items = [
                {"name": "file1.txt", "type": "file"},
                {"name": "file2.txt", "type": "file"},
                {"name": "subdir", "type": "directory"}
            ]
            return {
                "content": {
                    "items": items
                }
            }
        elif tool_name == "read_file":
            if "path" not in arguments:
                raise InvalidParamsError("Missing required argument: path")
            # Simulate file reading
            path = arguments["path"]
            # In a real server, this would read actual file contents
            content = f"This is the content of {path}"
            return {
                "content": {
                    "content": content
                }
            }
        elif tool_name == "write_file":
            if "path" not in arguments or "content" not in arguments:
                raise InvalidParamsError("Missing required arguments: path, content")
            # Simulate file writing
            path = arguments["path"]
            content = arguments["content"]
            # In a real server, this would write to actual file
            return {
                "content": {
                    "success": True
                }
            }
        else:
            raise MethodNotFoundError(f"Tool not found: {tool_name}")
    
    def handle_resources_list(self) -> Dict[str, Any]:
        """
        Handle the resources/list method.
        
        Returns:
            List of resources
        """
        resources_list = []
        for resource_id, resource in self.resources.items():
            resources_list.append({
                "id": resource_id,
                "type": resource["type"],
                "createdAt": resource["createdAt"]
            })
        
        # If there are no resources created yet, add a sample one
        if not resources_list:
            sample_id = "sample-resource-id"
            self.resources[sample_id] = {
                "type": "document",
                "data": {
                    "name": "Sample Document",
                    "content": "This is a sample document for testing."
                },
                "createdAt": int(time.time() * 1000)
            }
            resources_list.append({
                "id": sample_id,
                "type": "document",
                "createdAt": self.resources[sample_id]["createdAt"]
            })
        
        return {
            "resources": resources_list
        }
    
    def handle_resources_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the resources/get method.
        
        Args:
            params: The method parameters
            
        Returns:
            The resource details
            
        Raises:
            InvalidParamsError: If the parameters are invalid
        """
        if "id" not in params:
            raise InvalidParamsError("Missing required parameter: id")
            
        resource_id = params["id"]
        
        # Check if the resource exists
        if resource_id in self.resources:
            resource = self.resources[resource_id]
            return {
                "id": resource_id,
                "type": resource["type"],
                "data": resource["data"],
                "createdAt": resource["createdAt"]
            }
        # Handle the sample resource for backward compatibility
        elif resource_id == "sample-doc":
            sample_id = "sample-doc"
            self.resources[sample_id] = {
                "type": "document",
                "data": {
                    "name": "Sample Document",
                    "content": "This is a sample document for testing."
                },
                "createdAt": int(time.time() * 1000)
            }
            resource = self.resources[sample_id]
            return {
                "id": sample_id,
                "type": resource["type"],
                "data": resource["data"],
                "createdAt": resource["createdAt"]
            }
        else:
            raise InvalidParamsError(f"Resource not found: {resource_id}")
    
    def handle_resources_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the resources/create method.
        
        Args:
            params: The method parameters
            
        Returns:
            The created resource ID
            
        Raises:
            InvalidParamsError: If the parameters are invalid
        """
        if "type" not in params:
            raise InvalidParamsError("Missing required parameter: type")
            
        resource_type = params["type"]
        resource_data = params.get("data", {})
        
        # Generate a unique ID
        resource_id = str(uuid.uuid4())
        
        # Store the resource
        self.resources[resource_id] = {
            "type": resource_type,
            "data": resource_data,
            "createdAt": int(time.time() * 1000)  # Timestamp in milliseconds
        }
        
        return {
            "id": resource_id
        }
    
    def handle_prompt_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the prompt/completion method.
        
        Args:
            params: The method parameters
            
        Returns:
            The completion result
            
        Raises:
            InvalidParamsError: If required parameters are missing
        """
        if "prompt" not in params:
            raise InvalidParamsError("Missing required parameter: prompt")
            
        prompt = params.get("prompt")
        
        # Simulate a simple completion
        return {
            "completion": f"This is a response to: {prompt}",
            "model": "minimal-model-1.0"
        }
    
    def handle_prompt_models(self) -> Dict[str, Any]:
        """
        Handle the prompt/models method.
        
        Returns:
            List of available models
        """
        models = [
            {
                "id": "minimal-model-1.0",
                "name": "Minimal Model 1.0",
                "capabilities": {
                    "streaming": True
                }
            }
        ]
        
        return {"models": models}


class MethodNotFoundError(Exception):
    """Exception raised when a method is not found."""
    pass


class InvalidParamsError(Exception):
    """Exception raised when parameters are invalid."""
    pass


def main():
    """Main entry point."""
    try:
        server = MinimalMCPServer()
        server.run()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 