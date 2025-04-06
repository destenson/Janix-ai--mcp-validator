"""
STDIO transport implementation for MCP Protocol Validator.

This module provides an implementation of the MCPTransport interface
for communicating with MCP servers via standard input/output.
"""

import json
import sys
import subprocess
import threading
import time
from typing import Dict, Any, Optional, List, Tuple, BinaryIO, TextIO, Union
from transport.base import MCPTransport


class STDIOTransport(MCPTransport):
    """
    STDIO transport implementation for communicating with MCP servers via stdin/stdout.
    
    This class handles STDIO-specific connection and communication details.
    """
    
    def __init__(self, command: str = None, 
                process: subprocess.Popen = None,
                timeout: float = 10.0, 
                max_retries: int = 3, 
                debug: bool = False,
                use_shell: bool = True):
        """
        Initialize the STDIO transport.
        
        Args:
            command: The shell command to start the server (if process not provided)
            process: An existing subprocess.Popen instance (if command not provided)
            timeout: Response timeout in seconds
            max_retries: Maximum number of retries for broken pipes
            debug: Whether to enable debug logging
            use_shell: Whether to use shell=True when starting the process
        """
        super().__init__(debug=debug)
        self.command = command
        self.process = process
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_shell = use_shell
        self.is_running = False
        self.stderr_thread = None
        self.response_lock = threading.Lock()  # To prevent concurrent reading from stdout
        
        # Validate either command or process is provided
        if not command and not process:
            raise ValueError("Either command or process must be provided")
            
        self.log_debug(f"Initialized STDIO transport with timeout {timeout}s")
        
    def start(self) -> bool:
        """
        Start the STDIO connection to the server.
        
        Starts the server process if it doesn't exist yet.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Only start the process if it doesn't exist
            if self.process is None and self.command:
                self.log_debug(f"Starting process with command: {self.command}")
                
                # Start the process
                self.process = subprocess.Popen(
                    self.command,
                    shell=self.use_shell,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,  # Use binary mode for better control
                    bufsize=0    # Unbuffered
                )
                
                # Wait a moment for the process to initialize
                time.sleep(0.5)
                
                # Check if process started successfully
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read().decode('utf-8')
                    self.log_error(f"Process failed to start. Exit code: {self.process.returncode}")
                    self.log_error(f"Error output: {stderr}")
                    return False
                
                # Start a thread to log stderr output
                self.stderr_thread = threading.Thread(
                    target=self._read_stderr,
                    daemon=True
                )
                self.stderr_thread.start()
            
            # Mark as running
            self.is_running = True
            self.log_debug("STDIO transport started successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start STDIO transport: {str(e)}")
            return False
            
    def stop(self) -> bool:
        """
        Stop the STDIO connection to the server.
        
        Terminates the server process if we started it.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.process and self.command:  # Only terminate if we started it
            try:
                self.log_debug("Stopping process...")
                self.process.terminate()
                
                # Wait for process to terminate
                try:
                    self.process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.log_debug("Process did not terminate, force killing...")
                    self.process.kill()
                    self.process.wait(timeout=1.0)
                
                self.log_debug(f"Process stopped with exit code: {self.process.returncode}")
            except Exception as e:
                self.log_error(f"Error stopping process: {str(e)}")
                return False
                
            # Clear process reference
            self.process = None
            
        # Mark as not running
        self.is_running = False
        self.log_debug("STDIO transport stopped")
        return True
            
    def send_request(self, request: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the server via STDIO and get the response.
        
        Accepts either a pre-formatted request object or a method name and parameters.
        
        Args:
            request: Either a complete request object or a method name string
            params: Parameters to pass to the method (if request is a method name)
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            The JSON-RPC response from the server
            
        Raises:
            RuntimeError: If the transport is not started or the process is not running
        """
        if not self.is_running or not self.process:
            raise RuntimeError("STDIO transport not started")
            
        if self.process.poll() is not None:
            raise RuntimeError(f"Server process terminated unexpectedly with exit code {self.process.returncode}")
            
        # Handle the case where request is a complete request object
        if isinstance(request, dict):
            request_json = json.dumps(request)
        # Handle the case where request is a method name
        else:
            # Use provided request ID or generate one
            request_id = request_id or self.next_request_id()
            # Format the request
            params = params or {}
            method = request
            request_obj = self.format_request(method, params, request_id)
            request_json = json.dumps(request_obj)
        
        # Log the request
        self.log_debug(f"Sending request: {request_json}")
        
        # Add a newline to ensure the server processes the request
        request_bytes = (request_json + "\n").encode('utf-8')
        
        # Send the request and get the response with retries
        retries = 0
        while retries <= self.max_retries:
            try:
                # Acquire lock to prevent concurrent reading
                with self.response_lock:
                    # Send the request
                    self.process.stdin.write(request_bytes)
                    self.process.stdin.flush()
                    
                    # Read the response
                    response_line = self.process.stdout.readline()
                    
                    # If we got no response, the process might have died
                    if not response_line:
                        if self.process.poll() is not None:
                            self.log_error(f"Process terminated unexpectedly with exit code {self.process.returncode}")
                            return {
                                "jsonrpc": "2.0",
                                "id": request_id if request_id else "unknown",
                                "error": {
                                    "code": -32000,
                                    "message": f"Transport error: Process terminated with exit code {self.process.returncode}"
                                }
                            }
                        else:
                            self.log_error("Empty response received")
                            break
                    
                    # Parse the response
                    response_str = response_line.decode('utf-8').strip()
                    self.log_debug(f"Received response: {response_str}")
                    
                    try:
                        response = json.loads(response_str)
                        return response
                    except json.JSONDecodeError as e:
                        self.log_error(f"Failed to parse response as JSON: {str(e)}")
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id if request_id else "unknown",
                            "error": {
                                "code": -32700,
                                "message": f"Parse error: Invalid JSON response: {response_str}"
                            }
                        }
                
            except BrokenPipeError:
                retries += 1
                self.log_error(f"Broken pipe, retry {retries}/{self.max_retries}")
                if retries > self.max_retries:
                    break
                time.sleep(0.5)  # Wait a moment before retrying
            except Exception as e:
                self.log_error(f"Error sending request: {str(e)}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id if request_id else "unknown",
                    "error": {
                        "code": -32000,
                        "message": f"Transport error: {str(e)}"
                    }
                }
        
        # If we get here, all retries failed
        self.log_error("Failed to send request after retries")
        return {
            "jsonrpc": "2.0",
            "id": request_id if request_id else "unknown",
            "error": {
                "code": -32000,
                "message": "Transport error: Failed after retries"
            }
        }
            
    def send_notification(self, notification: Union[Dict[str, Any], str], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a JSON-RPC notification to the server via STDIO.
        
        Accepts either a pre-formatted notification object or a method name and parameters.
        
        Args:
            notification: Either a complete notification object or a method name string
            params: Parameters to pass to the method (if notification is a method name)
            
        Raises:
            RuntimeError: If the transport is not started or the process is not running
        """
        if not self.is_running or not self.process:
            raise RuntimeError("STDIO transport not started")
            
        if self.process.poll() is not None:
            raise RuntimeError(f"Server process terminated unexpectedly with exit code {self.process.returncode}")
            
        # Handle the case where notification is a complete notification object
        if isinstance(notification, dict):
            notification_json = json.dumps(notification)
        # Handle the case where notification is a method name
        else:
            # Format the notification
            params = params or {}
            method = notification
            notification_obj = self.format_notification(method, params)
            notification_json = json.dumps(notification_obj)
        
        # Log the notification
        self.log_debug(f"Sending notification: {notification_json}")
        
        # Add a newline to ensure the server processes the notification
        notification_bytes = (notification_json + "\n").encode('utf-8')
        
        # Send the notification
        retries = 0
        while retries <= self.max_retries:
            try:
                # Acquire lock to prevent concurrent writing
                with self.response_lock:
                    self.process.stdin.write(notification_bytes)
                    self.process.stdin.flush()
                return
            except BrokenPipeError:
                retries += 1
                self.log_error(f"Broken pipe, retry {retries}/{self.max_retries}")
                if retries > self.max_retries:
                    break
                time.sleep(0.5)  # Wait a moment before retrying
            except Exception as e:
                self.log_error(f"Error sending notification: {str(e)}")
                return
        
        # If we get here, all retries failed
        self.log_error("Failed to send notification after retries")
    
    def _read_stderr(self) -> None:
        """
        Background thread function to read and log stderr output from the process.
        """
        if not self.process:
            return
            
        try:
            while self.process.poll() is None:
                line = self.process.stderr.readline()
                if line:
                    stderr_line = line.decode('utf-8').strip()
                    if stderr_line:
                        self.log_debug(f"[SERVER STDERR] {stderr_line}")
        except Exception as e:
            self.log_error(f"Error reading stderr: {str(e)}")
            
    def get_exit_code(self) -> Optional[int]:
        """
        Get the exit code of the server process if it has terminated.
        
        Returns:
            The exit code or None if the process is still running
        """
        if self.process:
            return self.process.poll()
        return None
        
    def get_stderr_output(self) -> str:
        """
        Get any available stderr output from the server process.
        
        Returns:
            The stderr output as a string
        """
        if not self.process or not self.process.stderr:
            return ""
            
        try:
            # Read any available output without blocking
            output = ""
            while True:
                line = self.process.stderr.readline()
                if not line:
                    break
                output += line.decode('utf-8')
            return output
        except Exception as e:
            self.log_error(f"Error reading stderr output: {str(e)}")
            return "" 