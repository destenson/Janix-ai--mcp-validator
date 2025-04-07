#!/bin/bash

# Default values
TEST_MODULE="base_protocol"
PROTOCOL_VERSION="2024-11-05"
DEBUG=0

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --test=*)
      TEST_MODULE="${1#*=}"
      shift
      ;;
    --protocol=*)
      PROTOCOL_VERSION="${1#*=}"
      shift
      ;;
    --debug)
      DEBUG=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./run_with_venv.sh [--test=module_name] [--protocol=version] [--debug]"
      exit 1
      ;;
  esac
done

# Activate the virtual environment
source .venv/bin/activate

# Set PYTHONPATH to include the current directory
export PYTHONPATH="$PYTHONPATH:."

# Set environment variables
export MCP_TRANSPORT_TYPE="stdio"
export MCP_SERVER_COMMAND="python minimal_mcp_server/minimal_mcp_server.py"
export MCP_PROTOCOL_VERSION="$PROTOCOL_VERSION"
if [ "$DEBUG" -eq 1 ]; then
  export MCP_DEBUG="1"
fi

# Build the test file path
if [[ "$TEST_MODULE" == test_* ]]; then
  TEST_FILE="tests/$TEST_MODULE.py"
else
  TEST_FILE="tests/test_$TEST_MODULE.py"
fi

echo "Running tests with configuration:"
echo "  Test module: $TEST_MODULE"
echo "  Protocol version: $PROTOCOL_VERSION"
echo "  Debug mode: $([ "$DEBUG" -eq 1 ] && echo "enabled" || echo "disabled")"
echo "  Test file: $TEST_FILE"

# Run pytest with the venv's Python
.venv/bin/python -m pytest -v "$TEST_FILE" 