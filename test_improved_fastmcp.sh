#!/bin/bash
# Test script for the improved FastMCP HTTP server with SSE transport

# Set the working directory to the script's directory
cd "$(dirname "$0")"

# Make sure we have a reports directory
mkdir -p reports

# Kill any existing servers running on port 8085
echo "Checking for existing servers on port 8085..."
lsof -i:8085 -t | xargs kill -9 2>/dev/null || true

# Start the server in the background
echo "Starting improved FastMCP HTTP server..."
python ref_http_server/fastmcp_server.py --debug &
SERVER_PID=$!

# Give the server time to start
echo "Waiting for server to start..."
sleep 2

# Run the compliance tests
echo "Running compliance tests..."
python mcp_testing/scripts/fastmcp_compliance.py --server-url http://localhost:8085 --debug --report-file reports/improved_fastmcp_compliance_report.md

# Capture the exit code
TEST_EXIT_CODE=$?

# Kill the server
echo "Stopping server (PID: $SERVER_PID)..."
kill $SERVER_PID || true

# Report result
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Tests passed! See report at reports/improved_fastmcp_compliance_report.md"
else
    echo "❌ Tests failed! See report at reports/improved_fastmcp_compliance_report.md"
fi

exit $TEST_EXIT_CODE 