#!/usr/bin/env python3
import os, sys, subprocess
print("TEST STARTING")
sys.stdout.flush()
subprocess.run(["echo", "Hello from subprocess"], check=True)
print("TEST ENDING")
sys.stdout.flush()
