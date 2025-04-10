"""
Unit tests for the reporter module.
"""

import pytest
from mcp_testing.utils.reporter import extract_server_name, generate_markdown_report

class TestReporter:
    """Tests for the reporter module functions."""

    def test_extract_server_name(self):
        """Test extraction of server name from command strings."""
        # Test different command formats
        assert extract_server_name("minimal_mcp_server.py") == "Minimal Mcp Server"
        assert extract_server_name("./minimal_mcp_server/minimal_mcp_server.py") == "Minimal Mcp Server"
        # The function now returns 'Python' for python commands
        assert extract_server_name("python -m mcp_server_fetch") == "Python"
        assert extract_server_name("npx -y @modelcontextprotocol/server-brave-search") == "Brave Search"
        
        # Test with arguments
        assert extract_server_name("minimal_http_server.py --port 8080") == "Minimal Http Server"
        
        # Test with absolute paths
        assert extract_server_name("/usr/local/bin/mcp-server") == "Mcp Server"

    def test_generate_markdown_report(self):
        """Test markdown report generation with sample data."""
        # Sample test results
        results = {
            "total": 10,
            "passed": 8,
            "failed": 2,
            "results": [
                {"name": "test_1", "passed": True, "duration": 0.1},
                {"name": "test_2", "passed": True, "duration": 0.2},
                {"name": "test_3", "passed": False, "duration": 0.3, "message": "Failed test"},
                {"name": "test_4", "passed": False, "duration": 0.4, "message": "Another failure"},
                {"name": "test_5", "passed": True, "duration": 0.5},
                {"name": "test_6", "passed": True, "duration": 0.6},
                {"name": "test_7", "passed": True, "duration": 0.7},
                {"name": "test_8", "passed": True, "duration": 0.8},
                {"name": "test_9", "passed": True, "duration": 0.9},
                {"name": "test_10", "passed": True, "duration": 1.0},
            ]
        }
        
        server_command = "./minimal_mcp_server/minimal_mcp_server.py"
        protocol_version = "2025-03-26"
        
        # Generate the report
        report = generate_markdown_report(results, server_command, protocol_version)
        
        # Check that basic elements are in the report
        assert "# Minimal Mcp Server MCP Compliance Report" in report
        assert "**Total Tests**: 10" in report
        assert "**Passed**: 8 (80.0%)" in report
        assert "**Failed**: 2 (20.0%)" in report
        assert "**Compliance Status**: ⚠️ Mostly Compliant" in report

        # With 100% passing
        perfect_results = {
            "total": 10,
            "passed": 10,
            "failed": 0,
            "results": [{"name": f"test_{i}", "passed": True, "duration": 0.1} for i in range(1, 11)]
        }
        
        perfect_report = generate_markdown_report(perfect_results, server_command, protocol_version)
        assert "**Compliance Status**: ✅ Fully Compliant" in perfect_report

        # With poor results
        poor_results = {
            "total": 10,
            "passed": 7,
            "failed": 3,
            "results": [
                {"name": f"test_{i}", "passed": i < 8, "duration": 0.1} for i in range(1, 11)
            ]
        }
        
        poor_report = generate_markdown_report(poor_results, server_command, protocol_version)
        # The function now classifies 70% as Non-Compliant, not "Mostly Compliant"
        assert "**Compliance Status**: ❌ Non-Compliant (70.0%)" in poor_report

        # Very poor results
        very_poor_results = {
            "total": 10,
            "passed": 5,
            "failed": 5,
            "results": [
                {"name": f"test_{i}", "passed": i < 6, "duration": 0.1} for i in range(1, 11)
            ]
        }
        
        very_poor_report = generate_markdown_report(very_poor_results, server_command, protocol_version)
        assert "**Compliance Status**: ❌ Non-Compliant (50.0%)" in very_poor_report 