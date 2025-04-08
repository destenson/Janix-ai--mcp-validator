# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HTTP Testing Utilities

Helper functions for testing MCP over HTTP transport.
"""

import socket
import time
from urllib.parse import urlparse

def check_server(url, timeout=5):
    """
    Check if a server is accessible at the given URL.
    
    Args:
        url: The server URL to check
        timeout: Connection timeout in seconds
        
    Returns:
        True if the server is accessible, False otherwise
    """
    print(f"Checking if server at {url} is accessible...")
    
    # Parse the URL
    parsed_url = urlparse(url)
    host = parsed_url.netloc.split(':')[0]
    port = int(parsed_url.netloc.split(':')[1]) if ':' in parsed_url.netloc else 80
    
    # Try to connect to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    
    try:
        s.connect((host, port))
        print(f"Server at {host}:{port} is accessible.")
        return True
    except socket.error as e:
        print(f"Failed to connect to server at {host}:{port}: {e}")
        return False
    finally:
        s.close()

def wait_for_server(url, max_retries=3, retry_interval=2, timeout=5):
    """
    Wait for a server to become accessible, retrying as specified.
    
    Args:
        url: The server URL to check
        max_retries: Maximum number of retries before giving up
        retry_interval: Seconds to wait between retries
        timeout: Connection timeout in seconds
        
    Returns:
        True if the server became accessible, False otherwise
    """
    retries = 0
    while retries < max_retries:
        if check_server(url, timeout):
            return True
        
        retries += 1
        if retries < max_retries:
            print(f"Retrying in {retry_interval} seconds... (attempt {retries+1}/{max_retries})")
            time.sleep(retry_interval)
    
    print(f"Failed to connect to server after {max_retries} attempts")
    return False 