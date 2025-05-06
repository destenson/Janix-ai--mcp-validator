#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Launcher for MCP HTTP Server

This script allows running either the original or the new version of the MCP HTTP server.
"""

import argparse
import logging
import os
import sys
import importlib.util
from typing import Optional


def setup_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        debug: Whether to enable debug logging.
        log_file: The log file to write to.
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            logging.error(f"Error setting up log file {log_file}: {str(e)}")


def run_original_server(host: str, port: int, debug: bool, auto_port: bool) -> None:
    """
    Run the original MCP HTTP server.
    
    Args:
        host: The host to bind to.
        port: The port to bind to.
        debug: Whether to enable debug logging.
        auto_port: Whether to automatically find an available port.
    """
    from minimal_http_server.minimal_http_server import main as original_main
    
    # Call the original main function with the specified arguments
    sys.argv = [
        sys.argv[0],
        "--host", host,
        "--port", str(port)
    ]
    
    if debug:
        sys.argv.append("--debug")
    
    if auto_port:
        sys.argv.append("--auto-port")
    
    original_main()


def run_new_server(host: str, port: int, debug: bool, auto_port: bool, log_file: Optional[str] = None) -> None:
    """
    Run the new MCP HTTP server.
    
    Args:
        host: The host to bind to.
        port: The port to bind to.
        debug: Whether to enable debug logging.
        auto_port: Whether to automatically find an available port.
        log_file: The log file to write to.
    """
    try:
        from minimal_http_server.v2.server import run_server
    except ImportError:
        logging.error("Could not import new server implementation.")
        logging.error("Please make sure the minimal_http_server/v2 directory exists.")
        sys.exit(1)
    
    # Run the new server with the specified arguments
    run_server(host, port, debug, auto_port, log_file)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MCP HTTP Server Launcher')
    parser.add_argument('--version', type=str, choices=['original', 'v2'], default='v2',
                        help='Which version of the server to run')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Host to listen on (default: localhost)')
    parser.add_argument('--port', type=int, default=9000,
                        help='Port to listen on (default: 9000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--auto-port', action='store_true',
                        help='Automatically find an available port if the specified port is in use')
    parser.add_argument('--log-file', type=str,
                        help='Log file to write to (in addition to stdout)')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.debug, args.log_file)
    
    # Run the requested server version
    if args.version == 'original':
        logging.info("Starting original MCP HTTP server...")
        run_original_server(args.host, args.port, args.debug, args.auto_port)
    else:
        logging.info("Starting new MCP HTTP server...")
        run_new_server(args.host, args.port, args.debug, args.auto_port, args.log_file)


if __name__ == "__main__":
    main() 