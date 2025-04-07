#!/usr/bin/env python3

"""
Test script to verify imports used in run_validator.py
"""

import asyncio
import importlib
import os
import sys
import pytest
from pathlib import Path
from typing import List, Optional

try:
    print("Importing utils modules...")
    from utils.config import get_config, MCPValidatorConfig
    from utils.logging import configure_logging, get_logger
    print("Successfully imported utils modules.")
except ImportError as e:
    print(f"Error importing utils modules: {e}")

try:
    print("Importing protocols module...")
    from protocols import get_protocol_adapter, MCPProtocolAdapter
    print("Successfully imported protocols module.")
except ImportError as e:
    print(f"Error importing protocols module: {e}")

try:
    print("Importing transport modules...")
    from transport import MCPTransport, HTTPTransport, STDIOTransport
    print("Successfully imported transport modules.")
except ImportError as e:
    print(f"Error importing transport module: {e}")

if __name__ == "__main__":
    print("Python version:", sys.version)
    print("Python executable:", sys.executable)
    print("PYTHONPATH:", os.environ.get("PYTHONPATH", "Not set")) 