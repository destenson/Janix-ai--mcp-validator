#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the report.py module.
"""

import unittest
from mcp_testing.utils.report import generate_compliance_score


class TestReport(unittest.TestCase):
    """Test cases for the report module."""

    def test_generate_compliance_score_zero_tests(self):
        """Test that compliance score is 0 when there are no tests."""
        results = {"total": 0, "passed": 0, "failed": 0}
        score = generate_compliance_score(results)
        self.assertEqual(score, 0.0)

    def test_generate_compliance_score_all_passed(self):
        """Test that compliance score is 100% when all tests pass."""
        results = {"total": 10, "passed": 10, "failed": 0}
        score = generate_compliance_score(results)
        self.assertEqual(score, 100.0)

    def test_generate_compliance_score_all_failed(self):
        """Test that compliance score is 0% when all tests fail."""
        results = {"total": 10, "passed": 0, "failed": 10}
        score = generate_compliance_score(results)
        self.assertEqual(score, 0.0)

    def test_generate_compliance_score_partial(self):
        """Test that compliance score is correctly calculated for partial success."""
        results = {"total": 10, "passed": 7, "failed": 3}
        score = generate_compliance_score(results)
        self.assertEqual(score, 70.0)

    def test_generate_compliance_score_rounding(self):
        """Test that compliance score is rounded to one decimal place."""
        results = {"total": 3, "passed": 1, "failed": 2}
        score = generate_compliance_score(results)
        self.assertEqual(score, 33.3)


if __name__ == "__main__":
    unittest.main() 