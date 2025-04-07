#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time

# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.


print("BEGIN TEST")
sys.stdout.flush()

# Check for Docker network
print("Checking for Docker network")
sys.stdout.flush()
try:
    result = subprocess.run(
        ["docker", "network", "inspect", "mcp-test-network"],
        capture_output=True,
        text=True
    )
    print("Network check result:", result.returncode)
    sys.stdout.flush()
except Exception as e:
    print("Error checking network:", e)
    sys.stdout.flush()

# Start a simple server
print("About to start Docker container")
sys.stdout.flush()
try:
    # This is a minimal command just to see if output is working
    cmd = "echo 'hello from docker' && sleep 5"
    docker_cmd = f"docker run --rm -i ubuntu bash -c '{cmd}'"
    print("Docker command:", docker_cmd)
    sys.stdout.flush()
    
    process = subprocess.Popen(
        docker_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("Process started, waiting for output")
    sys.stdout.flush()
    
    stdout, stderr = process.communicate(timeout=10)
    
    print("Docker stdout:", stdout)
    print("Docker stderr:", stderr)
    print("Exit code:", process.returncode)
    sys.stdout.flush()
except Exception as e:
    print("Error running Docker:", e)
    sys.stdout.flush()

print("END TEST")
sys.stdout.flush() 