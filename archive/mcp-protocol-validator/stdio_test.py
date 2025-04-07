#!/usr/bin/env python3
import os, sys, subprocess, json, time
print("Starting STDIO test")
network_cmd = ["docker", "network", "inspect", "mcp-test-network"]
result = subprocess.run(network_cmd, capture_output=True, text=True)
print("Network exists:", result.returncode == 0)
