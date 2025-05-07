#!/usr/bin/env python3
"""
Simple MCP HTTP/SSE Server Test

A basic script to test HTTP/SSE MCP servers without using the complex MCP SDK.
Tests basic connectivity and tool functionality.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
    from httpx_sse import EventSource
except ImportError:
    print("Error: Required dependencies not found. Please install with:")
    print("pip install httpx httpx-sse")
    sys.exit(1)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

async def test_server(server_url, timeout=30):
    """Test basic functionality of an MCP HTTP/SSE server"""
    results = []
    start_time = time.time()
    
    # Ensure server_url doesn't end with a slash
    server_url = server_url.rstrip('/')
    
    print(f"Testing MCP server at {server_url}")
    print(f"Also trying messages endpoint at {server_url.replace('/mcp', '/messages')}")
    
    # Try both potential endpoints
    endpoints = [
        server_url,                      # Standard /mcp endpoint
        server_url.replace('/mcp', ''),  # Root endpoint
    ]
    
    # If server_url ends with /mcp, also try /messages and /messages/
    if server_url.endswith('/mcp'):
        endpoints.append(server_url.replace('/mcp', '/messages'))
        endpoints.append(server_url.replace('/mcp', '/messages/'))
    
    session_id = None
    success_endpoint = None
    
    # Test 1: Initialize session - try all potential endpoints
    for endpoint in endpoints:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                # Send init request
                init_request = {
                    "jsonrpc": "2.0",
                    "id": "init-test",
                    "method": "mcp.init",
                    "params": {
                        "protocol_version": "2025-03-26",
                        "client_name": "Simple SSE Test Client"
                    }
                }
                
                print(f"Trying endpoint: {endpoint}")
                headers = {"Content-Type": "application/json"}
                init_response = await client.post(endpoint, json=init_request, headers=headers)
                
                if init_response.status_code == 404:
                    print(f"Endpoint {endpoint} returned 404 Not Found, trying next endpoint")
                    continue
                
                init_data = init_response.json()
                
                if init_data.get("result") and init_data.get("result").get("session_id"):
                    session_id = init_data["result"]["session_id"]
                    success_endpoint = endpoint
                    print(f"Successfully connected to {success_endpoint}")
                    results.append({
                        "name": "initialization",
                        "result": "PASS",
                        "message": f"Successfully initialized session: {session_id} at {success_endpoint}",
                        "time": time.time() - start_time
                    })
                    break
        except Exception as e:
            print(f"Error connecting to {endpoint}: {str(e)}")
    
    if not session_id:
        results.append({
            "name": "initialization",
            "result": "FAIL",
            "message": f"Failed to initialize session on any endpoint",
            "time": time.time() - start_time
        })
        generate_report(results, server_url)
        return results
    
    # Continue with the successful endpoint
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # Test 2: Get capabilities
            cap_request = {
                "jsonrpc": "2.0",
                "id": "cap-test",
                "method": "mcp.get_capabilities",
                "params": {
                    "session_id": session_id
                }
            }
            
            cap_response = await client.post(success_endpoint, json=cap_request, headers={"Content-Type": "application/json"})
            cap_data = cap_response.json()
            
            if cap_data.get("result"):
                capabilities = cap_data["result"]
                results.append({
                    "name": "capabilities",
                    "result": "PASS", 
                    "message": f"Server capabilities: {', '.join(capabilities.keys())}",
                    "time": time.time() - start_time
                })
            else:
                results.append({
                    "name": "capabilities",
                    "result": "FAIL",
                    "message": f"Failed to get capabilities: {cap_data}",
                    "time": time.time() - start_time
                })
            
            # Test 3: List tools
            if "tools" in cap_data.get("result", {}):
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": "tools-test",
                    "method": "mcp.list_tools",
                    "params": {
                        "session_id": session_id
                    }
                }
                
                tools_response = await client.post(success_endpoint, json=tools_request, headers={"Content-Type": "application/json"})
                tools_data = tools_response.json()
                
                if tools_data.get("result") and isinstance(tools_data["result"], list):
                    tool_names = [t.get("name") for t in tools_data["result"]]
                    results.append({
                        "name": "tools_list",
                        "result": "PASS",
                        "message": f"Available tools: {', '.join(tool_names)}",
                        "time": time.time() - start_time
                    })
                    
                    # Test 4: Call echo tool if available
                    if any(t.get("name") == "echo" for t in tools_data["result"]):
                        echo_request = {
                            "jsonrpc": "2.0",
                            "id": "echo-test",
                            "method": "mcp.run_tool", 
                            "params": {
                                "session_id": session_id,
                                "name": "echo",
                                "inputs": {
                                    "message": "Hello MCP Server!"
                                }
                            }
                        }
                        
                        echo_response = await client.post(success_endpoint, json=echo_request, headers={"Content-Type": "application/json"})
                        echo_data = echo_response.json()
                        
                        if echo_data.get("result") and echo_data["result"].get("output") == "Hello MCP Server!":
                            results.append({
                                "name": "echo_tool",
                                "result": "PASS",
                                "message": "Echo tool returned expected output",
                                "time": time.time() - start_time
                            })
                        else:
                            results.append({
                                "name": "echo_tool",
                                "result": "FAIL",
                                "message": f"Echo tool failed: {echo_data}",
                                "time": time.time() - start_time
                            })
                else:
                    results.append({
                        "name": "tools_list",
                        "result": "FAIL",
                        "message": f"Failed to list tools: {tools_data}",
                        "time": time.time() - start_time
                    })
            
            # Test 5: Test SSE connection
            try:
                sse_request = {
                    "jsonrpc": "2.0",
                    "id": "sse-test",
                    "method": "mcp.subscribe",
                    "params": {
                        "session_id": session_id
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                async with client.stream("POST", success_endpoint, json=sse_request, headers=headers) as response:
                    async with EventSource(response) as event_source:
                        async for event in event_source.aiter_events():
                            if event.event == "message":
                                print(f"Received SSE event: {event.data}")
                                results.append({
                                    "name": "sse_connection",
                                    "result": "PASS",
                                    "message": "Successfully established SSE connection and received event",
                                    "time": time.time() - start_time
                                })
                                break
                            
                        # Wait for a short time for any events, then break
                        await asyncio.sleep(2)
            except Exception as e:
                results.append({
                    "name": "sse_connection",
                    "result": "FAIL",
                    "message": f"SSE connection failed: {str(e)}",
                    "time": time.time() - start_time
                })
    
    except Exception as e:
        results.append({
            "name": "unexpected_error",
            "result": "FAIL",
            "message": f"Unexpected error: {str(e)}",
            "time": time.time() - start_time
        })
    
    total_time = time.time() - start_time
    print(f"Tests completed in {total_time:.2f} seconds")
    
    # Generate summary
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = sum(1 for r in results if r["result"] == "FAIL")
    
    print(f"\nSummary: {passed}/{total} tests passed. {failed} failed.")
    
    if passed == total:
        print("\nAll tests passed! Server is working properly.")
    
    # Generate report
    generate_report(results, success_endpoint or server_url)
    
    return results

def generate_report(results, server_url):
    """Generate a Markdown report for the test results"""
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = sum(1 for r in results if r["result"] == "FAIL")
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report_path = REPORTS_DIR / f"simple_sse_test_{now}.md"
    
    lines = [
        f"# Simple MCP HTTP/SSE Server Test Report\n",
        f"**Server URL:** `{server_url}`  ",
        f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"## Summary\n",
        f"- **Total Tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        f"- **Success Rate:** {(passed / total) * 100:.1f}%\n",
        f"## Detailed Results\n",
        "| Test | Result | Message | Time (s) |",
        "|------|--------|---------|----------|",
    ]
    
    for r in results:
        lines.append(f"| {r['name']} | {r['result']} | {r['message']} | {r['time']:.2f} |")
    
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"\nReport saved to: {report_path}")

async def main():
    """Run the script"""
    parser = argparse.ArgumentParser(description="Simple test for MCP HTTP/SSE servers")
    parser.add_argument("--server-url", default="http://localhost:8086/mcp",
                       help="URL of the MCP HTTP/SSE server (default: http://localhost:8086/mcp)")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Request timeout in seconds (default: 30)")
    args = parser.parse_args()
    
    await test_server(args.server_url, args.timeout)

if __name__ == "__main__":
    asyncio.run(main()) 