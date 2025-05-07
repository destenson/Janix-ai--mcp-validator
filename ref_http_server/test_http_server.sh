#!/bin/bash
# Test script for MCP HTTP server compliance

# Default server URL
SERVER_URL="http://localhost:8088"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --server-url=*)
      SERVER_URL="${1#*=}"
      shift
      ;;
    --server-url)
      SERVER_URL="$2"
      shift 2
      ;;
    --debug)
      DEBUG="--debug"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Make the http_compliance_test.py script executable
chmod +x http_compliance_test.py

# Run the compliance test
python3 http_compliance_test.py --server-url="$SERVER_URL" $DEBUG 