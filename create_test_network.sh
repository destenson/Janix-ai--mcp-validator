#!/bin/bash
# Create Docker test network for MCP testing

# Check if network already exists
if docker network inspect mcp-test-network >/dev/null 2>&1; then
    echo "Network 'mcp-test-network' already exists."
else
    echo "Creating Docker network 'mcp-test-network'..."
    docker network create mcp-test-network
    echo "Network created successfully."
fi 