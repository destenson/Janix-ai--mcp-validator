#!/usr/bin/env python3
"""
Simple script to create a test file in a specific directory.
"""

import os
import sys
import datetime

def main():
    # Create test_output directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created directory: {output_dir}")
    
    # Create a test file
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/test_file_{timestamp}.txt"
    
    # Write to the file
    with open(filename, "w") as f:
        f.write(f"Test file created at {now}\n")
        f.write(f"Current working directory: {os.getcwd()}\n")
        f.write(f"Python version: {sys.version}\n")
    
    # Verify file exists
    if os.path.exists(filename):
        print(f"Successfully created file: {filename}")
        print(f"File size: {os.path.getsize(filename)} bytes")
    else:
        print(f"ERROR: File does not exist after writing: {filename}")
    
    # List contents of directory
    print(f"\nContents of {output_dir}:")
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isfile(item_path):
            print(f"  - {item} ({os.path.getsize(item_path)} bytes)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 