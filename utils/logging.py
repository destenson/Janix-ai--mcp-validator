"""
Logging utilities for the MCP protocol validator.

This module provides consistent logging functionality throughout the validator.
"""

import logging
import sys
from typing import Optional, Dict, Any

# Configure logging format
DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global flag for debug mode
_debug_mode = False


def configure_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """
    Configure the logging system.
    
    Args:
        debug: Whether to enable debug logging
        log_file: Optional path to a log file
    """
    global _debug_mode
    _debug_mode = debug
    
    # Set log level based on debug flag
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log configuration info
    logger = get_logger("config")
    logger.info(f"Logging configured: debug={debug}, log_file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with the validator's configuration.
    
    Args:
        name: The name for the logger
        
    Returns:
        A configured Logger instance
    """
    return logging.getLogger(f"mcp_validator.{name}")


def debug_enabled() -> bool:
    """
    Check if debug logging is enabled.
    
    Returns:
        True if debug logging is enabled, False otherwise
    """
    return _debug_mode


def log_request(logger: logging.Logger, data: Dict[str, Any]) -> None:
    """
    Log an outgoing MCP request.
    
    Args:
        logger: The logger to use
        data: The request data to log
    """
    if not debug_enabled():
        logger.info(f"Sending request: {data.get('method')} (id: {data.get('id')})")
    else:
        logger.debug(f"Outgoing request: {data}")


def log_response(logger: logging.Logger, response: Dict[str, Any]) -> None:
    """
    Log an incoming MCP response.
    
    Args:
        logger: The logger to use
        response: The response data to log
    """
    if not debug_enabled():
        # Basic logging for normal mode
        if "error" in response:
            logger.error(f"Received error response: {response['error'].get('message')} "
                        f"(code: {response['error'].get('code')})")
        else:
            logger.info(f"Received successful response (id: {response.get('id')})")
    else:
        # Verbose logging for debug mode
        logger.debug(f"Incoming response: {response}") 