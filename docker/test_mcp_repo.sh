#!/bin/bash
# Test an MCP server repository using the MCP Protocol Validator

set -e

# Check arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <repo_url> [transport_type] [protocol_version]"
    echo ""
    echo "Arguments:"
    echo "  repo_url:          Git repository URL containing an MCP server"
    echo "  transport_type:    Transport type (http or stdio, default: stdio)"
    echo "  protocol_version:  Protocol version to test (2024-11-05 or 2025-03-26, default: 2025-03-26)"
    echo ""
    echo "Example:"
    echo "  $0 https://github.com/user/mcp-server stdio 2025-03-26"
    exit 1
fi

REPO_URL="$1"
TRANSPORT="${2:-stdio}"
PROTOCOL_VERSION="${3:-2025-03-26}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Clean up on exit
function cleanup {
    echo "Cleaning up..."
    if [ -n "$CONTAINER_ID" ]; then
        echo "Stopping container $CONTAINER_ID..."
        docker stop "$CONTAINER_ID" > /dev/null 2>&1 || true
    fi
    echo "Removing temporary directory..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Clone the repository
echo "Cloning repository: $REPO_URL"
git clone "$REPO_URL" "$TEMP_DIR/repo"
cd "$TEMP_DIR/repo"

# Detect Dockerfile
DOCKERFILE=""
if [ -f "Dockerfile" ]; then
    DOCKERFILE="Dockerfile"
elif [ -f "docker/Dockerfile" ]; then
    DOCKERFILE="docker/Dockerfile"
else
    echo "No Dockerfile found in repo, searching recursively..."
    DOCKERFILE=$(find . -name "Dockerfile" | head -n 1)
fi

if [ -z "$DOCKERFILE" ]; then
    echo "Error: No Dockerfile found in the repository."
    echo "The repository must contain a Dockerfile to build the MCP server."
    exit 1
fi

echo "Found Dockerfile: $DOCKERFILE"

# Build the Docker image
REPO_NAME=$(basename "$REPO_URL" .git)
IMAGE_NAME="mcp-validator-test-$REPO_NAME"

echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" .

# Create test data directory
TEST_DATA_DIR="$TEMP_DIR/test_data"
mkdir -p "$TEST_DATA_DIR"
echo "Created test data directory: $TEST_DATA_DIR"

# Create some test files
echo "Creating test files..."
echo "This is a test file" > "$TEST_DATA_DIR/test.txt"
mkdir -p "$TEST_DATA_DIR/nested"
echo "This is a nested file" > "$TEST_DATA_DIR/nested/nested.txt"
echo '{"key": "value"}' > "$TEST_DATA_DIR/data.json"

# Determine Docker run command based on transport type
if [ "$TRANSPORT" = "http" ]; then
    # Run the HTTP server in Docker
    echo "Starting HTTP server in Docker..."
    
    # Find a free port
    PORT=8080
    while nc -z localhost $PORT > /dev/null 2>&1; do
        PORT=$((PORT + 1))
    done
    
    echo "Using port: $PORT"
    
    # Run the container
    CONTAINER_ID=$(docker run -d --rm -p $PORT:8080 \
        -v "$TEST_DATA_DIR:/projects/files" \
        -e MCP_PROTOCOL_VERSION="$PROTOCOL_VERSION" \
        -e MCP_TRANSPORT=http \
        "$IMAGE_NAME")
    
    echo "Server started in container: $CONTAINER_ID"
    echo "Waiting for server to start..."
    sleep 5
    
    # Get the current directory to find the validator
    CURRENT_DIR=$(pwd)
    cd - > /dev/null
    
    # Run the validator
    echo "Running MCP Protocol Validator..."
    python mcp_validator.py test \
        --transport http \
        --url "http://localhost:$PORT" \
        --protocol-version "$PROTOCOL_VERSION" \
        --report-format html \
        --debug
    
    # Stop the container
    echo "Stopping container..."
    docker stop "$CONTAINER_ID" > /dev/null
    
else
    # Run the STDIO server in Docker
    echo "Running STDIO server in Docker..."
    
    # Ensure network exists
    NETWORK_NAME="mcp-test-network"
    if ! docker network inspect "$NETWORK_NAME" > /dev/null 2>&1; then
        echo "Creating Docker network: $NETWORK_NAME"
        docker network create "$NETWORK_NAME"
    fi
    
    # Get the current directory to find the validator
    CURRENT_DIR=$(pwd)
    cd - > /dev/null
    
    # Run the validator with Docker transport
    echo "Running MCP Protocol Validator..."
    python mcp_validator.py test \
        --transport docker \
        --docker-image "$IMAGE_NAME" \
        --mount-dir "$TEST_DATA_DIR" \
        --protocol-version "$PROTOCOL_VERSION" \
        --report-format html \
        --debug
fi

echo "Test complete." 