#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Simple check script to test if the HTTP server is responding correctly.
"""

import requests
import json
import sys

def check_server(url):
    """Make a simple request to the server and print the response."""
    print(f"Checking server at {url}")
    
    # Create initialize request
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "MCP HTTP Test Client",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        }
    }
    
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    try:
        # Make the request
        print("Sending request...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Headers: {headers}")
        
        response = requests.post(url, json=request, headers=headers)
        
        # Print response details
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Server responded correctly!")
            return 0
        else:
            print(f"ERROR: Server returned status code {response.status_code}")
            return 1
            
    except Exception as e:
        print(f"ERROR: Failed to connect to server: {str(e)}")
        return 1
        
if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/mcp"
    sys.exit(check_server(url)) 