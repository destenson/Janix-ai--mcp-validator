#!/usr/bin/env python3
"""
Debug script for testing Docker transport connectivity.

This script tests the Docker transport by connecting to a Docker container
running an MCP server and sending basic protocol messages.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from transport.enhanced_docker_client import EnhancedDockerSTDIOTransport

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("docker_debug")

def test_docker_connection(docker_image, protocol_version, mount_path=None, timeout=60):
    """
    Test Docker transport connection with detailed debugging.
    
    Args:
        docker_image: Docker image to test with
        protocol_version: MCP protocol version to use
        mount_path: Optional path to mount into the container
        timeout: Connection timeout in seconds
    
    Returns:
        True if the test passed, False otherwise
    """
    logger.info(f"Testing Docker connection to image: {docker_image}")
    logger.info(f"Protocol version: {protocol_version}")
    
    if mount_path:
        logger.info(f"Using mount path: {mount_path}")
        # Ensure mount path exists
        os.makedirs(mount_path, exist_ok=True)
    
    # Initialize the transport
    transport = EnhancedDockerSTDIOTransport(
        docker_image=docker_image,
        mount_path=mount_path,
        protocol_version=protocol_version,
        timeout=timeout,
        debug=True,
        env_vars={"MCP_DEBUG": "true"}
    )
    
    success = False
    
    try:
        logger.info("Starting Docker transport...")
        start_time = time.time()
        
        # Start the transport
        if not transport.start():
            logger.error("Failed to start Docker transport")
            return False
        
        logger.info(f"Docker transport started in {time.time() - start_time:.2f} seconds")
        
        # Send initialization request
        logger.info("Sending initialization request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "mcp/initialize",
            "params": {
                "protocol_version": protocol_version
            },
            "id": "init-1"
        }
        
        try:
            init_response = transport.send_request(init_request)
            logger.info(f"Initialization response: {json.dumps(init_response, indent=2)}")
            
            if "result" in init_response:
                logger.info("Initialization successful")
                
                # If initialization worked, try getting available tools
                logger.info("Querying available tools...")
                tools_response = transport.send_request("mcp/list_available_tools", {}, "tools-1")
                logger.info(f"Tools response: {json.dumps(tools_response, indent=2)}")
                
                # Try another simple request
                logger.info("Sending a test request...")
                test_response = transport.send_request("mcp/echo", {"message": "Hello Docker!"}, "test-1")
                logger.info(f"Test response: {json.dumps(test_response, indent=2)}")
                
                # Send shutdown request
                logger.info("Sending shutdown request...")
                shutdown_response = transport.send_request("mcp/shutdown", {}, "shutdown-1")
                logger.info(f"Shutdown response: {json.dumps(shutdown_response, indent=2)}")
                
                success = True
            else:
                logger.error("Initialization failed")
        except Exception as e:
            logger.error(f"Error during communication: {str(e)}")
            
            # Get container logs if available
            if hasattr(transport, 'get_container_logs'):
                logger.info("Container logs:")
                logs = transport.get_container_logs()
                for line in logs.splitlines():
                    logger.info(f"CONTAINER: {line}")
    
    except Exception as e:
        logger.error(f"Error during Docker transport test: {str(e)}")
    finally:
        # Stop the transport
        logger.info("Stopping Docker transport...")
        transport.stop()
        logger.info("Docker transport stopped")
    
    if success:
        logger.info("Docker transport test PASSED!")
    else:
        logger.error("Docker transport test FAILED!")
    
    return success

def main():
    parser = argparse.ArgumentParser(description="Debug Docker transport for MCP servers")
    parser.add_argument("--image", required=True, help="Docker image to test")
    parser.add_argument("--protocol", default="2024-11-05", help="Protocol version")
    parser.add_argument("--mount", help="Path to mount into the container")
    parser.add_argument("--timeout", type=int, default=60, help="Connection timeout in seconds")
    
    args = parser.parse_args()
    
    result = test_docker_connection(
        docker_image=args.image,
        protocol_version=args.protocol,
        mount_path=args.mount,
        timeout=args.timeout
    )
    
    # Exit with appropriate status code
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main() 