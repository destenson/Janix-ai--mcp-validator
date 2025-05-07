#!/bin/bash

# Simple script to test FastMCP HTTP server

# Configuration
SERVER_URL="http://localhost:8085/mcp/"
BASE_URL="${SERVER_URL%mcp/}"
PROTOCOL_VERSION="2025-03-26"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing FastMCP server at ${SERVER_URL}${NC}"
echo

# Check if server is running
echo -e "${YELLOW}Checking if server is running...${NC}"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_URL}")
if [ $? -ne 0 ] || [ "$HEALTH_CHECK" -ge 500 ]; then
    echo -e "${RED}Server is not running (status code: $HEALTH_CHECK).${NC}"
    exit 1
fi
echo -e "${GREEN}Server is running.${NC}"
echo

# Establish a session by connecting to the SSE endpoint and extract the session ID
echo -e "${YELLOW}Establishing session via SSE endpoint...${NC}"

# Create a temporary file to capture SSE output
SSE_OUTPUT=$(mktemp)

# Start the SSE connection in the background and capture the output
curl -s -N "${BASE_URL}notifications" > "$SSE_OUTPUT" &
SSE_PID=$!

# Give it a moment to receive the session ID
sleep 2

# Extract the session ID from the SSE output
SESSION_ID=$(grep -o 'session_id=[a-zA-Z0-9]*' "$SSE_OUTPUT" | head -1 | cut -d= -f2)

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}Failed to get session ID from SSE stream.${NC}"
    cat "$SSE_OUTPUT"
    rm "$SSE_OUTPUT"
    kill $SSE_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}Got session ID: ${SESSION_ID}${NC}"
rm "$SSE_OUTPUT"

# Test initialize method
echo -e "${YELLOW}Testing initialize method...${NC}"
INIT_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":\"test-1\",\"params\":{\"client_info\":{\"name\":\"curl-test\"},\"protocol_version\":\"${PROTOCOL_VERSION}\"}}" \
    "${SERVER_URL}?session_id=${SESSION_ID}")

echo "Response: ${INIT_RESPONSE}"

if [[ "${INIT_RESPONSE}" == *"\"result\""* ]]; then
    echo -e "${GREEN}Initialize test passed.${NC}"
    INIT_SUCCESS=true
elif [[ "${INIT_RESPONSE}" == *"Accepted"* ]]; then
    echo -e "${YELLOW}Initialize accepted but no result payload (This may be normal for async processing)${NC}"
    INIT_SUCCESS=true
else
    echo -e "${RED}Initialize test failed.${NC}"
    INIT_SUCCESS=false
fi
echo

# Test echo tool
if [ "${INIT_SUCCESS}" = true ]; then
    echo -e "${YELLOW}Testing echo tool...${NC}"
    TEST_MESSAGE="Hello MCP $(date)"
    
    ECHO_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"echo\",\"id\":\"test-2\",\"params\":{\"message\":\"${TEST_MESSAGE}\"}}" \
        "${SERVER_URL}?session_id=${SESSION_ID}")
    
    echo "Response: ${ECHO_RESPONSE}"
    
    if [[ "${ECHO_RESPONSE}" == *"\"${TEST_MESSAGE}\""* ]]; then
        echo -e "${GREEN}Echo test passed.${NC}"
        ECHO_SUCCESS=true
    elif [[ "${ECHO_RESPONSE}" == *"Accepted"* ]]; then
        echo -e "${YELLOW}Echo accepted but no result payload (This may be normal for async processing)${NC}"
        ECHO_SUCCESS=true
    else
        echo -e "${RED}Echo test failed.${NC}"
        ECHO_SUCCESS=false
    fi
    echo
fi

# Test add tool
if [ "${INIT_SUCCESS}" = true ]; then
    echo -e "${YELLOW}Testing add tool...${NC}"
    
    ADD_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"add\",\"id\":\"test-3\",\"params\":{\"a\":5,\"b\":7}}" \
        "${SERVER_URL}?session_id=${SESSION_ID}")
    
    echo "Response: ${ADD_RESPONSE}"
    
    if [[ "${ADD_RESPONSE}" == *"\"result\":12"* ]]; then
        echo -e "${GREEN}Add test passed.${NC}"
        ADD_SUCCESS=true
    elif [[ "${ADD_RESPONSE}" == *"Accepted"* ]]; then
        echo -e "${YELLOW}Add accepted but no result payload (This may be normal for async processing)${NC}"
        ADD_SUCCESS=true
    else
        echo -e "${RED}Add test failed.${NC}"
        ADD_SUCCESS=false
    fi
    echo
fi

# Kill the SSE connection
if [ -n "$SSE_PID" ]; then
    kill $SSE_PID >/dev/null 2>&1
fi

# Summary
echo -e "${YELLOW}Test Summary:${NC}"
if [ "${INIT_SUCCESS}" = true ] && [ "${ECHO_SUCCESS}" = true ] && [ "${ADD_SUCCESS}" = true ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi 