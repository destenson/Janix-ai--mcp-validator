#!/usr/bin/env python3
"""
Simple test script for the HTTP server.

This is a simplified version that directly tests HTTP communication with the MCP server using curl.
"""

import json
import sys
import subprocess
import tempfile
import os

def test_server(url):
    """Test basic communication with the server using curl."""
    print(f"Testing server at {url}")
    
    # Create an initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "Simple HTTP Test",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        }
    }
    
    try:
        # First try OPTIONS request
        print("Sending OPTIONS request...")
        options_cmd = ["curl", "-s", "-i", "-m", "30", "-X", "OPTIONS", url]
        print(f"Running: {' '.join(options_cmd)}")
        
        options_result = subprocess.run(options_cmd, capture_output=True, text=True)
        
        if options_result.returncode != 0:
            print(f"OPTIONS request failed with code {options_result.returncode}")
            print(f"Stderr: {options_result.stderr}")
            return 1
            
        print("OPTIONS response:")
        print(options_result.stdout)
        
        # Send initialize request using curl
        print("\nSending initialize request...")
        print(f"Request: {json.dumps(initialize_request, indent=2)}")
        
        # Create a temporary file to hold the JSON request
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp:
            json.dump(initialize_request, temp)
            temp_path = temp.name
        
        try:
            # Execute curl to post the JSON
            cmd = [
                "curl", "-s", "-i", "-m", "30",
                "-H", "Content-Type: application/json",
                "-H", "Accept: application/json",
                "--data", "@" + temp_path,
                url
            ]
            print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Initialize request failed with code {result.returncode}")
                print(f"Stderr: {result.stderr}")
                return 1
                
            print("Initialize response:")
            print(result.stdout)
            
            # Parse headers and body from the response
            response_lines = result.stdout.strip().split('\n')
            headers_end = response_lines.index('') if '' in response_lines else len(response_lines)
            
            headers = response_lines[:headers_end]
            body = '\n'.join(response_lines[headers_end+1:]) if headers_end < len(response_lines) else ""
            
            # Find session ID in headers
            session_id = None
            for header in headers:
                if header.lower().startswith("mcp-session-id:"):
                    session_id = header.split(":", 1)[1].strip()
                    break
            
            if not session_id:
                print("No session ID found in response headers")
                return 1
                
            print(f"\nFound session ID: {session_id}")
            print("\nSending tools/list request with session ID...")
            
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            # Create a temporary file for the tools request
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp:
                json.dump(tools_request, temp)
                tools_temp_path = temp.name
            
            try:
                # Execute curl with session ID
                tools_cmd = [
                    "curl", "-s", "-i", "-m", "30",
                    "-H", "Content-Type: application/json",
                    "-H", "Accept: application/json",
                    "-H", f"Mcp-Session-Id: {session_id}",
                    "--data", "@" + tools_temp_path,
                    url
                ]
                print(f"Running: {' '.join(tools_cmd)}")
                
                tools_result = subprocess.run(tools_cmd, capture_output=True, text=True)
                
                if tools_result.returncode != 0:
                    print(f"Tools/list request failed with code {tools_result.returncode}")
                    print(f"Stderr: {tools_result.stderr}")
                    return 1
                    
                print("Tools/list response:")
                print(tools_result.stdout)
                
                print("All tests passed successfully!")
                return 0
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tools_temp_path)
                except Exception:
                    pass
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9000/mcp"
    sys.exit(test_server(url)) 