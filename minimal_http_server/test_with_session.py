#!/usr/bin/env python3
"""
Session Testing Tool for MCP HTTP Server

This script demonstrates and validates proper session ID handling when interacting
with an MCP server over HTTP. It follows these key steps:
1. Initialize the server and capture the session ID from response headers
2. Include the session ID in all subsequent requests via the Mcp-Session-Id header
3. Test basic server functionality (server/info, tools/list, tools/call)
4. Test async tool functionality (tools/call-async, tools/result)

It serves as both a validation tool and a reference implementation for
clients that need to properly handle MCP sessions.

Usage:
    python test_with_session.py [--url URL] [--debug]

Options:
    --url URL    The URL of the MCP server (default: http://localhost:8888/mcp)
    --debug      Enable debug output
"""

import argparse
import json
import requests
import sys
import time
import uuid
import logging

def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('MCPSessionTest')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test MCP HTTP server with session handling")
    parser.add_argument('--url', default='http://localhost:8888/mcp',
                        help='URL of the MCP server (default: http://localhost:8888/mcp)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_args()
    logger = setup_logging(args.debug)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Set up common headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    # Create a unique request ID
    request_id = str(uuid.uuid4())
    
    # Step 1: Initialize the server and capture the session ID
    logger.info("Step 1: Initializing server...")
    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "clientInfo": {
                "name": "Session Test Client",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"asyncSupported": True},
                "resources": True
            }
        },
        "id": request_id
    }
    
    try:
        response = session.post(args.url, json=init_payload, headers=headers)
        logger.info(f"Status: {response.status_code}")
        logger.debug(f"Response: {response.text}")
        logger.debug(f"Headers: {dict(response.headers)}")
        
        # Check if initialization was successful
        if response.status_code != 200:
            logger.error("Failed to initialize server")
            sys.exit(1)
        
        init_result = response.json()
        session_id = None
        
        # Extract session ID from response headers or body
        if "Mcp-Session-Id" in response.headers:
            session_id = response.headers["Mcp-Session-Id"]
            logger.info(f"Session ID from headers: {session_id}")
        elif "result" in init_result and "sessionId" in init_result["result"]:
            session_id = init_result["result"]["sessionId"]
            logger.info(f"Session ID from response body: {session_id}")
        else:
            logger.warning("No session ID found in response")
            # Try to continue with server/info to get session ID
        
        # Add session ID to headers for all subsequent requests
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        
        # Step 2: Get server info using the session ID
        logger.info("\nStep 2: Getting server info...")
        info_payload = {
            "jsonrpc": "2.0",
            "method": "server/info",
            "id": str(uuid.uuid4())
        }
        
        response = session.post(args.url, json=info_payload, headers=headers)
        logger.info(f"Status: {response.status_code}")
        logger.debug(f"Response: {response.text}")
        
        # Check if we need to extract session ID from server/info response
        if not session_id and response.status_code == 200:
            info_result = response.json()
            if "result" in info_result and "sessionId" in info_result["result"]:
                session_id = info_result["result"]["sessionId"]
                logger.info(f"Session ID from server/info: {session_id}")
                headers["Mcp-Session-Id"] = session_id
        
        # Step 3: List available tools
        logger.info("\nStep 3: Listing tools...")
        tools_payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": str(uuid.uuid4())
        }
        
        response = session.post(args.url, json=tools_payload, headers=headers)
        logger.info(f"Status: {response.status_code}")
        tools_response = response.json()
        
        if "result" in tools_response and "tools" in tools_response["result"]:
            tools = tools_response["result"]["tools"]
            logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        else:
            logger.debug(f"Full response: {response.text}")
            logger.error("Failed to retrieve tools list")
        
        # Step 4: Call the echo tool
        logger.info("\nStep 4: Calling echo tool...")
        echo_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "echo",
                "parameters": {
                    "message": "Hello, this is a test with session ID!"
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = session.post(args.url, json=echo_payload, headers=headers)
        logger.info(f"Status: {response.status_code}")
        echo_response = response.json()
        
        if "result" in echo_response:
            logger.info(f"Echo response: {echo_response['result']}")
        else:
            logger.debug(f"Full response: {response.text}")
            logger.error("Failed to execute echo tool")
        
        # Step 5: Test async tool call
        logger.info("\nStep 5: Testing async tool call...")
        async_call_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call-async",
            "params": {
                "name": "sleep",
                "parameters": {
                    "seconds": 2
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = session.post(args.url, json=async_call_payload, headers=headers)
        logger.info(f"Status: {response.status_code}")
        async_response = response.json()
        
        if response.status_code == 200 and "result" in async_response and "id" in async_response["result"]:
            task_id = async_response["result"]["id"]
            logger.info(f"Async task ID: {task_id}")
            
            # Check async result after a few seconds
            logger.info("\nChecking async result...")
            result_payload = {
                "jsonrpc": "2.0",
                "method": "tools/result",
                "params": {
                    "id": task_id
                },
                "id": str(uuid.uuid4())
            }
            
            # Wait a moment to let the task complete
            logger.info("Waiting for async task to complete...")
            time.sleep(3)
            
            response = session.post(args.url, json=result_payload, headers=headers)
            logger.info(f"Status: {response.status_code}")
            result_response = response.json()
            
            if "result" in result_response:
                logger.info(f"Async result: {result_response['result']}")
            else:
                logger.debug(f"Full response: {response.text}")
                logger.error("Failed to retrieve async result")
        else:
            logger.debug(f"Full response: {response.text}")
            logger.error("Failed to start async task")
        
        logger.info("\nAll tests completed successfully!")
    
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 