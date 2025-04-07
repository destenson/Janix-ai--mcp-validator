#!/bin/bash
# Script to test the minimal MCP server with the validator

# Set protocol version from command line or default to 2024-11-05
PROTOCOL_VERSION=${1:-2024-11-05}

# Run the validator
./run_validator.py \
  --transport stdio \
  --server-command "./minimal_mcp_server/minimal_mcp_server.py" \
  --protocol-version ${PROTOCOL_VERSION} \
  --debug \
  --report-format html \
  --report-path reports/minimal_server_${PROTOCOL_VERSION}.html

# Check the exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "\nValidator test passed! 🎉"
  echo "Report saved to: reports/minimal_server_${PROTOCOL_VERSION}.html"
else
  echo -e "\nValidator test failed with exit code: $EXIT_CODE"
  echo "See the report for details: reports/minimal_server_${PROTOCOL_VERSION}.html"
fi

exit $EXIT_CODE 