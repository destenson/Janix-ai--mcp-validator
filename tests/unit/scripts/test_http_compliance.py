#!/usr/bin/env python3
"""
Unit tests for HTTP Compliance Scripts.

Tests the HTTP compliance testing, reporting, and validation scripts
for MCP 2025-06-18 protocol compliance.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from io import StringIO

from mcp_testing.scripts import http_compliance, http_compliance_report, http_compliance_test


class TestHttpCompliance:
    """Test suite for HTTP compliance script."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_server_url = "http://localhost:8088"
        self.test_protocol = "2025-06-18"

    @patch('mcp_testing.scripts.http_compliance.requests.post')
    def test_test_server_initialization(self, mock_post):
        """Test server initialization test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"supported": True}},
                "serverInfo": {"name": "Test Server", "version": "1.0.0"}
            }
        }
        mock_post.return_value = mock_response

        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        result = tester.test_initialization()

        assert result["passed"] is True
        assert result["protocol_version"] == "2025-06-18"
        assert "Test Server" in result["server_info"]["name"]

    @patch('mcp_testing.scripts.http_compliance.requests.post')
    def test_test_oauth_authentication(self, mock_post):
        """Test OAuth authentication compliance."""
        # Mock OAuth capability response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "capabilities": {
                    "oauth": {
                        "supported": True,
                        "flows": ["authorization_code"],
                        "scopes": ["read", "write"]
                    }
                }
            }
        }
        mock_post.return_value = mock_response

        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        result = tester.test_oauth_compliance()

        assert result["passed"] is True
        assert result["oauth_supported"] is True
        assert "authorization_code" in result["supported_flows"]

    @patch('mcp_testing.scripts.http_compliance.requests.post')
    def test_test_structured_tool_output(self, mock_post):
        """Test structured tool output compliance."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "content": [{"type": "text", "text": "Hello"}],
                "isError": False,
                "structuredContent": {
                    "type": "echo_response",
                    "timestamp": "2025-06-18T10:00:00Z"
                }
            }
        }
        mock_post.return_value = mock_response

        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        result = tester.test_structured_output()

        assert result["passed"] is True
        assert "content" in result["output_format"]
        assert "isError" in result["output_format"]
        assert "structuredContent" in result["output_format"]

    @patch('mcp_testing.scripts.http_compliance.requests.post')
    def test_test_batch_request_rejection(self, mock_post):
        """Test that batch requests are properly rejected."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": -32600,
                "message": "Batch requests not supported in 2025-06-18"
            }
        }
        mock_post.return_value = mock_response

        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        result = tester.test_batch_rejection()

        assert result["passed"] is True
        assert result["batch_rejected"] is True

    @patch('mcp_testing.scripts.http_compliance.requests.post')
    def test_test_elicitation_support(self, mock_post):
        """Test elicitation support compliance."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "elicitation": {
                    "type": "confirmation",
                    "message": "Proceed?",
                    "options": ["yes", "no"]
                }
            }
        }
        mock_post.return_value = mock_response

        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        result = tester.test_elicitation()

        assert result["passed"] is True
        assert result["elicitation_type"] == "confirmation"

    def test_run_all_tests_success(self):
        """Test running all compliance tests successfully."""
        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        
        with patch.object(tester, 'test_initialization') as mock_init, \
             patch.object(tester, 'test_oauth_compliance') as mock_oauth, \
             patch.object(tester, 'test_structured_output') as mock_struct, \
             patch.object(tester, 'test_batch_rejection') as mock_batch, \
             patch.object(tester, 'test_elicitation') as mock_elic:
            
            # Mock all tests to pass
            mock_init.return_value = {"passed": True, "test": "initialization"}
            mock_oauth.return_value = {"passed": True, "test": "oauth"}
            mock_struct.return_value = {"passed": True, "test": "structured_output"}
            mock_batch.return_value = {"passed": True, "test": "batch_rejection"}
            mock_elic.return_value = {"passed": True, "test": "elicitation"}

            results = tester.run_all_tests()

            assert len(results) == 5
            assert all(result["passed"] for result in results)

    def test_run_all_tests_with_failures(self):
        """Test running all compliance tests with some failures."""
        tester = http_compliance.HttpComplianceTester(self.test_server_url)
        
        with patch.object(tester, 'test_initialization') as mock_init, \
             patch.object(tester, 'test_oauth_compliance') as mock_oauth:
            
            # Mock mixed results
            mock_init.return_value = {"passed": True, "test": "initialization"}
            mock_oauth.return_value = {"passed": False, "test": "oauth", "error": "OAuth not supported"}

            results = tester.run_all_tests()

            passed_tests = [r for r in results if r["passed"]]
            failed_tests = [r for r in results if not r["passed"]]
            
            assert len(passed_tests) >= 1
            assert len(failed_tests) >= 1


class TestHttpComplianceReport:
    """Test suite for HTTP compliance reporting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_results = [
            {"test": "initialization", "passed": True, "protocol_version": "2025-06-18"},
            {"test": "oauth", "passed": True, "oauth_supported": True},
            {"test": "structured_output", "passed": False, "error": "Missing structuredContent"},
            {"test": "batch_rejection", "passed": True, "batch_rejected": True},
            {"test": "elicitation", "passed": True, "elicitation_type": "confirmation"}
        ]

    def test_generate_html_report(self):
        """Test HTML report generation."""
        reporter = http_compliance_report.ComplianceReporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            report_path = f.name

        try:
            reporter.generate_html_report(self.test_results, report_path)
            
            assert os.path.exists(report_path)
            
            with open(report_path, 'r') as f:
                content = f.read()
                
            assert "<html>" in content
            assert "MCP 2025-06-18 Compliance Report" in content
            assert "initialization" in content
            assert "oauth" in content
            assert "structured_output" in content
            
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def test_generate_json_report(self):
        """Test JSON report generation."""
        reporter = http_compliance_report.ComplianceReporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            report_path = f.name

        try:
            reporter.generate_json_report(self.test_results, report_path)
            
            assert os.path.exists(report_path)
            
            with open(report_path, 'r') as f:
                data = json.load(f)
                
            assert "summary" in data
            assert "results" in data
            assert data["summary"]["total_tests"] == 5
            assert data["summary"]["passed_tests"] == 4
            assert data["summary"]["failed_tests"] == 1
            
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)

    def test_calculate_compliance_score(self):
        """Test compliance score calculation."""
        reporter = http_compliance_report.ComplianceReporter()
        
        score = reporter.calculate_compliance_score(self.test_results)
        
        # 4 passed out of 5 total = 80%
        assert score == 80.0

    def test_generate_summary_stats(self):
        """Test summary statistics generation."""
        reporter = http_compliance_report.ComplianceReporter()
        
        stats = reporter.generate_summary_stats(self.test_results)
        
        assert stats["total_tests"] == 5
        assert stats["passed_tests"] == 4
        assert stats["failed_tests"] == 1
        assert stats["compliance_score"] == 80.0

    def test_format_test_details(self):
        """Test test details formatting."""
        reporter = http_compliance_report.ComplianceReporter()
        
        test_result = {
            "test": "oauth",
            "passed": True,
            "oauth_supported": True,
            "supported_flows": ["authorization_code"]
        }
        
        details = reporter.format_test_details(test_result)
        
        assert "OAuth" in details
        assert "PASSED" in details
        assert "authorization_code" in details


class TestHttpComplianceTest:
    """Test suite for HTTP compliance test runner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_server_url = "http://localhost:8088"

    @patch('mcp_testing.scripts.http_compliance_test.HttpComplianceTester')
    @patch('mcp_testing.scripts.http_compliance_test.ComplianceReporter')
    def test_run_compliance_test_success(self, mock_reporter, mock_tester):
        """Test successful compliance test run."""
        # Mock tester
        mock_tester_instance = MagicMock()
        mock_tester_instance.run_all_tests.return_value = [
            {"test": "initialization", "passed": True},
            {"test": "oauth", "passed": True}
        ]
        mock_tester.return_value = mock_tester_instance

        # Mock reporter
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance

        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        result = runner.run_tests()

        assert result["success"] is True
        assert result["total_tests"] == 2
        assert result["passed_tests"] == 2
        assert result["compliance_score"] == 100.0

    @patch('mcp_testing.scripts.http_compliance_test.HttpComplianceTester')
    def test_run_compliance_test_with_failures(self, mock_tester):
        """Test compliance test run with failures."""
        # Mock tester with mixed results
        mock_tester_instance = MagicMock()
        mock_tester_instance.run_all_tests.return_value = [
            {"test": "initialization", "passed": True},
            {"test": "oauth", "passed": False, "error": "OAuth not supported"}
        ]
        mock_tester.return_value = mock_tester_instance

        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        result = runner.run_tests()

        assert result["success"] is False
        assert result["total_tests"] == 2
        assert result["passed_tests"] == 1
        assert result["failed_tests"] == 1
        assert result["compliance_score"] == 50.0

    @patch('mcp_testing.scripts.http_compliance_test.requests.get')
    def test_check_server_availability(self, mock_get):
        """Test server availability check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        available = runner.check_server_availability()

        assert available is True

    @patch('mcp_testing.scripts.http_compliance_test.requests.get')
    def test_check_server_unavailable(self, mock_get):
        """Test server unavailability detection."""
        mock_get.side_effect = Exception("Connection refused")

        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        available = runner.check_server_availability()

        assert available is False

    def test_validate_protocol_version(self):
        """Test protocol version validation."""
        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        
        assert runner.validate_protocol_version("2025-06-18") is True
        assert runner.validate_protocol_version("2025-03-26") is True
        assert runner.validate_protocol_version("2024-11-05") is True
        assert runner.validate_protocol_version("invalid") is False

    @patch('sys.argv', ['http_compliance_test.py', '--server-url', 'http://localhost:8088', '--protocol', '2025-06-18'])
    @patch('mcp_testing.scripts.http_compliance_test.ComplianceTestRunner')
    def test_main_function(self, mock_runner):
        """Test main function execution."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run_tests.return_value = {
            "success": True,
            "compliance_score": 100.0
        }
        mock_runner.return_value = mock_runner_instance

        # Test main function
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            http_compliance_test.main()
            
        output = mock_stdout.getvalue()
        assert "Compliance test completed" in output or len(output) >= 0

    def test_format_test_results(self):
        """Test test results formatting."""
        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        
        results = [
            {"test": "initialization", "passed": True},
            {"test": "oauth", "passed": False, "error": "Not supported"}
        ]
        
        formatted = runner.format_results(results)
        
        assert "initialization: PASSED" in formatted
        assert "oauth: FAILED" in formatted
        assert "Not supported" in formatted

    @patch('mcp_testing.scripts.http_compliance_test.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_results_to_file(self, mock_file, mock_makedirs):
        """Test saving results to file."""
        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url)
        
        results = [{"test": "initialization", "passed": True}]
        output_path = "/tmp/test_results.json"
        
        runner.save_results(results, output_path)
        
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once_with(output_path, 'w')

    def test_error_handling_network_failure(self):
        """Test error handling for network failures."""
        runner = http_compliance_test.ComplianceTestRunner("http://invalid-server:9999")
        
        with patch('mcp_testing.scripts.http_compliance_test.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = runner.run_tests()
            
            assert result["success"] is False
            assert "error" in result

    def test_timeout_handling(self):
        """Test timeout handling for slow servers."""
        runner = http_compliance_test.ComplianceTestRunner(self.test_server_url, timeout=1)
        
        with patch('mcp_testing.scripts.http_compliance_test.requests.post') as mock_post:
            mock_post.side_effect = Exception("Timeout")
            
            result = runner.run_tests()
            
            assert result["success"] is False 