"""
MCP STDIO Tester module for testing STDIO server implementations.
"""

import json
import logging
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from mcp_testing.stdio.utils import check_command_exists, verify_python_server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCPStdioTester")


class MCPStdioTester:
    """Tester for MCP STDIO server implementations."""
    
    def __init__(self, server_command: str, args: List[str] = None, debug: bool = False):
        """Initialize the tester.
        
        Args:
            server_command: Command to run the server
            args: Additional arguments to pass to the server command
            debug: Enable debug output
        """
        self.server_command = server_command
        self.args = args or []
        self.debug = debug
        self.protocol_version = "2025-03-26"
        self.server_process = None
        self.client_id = 1
        self.session_id = None
        
        # Configure logging based on debug flag
        if debug:
            logger.setLevel(logging.DEBUG)
        
            # Only log if debug is enabled and using the instance args (which is guaranteed to be a list)
            logger.debug(f"Initialized tester with command: {server_command} {' '.join(self.args)}")
    
    def start_server(self) -> bool:
        """Start the server process.
        
        Returns:
            True if server started successfully, False otherwise
        """
        try:
            # Check if the command exists
            cmd_parts = shlex.split(self.server_command)
            if not check_command_exists(cmd_parts[0]):
                logger.error(f"Command not found: {cmd_parts[0]}")
                return False
            
            # If it's a Python server, verify it exists and is valid
            if cmd_parts[0] in ["python", "python3"] and len(cmd_parts) > 1:
                server_script = cmd_parts[1]
                if not verify_python_server(server_script):
                    return False
            
            # Build command
            cmd = cmd_parts + self.args
            logger.debug(f"Starting server with command: {' '.join(cmd)}")
            
            # Start server process with pipes for stdin/stdout
            self.server_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Wait a short time for server to start
            time.sleep(0.5)
            
            if self.server_process.poll() is not None:
                # Server exited prematurely
                returncode = self.server_process.poll()
                stderr = self.server_process.stderr.read()
                logger.error(f"Server exited with code {returncode}. Error: {stderr}")
                return False
            
            logger.info("Server started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    def stop_server(self) -> None:
        """Stop the server process."""
        if self.server_process:
            try:
                logger.debug("Sending shutdown request to server")
                # Send shutdown request if possible
                try:
                    self._send_request("shutdown", {})
                except Exception:
                    pass
                
                logger.debug("Terminating server process")
                self.server_process.terminate()
                
                # Wait for process to terminate
                try:
                    self.server_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("Server did not terminate within timeout, killing forcefully")
                    self.server_process.kill()
                
                # Close pipes
                self.server_process.stdin.close()
                self.server_process.stdout.close()
                self.server_process.stderr.close()
                
                logger.info("Server stopped")
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
            
            self.server_process = None
    
    def _send_request(self, method: str, params: Dict[str, Any], request_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Send a request to the server and receive a response.
        
        Args:
            method: Method name
            params: Method parameters
            request_id: Request ID (generated if None)
            
        Returns:
            Tuple of (success, response)
        """
        if not self.server_process:
            logger.error("Cannot send request - server not running")
            return False, {"error": "Server not running"}
        
        # Generate request ID if not provided
        if request_id is None:
            request_id = self.client_id
            self.client_id += 1
        
        # Build request object
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        # Add session ID if we have one
        if self.session_id and method != "initialize":
            request["sessionId"] = self.session_id
        
        # Convert to JSON and send
        request_json = json.dumps(request)
        if self.debug:
            logger.debug(f"Sending request: {request_json}")
        
        try:
            # Send request with newline
            self.server_process.stdin.write(request_json + "\n")
            self.server_process.stdin.flush()
            
            # Read response
            response_json = self.server_process.stdout.readline()
            
            if not response_json:
                logger.error("Server closed connection without sending a response")
                return False, {"error": "No response received"}
            
            # Parse response
            response = json.loads(response_json)
            if self.debug:
                logger.debug(f"Received response: {response_json}")
            
            # Check for errors
            if "error" in response:
                logger.error(f"Server returned error: {response['error']}")
                return False, response
            
            return True, response
        
        except Exception as e:
            logger.error(f"Error communicating with server: {e}")
            return False, {"error": str(e)}
    
    def initialize(self) -> bool:
        """Initialize the server.
        
        Returns:
            True if initialization successful, False otherwise
        """
        params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": {
                "name": "MCP STDIO Tester",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "asyncSupported": True
                }
            }
        }
        
        logger.info("Initializing server")
        success, response = self._send_request("initialize", params)
        
        if success and "result" in response:
            # Store session ID if provided
            if "sessionId" in response["result"]:
                self.session_id = response["result"]["sessionId"]
                logger.info(f"Server initialized with session ID: {self.session_id}")
            else:
                logger.info("Server initialized (no session ID provided)")
            
            return True
        else:
            logger.error("Failed to initialize server")
            return False
    
    def list_tools(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """List available tools.
        
        Returns:
            Tuple of (success, tools_list)
        """
        logger.info("Listing tools")
        success, response = self._send_request("listTools", {})
        
        if success and "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            logger.info(f"Server reported {len(tools)} available tools")
            return True, tools
        else:
            logger.error("Failed to list tools")
            return False, []
    
    def test_echo_tool(self) -> bool:
        """Test the echo tool.
        
        Returns:
            True if test passed, False otherwise
        """
        test_message = "Hello, MCP STDIO server!"
        logger.info(f"Testing echo tool with message: '{test_message}'")
        
        success, response = self._send_request("invokeToolCall", {
            "toolCall": {
                "id": "echo-test",
                "name": "echo",
                "parameters": {
                    "message": test_message
                }
            }
        })
        
        if success and "result" in response and "result" in response["result"]:
            echo_result = response["result"]["result"]
            if echo_result == test_message:
                logger.info("Echo tool test passed")
                return True
            else:
                logger.error(f"Echo tool returned unexpected result: {echo_result}")
                return False
        else:
            logger.error("Failed to invoke echo tool")
            return False
    
    def test_add_tool(self) -> bool:
        """Test the add tool.
        
        Returns:
            True if test passed, False otherwise
        """
        logger.info("Testing add tool with numbers 5 and 7")
        
        success, response = self._send_request("invokeToolCall", {
            "toolCall": {
                "id": "add-test",
                "name": "add",
                "parameters": {
                    "a": 5,
                    "b": 7
                }
            }
        })
        
        if success and "result" in response and "result" in response["result"]:
            add_result = response["result"]["result"]
            if add_result == 12:
                logger.info("Add tool test passed")
                return True
            else:
                logger.error(f"Add tool returned unexpected result: {add_result}")
                return False
        else:
            logger.error("Failed to invoke add tool")
            return False
    
    def test_async_sleep_tool(self) -> bool:
        """Test the async sleep tool.
        
        Returns:
            True if test passed, False otherwise
        """
        sleep_duration = 1  # 1 second
        logger.info(f"Testing async sleep tool with duration: {sleep_duration}s")
        
        # Start async tool call
        success, response = self._send_request("invokeToolCall", {
            "toolCall": {
                "id": "sleep-test",
                "name": "sleep",
                "parameters": {
                    "duration": sleep_duration
                }
            }
        })
        
        if not success or "result" not in response or "status" not in response["result"]:
            logger.error("Failed to invoke async sleep tool")
            return False
        
        # Check if status is running
        if response["result"]["status"] != "running":
            logger.error(f"Unexpected status from async tool: {response['result']['status']}")
            return False
        
        # Get tool call ID
        tool_call_id = response["result"]["toolCallId"]
        logger.debug(f"Async tool call started with ID: {tool_call_id}")
        
        # Poll for completion
        start_time = time.time()
        max_wait = sleep_duration + 3  # Add buffer
        
        while time.time() - start_time < max_wait:
            success, response = self._send_request("getToolCallStatus", {
                "toolCallId": tool_call_id
            })
            
            if not success or "result" not in response or "status" not in response["result"]:
                logger.error("Failed to get tool call status")
                return False
            
            status = response["result"]["status"]
            logger.debug(f"Tool call status: {status}")
            
            if status == "completed":
                logger.info("Async sleep tool completed successfully")
                return True
            
            if status == "failed":
                logger.error("Async sleep tool failed")
                return False
            
            # Wait before polling again
            time.sleep(0.2)
        
        logger.error("Timed out waiting for async tool to complete")
        return False
    
    def run_all_tests(self) -> bool:
        """Run all tests.
        
        Returns:
            True if all tests passed, False otherwise
        """
        logger.info("Starting MCP STDIO server tests")
        
        try:
            # Start server
            if not self.start_server():
                logger.error("Failed to start server, aborting tests")
                return False
            
            # Initialize server
            if not self.initialize():
                logger.error("Failed to initialize server, aborting tests")
                return False
            
            # List tools
            success, tools = self.list_tools()
            if not success:
                logger.error("Failed to list tools, aborting tests")
                return False
            
            # Check if required tools are available
            tool_names = [tool["name"] for tool in tools]
            logger.debug(f"Available tools: {', '.join(tool_names)}")
            
            # Test echo tool if available
            if "echo" in tool_names:
                echo_result = self.test_echo_tool()
                if not echo_result:
                    logger.error("Echo tool test failed")
                    return False
            else:
                logger.warning("Echo tool not available, skipping test")
            
            # Test add tool if available
            if "add" in tool_names:
                add_result = self.test_add_tool()
                if not add_result:
                    logger.error("Add tool test failed")
                    return False
            else:
                logger.warning("Add tool not available, skipping test")
            
            # Test async sleep tool if available
            if "sleep" in tool_names:
                sleep_result = self.test_async_sleep_tool()
                if not sleep_result:
                    logger.error("Async sleep tool test failed")
                    return False
            else:
                logger.warning("Sleep tool not available, skipping async test")
            
            logger.info("All tests completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during testing: {e}")
            return False
        
        finally:
            # Clean up
            self.stop_server() 