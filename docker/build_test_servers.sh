#!/bin/bash
# Build Docker images for MCP test servers

set -e

echo "Building Docker images for MCP test servers..."

# Check for required files
if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found in the current directory."
    echo "Please run this script from the root of the mcp-protocol-validator project."
    exit 1
fi

for file in docker/Dockerfile.http docker/Dockerfile.stdio docker/http_server.py docker/stdio_server.py; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found."
        echo "Please ensure all required files are in place before building."
        exit 1
    fi
done

# Build HTTP server image
echo "Building HTTP server image..."
docker build -t mcp-http-server -f docker/Dockerfile.http .

# Build STDIO server image
echo "Building STDIO server image..."
docker build -t mcp-stdio-server -f docker/Dockerfile.stdio .

echo "Build complete."
echo ""
echo "To run the HTTP server:"
echo "  docker run -p 8080:8080 -v /path/to/files:/projects/files mcp-http-server"
echo ""
echo "To test with the validator:"
echo "  # HTTP transport"
echo "  python mcp_validator.py test --transport http --url http://localhost:8080"
echo ""
echo "  # Docker STDIO transport"
echo "  python mcp_validator.py test --transport docker --docker-image mcp-stdio-server --mount-dir /path/to/files"
echo "" 