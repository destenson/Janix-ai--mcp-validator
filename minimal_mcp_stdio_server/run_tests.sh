#!/bin/bash
# Script to test the minimal MCP STDIO server with the validator

set -e  # Exit on error

PROTOCOL_VERSION=${1:-"2024-11-05"}
TEST_TYPE=${2:-"basic"}

echo "================================================================="
echo "Running tests for Minimal MCP STDIO Server"
echo "Protocol version: $PROTOCOL_VERSION"
echo "Test type: $TEST_TYPE"
echo "================================================================="

# Ensure server is executable
chmod +x ./minimal_mcp_stdio_server.py

# Set environment variables
export MCP_PROTOCOL_VERSION=$PROTOCOL_VERSION
export MCP_TRANSPORT_TYPE="stdio"
export MCP_SERVER_COMMAND="$(pwd)/minimal_mcp_stdio_server.py"
export MCP_DEBUG="true"

# Navigate to parent directory where validator is located
cd ..

# Create reports directory if it doesn't exist
mkdir -p reports

# Define test functions
run_basic_test() {
    echo "Running basic initialization test..."
    ./run_validator.py \
        --transport stdio \
        --server-command "$MCP_SERVER_COMMAND" \
        --protocol-version $PROTOCOL_VERSION \
        --test-module test_base_protocol \
        --test-class TestBasicSTDIO \
        --test-method test_initialization \
        --report-path "reports/minimal_stdio_${PROTOCOL_VERSION}_basic.html" \
        --debug
}

run_tools_test() {
    echo "Running tools tests..."
    ./run_validator.py \
        --transport stdio \
        --server-command "$MCP_SERVER_COMMAND" \
        --protocol-version $PROTOCOL_VERSION \
        --test-module test_tools \
        --test-class TestToolsProtocol \
        --report-path "reports/minimal_stdio_${PROTOCOL_VERSION}_tools.html" \
        --debug
}

run_resources_test() {
    echo "Running resources tests..."
    ./run_validator.py \
        --transport stdio \
        --server-command "$MCP_SERVER_COMMAND" \
        --protocol-version $PROTOCOL_VERSION \
        --test-module test_resources \
        --test-class TestResourcesProtocol \
        --report-path "reports/minimal_stdio_${PROTOCOL_VERSION}_resources.html" \
        --debug
}

run_batch_test() {
    echo "Running batch request test..."
    ./run_validator.py \
        --transport stdio \
        --server-command "$MCP_SERVER_COMMAND" \
        --protocol-version $PROTOCOL_VERSION \
        --test-module test_base_protocol \
        --test-class TestBasicSTDIO \
        --test-method test_batch_request \
        --report-path "reports/minimal_stdio_${PROTOCOL_VERSION}_batch.html" \
        --debug
}

# Run tests based on test type
case $TEST_TYPE in
    "basic")
        run_basic_test
        ;;
    "tools")
        run_tools_test
        ;;
    "resources")
        run_resources_test
        ;;
    "batch")
        run_batch_test
        ;;
    "all")
        run_basic_test
        run_tools_test
        run_resources_test
        run_batch_test
        ;;
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Available test types: basic, tools, resources, batch, all"
        exit 1
        ;;
esac

echo "================================================================="
echo "Tests completed."
echo "Reports available in the 'reports' directory."
echo "=================================================================" 