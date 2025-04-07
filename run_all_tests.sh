#!/bin/bash
# MCP Protocol Validator - Run All Tests
# This script runs tests against both HTTP and STDIO servers with both protocol versions

set -e  # Exit on error

# Ensure Docker test servers are built
echo "Building Docker test servers..."
cd docker
./build_test_servers.sh
cd ..

# Create directory for reports
mkdir -p reports

# Test HTTP server with protocol version 2024-11-05
echo "========================================================"
echo "Testing HTTP server with protocol version 2024-11-05..."
echo "========================================================"
./run_validator.py --transport http --server-url http://localhost:3000 \
                  --protocol-version 2024-11-05 \
                  --report-format html --report-path reports/http-2024-11-05.html

# Test HTTP server with protocol version 2025-03-26
echo "========================================================"
echo "Testing HTTP server with protocol version 2025-03-26..."
echo "========================================================"
./run_validator.py --transport http --server-url http://localhost:3000 \
                  --protocol-version 2025-03-26 \
                  --report-format html --report-path reports/http-2025-03-26.html

# Test STDIO server with Docker for protocol version 2024-11-05
echo "========================================================"
echo "Testing STDIO server with protocol version 2024-11-05..."
echo "========================================================"
./run_validator.py --transport docker --docker-image mcp-stdio-server \
                  --protocol-version 2024-11-05 \
                  --report-format html --report-path reports/stdio-2024-11-05.html

# Test STDIO server with Docker for protocol version 2025-03-26
echo "========================================================"
echo "Testing STDIO server with protocol version 2025-03-26..."
echo "========================================================"
./run_validator.py --transport docker --docker-image mcp-stdio-server \
                  --protocol-version 2025-03-26 \
                  --report-format html --report-path reports/stdio-2025-03-26.html

echo "========================================================"
echo "All tests completed!"
echo "Reports are available in the reports directory:"
echo "  - reports/http-2024-11-05.html"
echo "  - reports/http-2025-03-26.html"
echo "  - reports/stdio-2024-11-05.html"
echo "  - reports/stdio-2025-03-26.html"
echo "========================================================" 