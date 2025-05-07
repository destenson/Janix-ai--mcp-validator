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

# Establish a session by connecting to the SSE endpoint
echo -e "${YELLOW}Establishing session via SSE endpoint...${NC}"
# Get the server-provided session ID from the SSE stream
SESSION_RESPONSE=$(curl -s -N "${BASE_URL}notifications")
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect to notifications endpoint.${NC}"
    exit 1
fi

echo "$SESSION_RESPONSE"

# Extract session ID using a regular expression
if [[ $SESSION_RESPONSE =~ Connected\ to\ session\ ([a-z0-9-]+) ]]; then
    SESSION_ID="${BASH_REMATCH[1]}"
    echo -e "${GREEN}Got session ID: ${SESSION_ID}${NC}"
else
    echo -e "${RED}Failed to get session ID from SSE stream.${NC}"
    # Print what we received for debugging
    echo "$SESSION_RESPONSE"
    exit 1
fi

# Use a new terminal for the SSE connection
echo -e "${YELLOW}Opening SSE connection (this will keep running)...${NC}"
curl -s -N "${BASE_URL}notifications?session_id=${SESSION_ID}" > sse_output.log 2>&1 &
SSE_PID=$!
sleep 2  # Give time for connection to establish

# Initialize the server
echo -e "${YELLOW}Testing initialize method...${NC}"
INITIALIZE_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":\"test-1\",\"params\":{\"protocol_version\":\"${PROTOCOL_VERSION}\",\"client_info\":{\"name\":\"test-client\"}}}" \
    "${SERVER_URL}?session_id=${SESSION_ID}")

# Check initialize response status
INITIALIZE_STATUS=$(echo "$INITIALIZE_RESPONSE" | grep -o '"status"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [ "$INITIALIZE_STATUS" != "accepted" ]; then
    echo -e "${RED}Initialize request failed: ${INITIALIZE_RESPONSE}${NC}"
    kill $SSE_PID
    exit 1
fi
echo -e "${GREEN}Response: ${INITIALIZE_STATUS}${NC}"
echo -e "${YELLOW}Initialize accepted but no result payload (This may be normal for async processing)${NC}"
echo

# Wait for SSE response
sleep 2
INIT_SSE_RESPONSE=$(cat sse_output.log)
echo -e "${YELLOW}SSE response for initialize:${NC}"
echo "$INIT_SSE_RESPONSE"
echo

# Test echo tool
echo -e "${YELLOW}Testing echo tool...${NC}"
ECHO_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"echo\",\"id\":\"test-2\",\"params\":{\"message\":\"Hello World\"}}" \
    "${SERVER_URL}?session_id=${SESSION_ID}")

# Check echo response status
ECHO_STATUS=$(echo "$ECHO_RESPONSE" | grep -o '"status"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [ "$ECHO_STATUS" != "accepted" ]; then
    echo -e "${RED}Echo request failed: ${ECHO_RESPONSE}${NC}"
    kill $SSE_PID
    exit 1
fi
echo -e "${GREEN}Response: ${ECHO_STATUS}${NC}"
echo -e "${YELLOW}Echo accepted but no result payload (This may be normal for async processing)${NC}"
echo

# Wait for SSE response
sleep 2
ECHO_SSE_RESPONSE=$(cat sse_output.log)
echo -e "${YELLOW}SSE response for echo:${NC}"
echo "$ECHO_SSE_RESPONSE"
echo

# Test add tool
echo -e "${YELLOW}Testing add tool...${NC}"
ADD_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"add\",\"id\":\"test-3\",\"params\":{\"a\":5,\"b\":3}}" \
    "${SERVER_URL}?session_id=${SESSION_ID}")

# Check add response status
ADD_STATUS=$(echo "$ADD_RESPONSE" | grep -o '"status"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [ "$ADD_STATUS" != "accepted" ]; then
    echo -e "${RED}Add request failed: ${ADD_RESPONSE}${NC}"
    kill $SSE_PID
    exit 1
fi
echo -e "${GREEN}Response: ${ADD_STATUS}${NC}"
echo -e "${YELLOW}Add accepted but no result payload (This may be normal for async processing)${NC}"
echo

# Wait for SSE response
sleep 2
ADD_SSE_RESPONSE=$(cat sse_output.log)
echo -e "${YELLOW}SSE response for add:${NC}"
echo "$ADD_SSE_RESPONSE"
echo

# Clean up
kill $SSE_PID
rm sse_output.log

echo -e "${YELLOW}Test Summary:${NC}"
echo -e "${GREEN}All tests passed!${NC}" 