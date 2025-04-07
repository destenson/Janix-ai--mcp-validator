#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Script to migrate legacy test files to the legacy directory and add deprecation warnings.
"""

import os
import sys
import shutil
import re

LEGACY_DIR = "legacy"
DEPRECATION_NOTICE = """
# DEPRECATION WARNING: This script is part of the legacy test framework.
# It is maintained for backward compatibility but will be removed in a future release.
# Please use the new unified test framework in the tests/ directory instead.
# See docs/legacy_tests.md for more information.
"""

def ensure_legacy_dir():
    """Ensure the legacy directory exists."""
    if not os.path.exists(LEGACY_DIR):
        os.makedirs(LEGACY_DIR)
        print(f"Created legacy directory: {LEGACY_DIR}")

def get_legacy_files():
    """Get a list of legacy test files to migrate."""
    legacy_files = []
    for filename in os.listdir("."):
        if os.path.isfile(filename) and (
            filename.endswith("_test.py") or 
            filename.startswith("test_") or
            "_test_" in filename
        ) and filename != "migrate_legacy_scripts.py":
            legacy_files.append(filename)
    return sorted(legacy_files)

def add_deprecation_notice(file_path):
    """Add a deprecation notice to a file."""
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if file already has a shebang line or imports
    lines = content.split("\n")
    insert_pos = 0
    
    # Find position after shebang and imports
    for i, line in enumerate(lines):
        if i == 0 and line.startswith("#!"):
            insert_pos = 1
            continue
        if line.startswith("import ") or line.startswith("from ") or line.startswith("#"):
            insert_pos = i + 1
        else:
            break
    
    # Avoid adding the notice if it's already there
    if "DEPRECATION WARNING" in content:
        return content
    
    # Insert the deprecation notice
    lines.insert(insert_pos, DEPRECATION_NOTICE)
    return "\n".join(lines)

def migrate_file(filename):
    """Migrate a legacy file to the legacy directory with a deprecation notice."""
    original_path = os.path.join(".", filename)
    target_path = os.path.join(LEGACY_DIR, filename)
    
    # Add deprecation notice
    content = add_deprecation_notice(original_path)
    
    # Write the updated content to the legacy directory
    with open(target_path, "w") as f:
        f.write(content)
    
    print(f"Migrated: {filename} -> {target_path}")
    return True

def main():
    """Main function to migrate legacy test files."""
    ensure_legacy_dir()
    legacy_files = get_legacy_files()
    
    if not legacy_files:
        print("No legacy test files found to migrate.")
        return
    
    print(f"Found {len(legacy_files)} legacy test files to migrate:")
    for filename in legacy_files:
        print(f"  - {filename}")
    
    confirmation = input("\nDo you want to proceed with migration? (y/n): ")
    if confirmation.lower() != "y":
        print("Migration aborted.")
        return
    
    success_count = 0
    for filename in legacy_files:
        try:
            if migrate_file(filename):
                success_count += 1
        except Exception as e:
            print(f"Error migrating {filename}: {e}")
    
    print(f"\nSuccessfully migrated {success_count} of {len(legacy_files)} files to {LEGACY_DIR}/")
    
    # Ask if the user wants to remove the original files
    if success_count > 0:
        remove = input("\nDo you want to remove the original files? (y/n): ")
        if remove.lower() == "y":
            remove_count = 0
            for filename in legacy_files:
                try:
                    os.remove(os.path.join(".", filename))
                    remove_count += 1
                    print(f"Removed: {filename}")
                except Exception as e:
                    print(f"Error removing {filename}: {e}")
            print(f"\nRemoved {remove_count} original files.")

if __name__ == "__main__":
    main() 