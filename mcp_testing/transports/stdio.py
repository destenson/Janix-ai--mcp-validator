# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
STDIO Transport Adapter for MCP Testing.

This module implements the STDIO transport adapter for the MCP testing framework.
It launches an MCP server as a subprocess and communicates with it via stdin/stdout.
"""

import json
import subprocess
import time
from typing import Dict, Any, List, Optional

from mcp_testing.transports.base import MCPTransportAdapter


class StdioTransportAdapter(MCPTransportAdapter):
    """
    STDIO transport adapter for MCP testing.
    
    This adapter launches an MCP server as a subprocess and communicates with it
    via standard input/output.
    """
    
    def __init__(self, server_command: str, env_vars: Optional[Dict[str, str]] = None, 
                 timeout: float = 5.0, debug: bool = False):
        """
        Initialize the STDIO transport adapter.
        
        Args:
            server_command: The command to launch the server
            env_vars: Environment variables to pass to the server process
            timeout: Timeout for server responses in seconds
            debug: Whether to enable debug output
        """
        super().__init__(debug=debug)
        self.server_command = server_command
        self.env_vars = env_vars or {}
        self.timeout = timeout
        self.process = None
    
    def __del__(self):
        """Clean up on deletion to avoid Windows file descriptor issues"""
        # Suppress all errors during cleanup
        try:
            if hasattr(self, 'process') and self.process is not None:
                # Don't try to stop, just clean up references
                self.process = None
        except:
            pass
    
    def start(self) -> bool:
        """
        Start the server process.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_started:
            return True
            
        try:
            if self.debug:
                print(f"Starting server process: {self.server_command}")
                print(f"Environment variables: {self.env_vars}")
            
            # Split the command string into parts
            command_parts = self.server_command.split()
            
            # Launch the server process
            self.process = subprocess.Popen(
                command_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=self.env_vars
            )
            
            # Give the server a moment to start
            time.sleep(0.5)
            
            # Check if the process is still running
            if self.process.poll() is not None:
                if self.debug:
                    print(f"Server process failed to start. Exit code: {self.process.returncode}")
                    stderr = self.process.stderr.read()
                    print(f"Server error output: {stderr}")
                return False
                
            self.is_started = True
            return True
            
        except Exception as e:
            if self.debug:
                print(f"Failed to start server process: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the server process.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_started or self.process is None:
            return True
            
        try:
            # Try graceful shutdown first
            try:
                # Send shutdown request
                shutdown_request = {
                    "jsonrpc": "2.0",
                    "id": "shutdown",
                    "method": "shutdown",
                    "params": {}
                }
                self.send_request(shutdown_request)
                
                # Send exit notification
                exit_notification = {
                    "jsonrpc": "2.0",
                    "method": "exit"
                }
                self.send_notification(exit_notification)
                
                # Wait for the process to terminate
                self.process.wait(timeout=2.0)
                
            except Exception:
                # Graceful shutdown failed, force termination
                if self.debug:
                    print("Graceful shutdown failed, terminating process")
                
                self.process.terminate()
                try:
                    self.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    if self.debug:
                        print("Process did not terminate, killing")
                    try:
                        self.process.kill()
                        self.process.wait()
                    except Exception as kill_e:
                        if self.debug:
                            print(f"Failed to kill process: {str(kill_e)}")                    
            
            self.is_started = False
            # Clean up process reference without triggering Windows file descriptor issues
            if self.process is not None:
                try:
                    # Close the file handles explicitly before clearing the reference
                    if hasattr(self.process.stdin, 'close'):
                        try:
                            self.process.stdin.close()
                        except:
                            pass
                    if hasattr(self.process.stdout, 'close'):
                        try:
                            self.process.stdout.close()
                        except:
                            pass
                    if hasattr(self.process.stderr, 'close'):
                        try:
                            self.process.stderr.close()
                        except:
                            pass
                except:
                    pass
                finally:
                    self.process = None
            return True
            
        except Exception as e:
            if self.debug:
                print(f"Failed to stop server process: {str(e)}")
            return False
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and wait for a response.
        
        Args:
            request: The JSON-RPC request object
            
        Returns:
            The JSON-RPC response object
            
        Raises:
            ConnectionError: If the transport is not started or the request fails
        """
        if not self.is_started or self.process is None:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert request to JSON and add newline
            request_str = json.dumps(request) + "\n"
            
            if self.debug:
                print(f"Sending request: {request_str.strip()}")
            
            # Send the request
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Read the response
            response_str = self.process.stdout.readline().strip()
            
            if not response_str:
                raise ConnectionError("No response received from server")
                
            if self.debug:
                print(f"Received response: {response_str}")
            
            # Parse and return the response
            return json.loads(response_str)
            
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Failed to send request: {str(e)}")
    
    def send_notification(self, notification: Dict[str, Any]) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            notification: The JSON-RPC notification object
            
        Raises:
            ConnectionError: If the transport is not started or the notification fails
        """
        if not self.is_started or self.process is None:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert notification to JSON and add newline
            notification_str = json.dumps(notification) + "\n"
            
            if self.debug:
                print(f"Sending notification: {notification_str.strip()}")
            
            # Send the notification
            self.process.stdin.write(notification_str)
            self.process.stdin.flush()
            
        except Exception as e:
            raise ConnectionError(f"Failed to send notification: {str(e)}")
    
    def send_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Send a batch of JSON-RPC requests and wait for responses.
        
        Args:
            requests: A list of JSON-RPC request objects
            
        Returns:
            A list of JSON-RPC response objects
            
        Raises:
            ConnectionError: If the transport is not started or the batch request fails
        """
        if not self.is_started or self.process is None:
            raise ConnectionError("Transport not started")
            
        try:
            # Convert batch to JSON and add newline
            batch_str = json.dumps(requests) + "\n"
            
            if self.debug:
                print(f"Sending batch request: {batch_str.strip()}")
            
            # Send the batch request
            self.process.stdin.write(batch_str)
            self.process.stdin.flush()
            
            # Set up for non-blocking read with timeout
            import select
            import time
            
            start_time = time.time()
            response_str = ""
            stdout_fd = self.process.stdout.fileno()
            
            # Wait for response with timeout
            while time.time() - start_time < self.timeout:
                # Check if data is available to read
                ready, _, _ = select.select([stdout_fd], [], [], 0.1)
                if ready:
                    # Read available data
                    line = self.process.stdout.readline().strip()
                    if line:
                        response_str = line
                        break
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.05)
            
            # Check if we got a response
            if not response_str:
                raise ConnectionError(f"No response received from server within {self.timeout} seconds")
                
            if self.debug:
                print(f"Received batch response: {response_str}")
            
            # Parse and return the response
            responses = json.loads(response_str)
            
            if not isinstance(responses, list):
                raise ConnectionError("Expected batch response to be an array")
                
            return responses
            
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Failed to send batch request: {str(e)}")

    def read_stderr(self) -> str:
        """
        Read any available stderr output from the server process.
        
        Returns:
            The stderr output as a string, or an empty string if none available
        """
        if not self.is_started or self.process is None:
            return ""
            
        try:
            # Check if stderr has data available
            if self.process.stderr.readable():
                return self.process.stderr.read()
            else:
                return ""
                
        except Exception:
            return "" 
