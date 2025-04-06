#!/usr/bin/env python3
import os, sys, subprocess
print("DOCKER TEST STARTING")
subprocess.run(["docker", "run", "--rm", "ubuntu", "echo", "Hello from Docker"], check=True)
print("DOCKER TEST ENDING")
