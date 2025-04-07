#!/usr/bin/env python3
"""
Simple test file to verify pytest-md reporting functionality.
"""

def test_simple_pass():
    """A simple test that passes."""
    assert True

def test_simple_with_output():
    """A test with some output."""
    print("This is a test output")
    assert 1 + 1 == 2 