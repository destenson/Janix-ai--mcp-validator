#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test client script for the MCP HTTP Server V2.

This script directly imports and runs the V2 test client without package issues.
"""

import sys
import os

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, parent_dir)

# Import the test client components
from ref_http_server.test_client import main

if __name__ == "__main__":
    main() 