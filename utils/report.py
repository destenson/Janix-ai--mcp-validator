"""
Report generation utilities for the MCP protocol validator.

This module provides functionality for generating HTML and JSON reports
from test results.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import html


class TestReport:
    """Class for collecting and generating test reports."""
    
    def __init__(self, title: str = "MCP Protocol Validator Report"):
        """
        Initialize a new test report.
        
        Args:
            title: The title for the report
        """
        self.title = title
        self.start_time = time.time()
        self.end_time = None
        self.results = []
        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0
        }
        self.metadata = {
            "timestamp": datetime.now().isoformat(),
            "transport_type": None,
            "protocol_version": None,
            "server_info": None
        }
    
    def set_metadata(self, transport_type: str, protocol_version: str, 
                    server_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Set metadata for the test report.
        
        Args:
            transport_type: The transport type used for testing
            protocol_version: The protocol version being tested
            server_info: Optional server information
        """
        self.metadata["transport_type"] = transport_type
        self.metadata["protocol_version"] = protocol_version
        self.metadata["server_info"] = server_info
    
    def add_result(self, test_name: str, status: str, duration: float, 
                  message: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a test result to the report.
        
        Args:
            test_name: The name of the test
            status: The test status ("passed", "failed", "skipped", "error")
            duration: The test duration in seconds
            message: Optional message describing the result
            details: Optional details about the test execution
        """
        result = {
            "name": test_name,
            "status": status,
            "duration": duration,
            "message": message,
            "details": details or {}
        }
        
        self.results.append(result)
        
        # Update summary
        self.summary["total"] += 1
        if status in self.summary:
            self.summary[status] += 1
    
    def finalize(self) -> None:
        """Finalize the report by setting the end time."""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the report to a dictionary.
        
        Returns:
            A dictionary representation of the report
        """
        if self.end_time is None:
            self.finalize()
            
        return {
            "title": self.title,
            "metadata": self.metadata,
            "summary": self.summary,
            "duration": self.end_time - self.start_time,
            "results": self.results
        }
    
    def to_json(self, pretty: bool = True) -> str:
        """
        Convert the report to a JSON string.
        
        Args:
            pretty: Whether to format the JSON with indentation
            
        Returns:
            A JSON string representation of the report
        """
        indent = 2 if pretty else None
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_html(self) -> str:
        """
        Convert the report to an HTML string.
        
        Returns:
            An HTML string representation of the report
        """
        if self.end_time is None:
            self.finalize()
            
        # Calculate duration
        duration = self.end_time - self.start_time
        
        # Start building HTML
        html_parts = []
        
        # HTML header
        html_parts.append(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(self.title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #444;
        }}
        .summary {{
            background-color: #f5f5f5;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .summary-item {{
            padding: 10px 15px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .total {{
            background-color: #e0e0e0;
        }}
        .passed {{
            background-color: #d4edda;
            color: #155724;
        }}
        .failed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .skipped {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .error {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .metadata {{
            margin-bottom: 20px;
            font-size: 0.9em;
        }}
        .metadata table {{
            border-collapse: collapse;
            width: 100%;
        }}
        .metadata td, .metadata th {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        .test-results {{
            border-collapse: collapse;
            width: 100%;
        }}
        .test-results th, .test-results td {{
            border: 1px solid #ddd;
            padding: 12px 8px;
            text-align: left;
        }}
        .test-results th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .test-results tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .test-results tr:hover {{
            background-color: #f5f5f5;
        }}
        .test-details {{
            font-family: monospace;
            white-space: pre-wrap;
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin-top: 10px;
            overflow-x: auto;
            display: none;
        }}
        .toggle-details {{
            background-color: #e7e7e7;
            border: none;
            color: black;
            padding: 5px 10px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 12px;
            margin: 2px;
            cursor: pointer;
            border-radius: 3px;
        }}
    </style>
    <script>
        function toggleDetails(id) {{
            var element = document.getElementById(id);
            if (element.style.display === "block") {{
                element.style.display = "none";
            }} else {{
                element.style.display = "block";
            }}
        }}
    </script>
</head>
<body>
    <h1>{html.escape(self.title)}</h1>
""")
        
        # Metadata section
        html_parts.append(f"""
    <div class="metadata">
        <h2>Test Information</h2>
        <table>
            <tr><td><strong>Date:</strong></td><td>{self.metadata["timestamp"]}</td></tr>
            <tr><td><strong>Duration:</strong></td><td>{duration:.2f} seconds</td></tr>
            <tr><td><strong>Transport:</strong></td><td>{self.metadata["transport_type"] or "N/A"}</td></tr>
            <tr><td><strong>Protocol Version:</strong></td><td>{self.metadata["protocol_version"] or "N/A"}</td></tr>
        </table>
""")
        
        # Add server info if available
        if self.metadata["server_info"]:
            html_parts.append("""
        <h3>Server Information</h3>
        <table>
""")
            for key, value in self.metadata["server_info"].items():
                html_parts.append(f"            <tr><td><strong>{html.escape(str(key))}:</strong></td><td>{html.escape(str(value))}</td></tr>\n")
            html_parts.append("        </table>\n")
            
        html_parts.append("    </div>\n")
        
        # Summary section
        html_parts.append(f"""
    <div class="summary">
        <div class="summary-item total">Total: {self.summary["total"]}</div>
        <div class="summary-item passed">Passed: {self.summary["passed"]}</div>
        <div class="summary-item failed">Failed: {self.summary["failed"]}</div>
        <div class="summary-item skipped">Skipped: {self.summary["skipped"]}</div>
        <div class="summary-item error">Errors: {self.summary["error"]}</div>
    </div>
""")
        
        # Results table
        html_parts.append("""
    <h2>Test Results</h2>
    <table class="test-results">
        <thead>
            <tr>
                <th>Test</th>
                <th>Status</th>
                <th>Duration (s)</th>
                <th>Message</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>
""")
        
        # Add each result row
        for i, result in enumerate(self.results):
            status_class = result["status"]
            details_id = f"details-{i}"
            
            html_parts.append(f"""
            <tr class="{status_class}">
                <td>{html.escape(result["name"])}</td>
                <td class="{status_class}">{html.escape(result["status"])}</td>
                <td>{result["duration"]:.3f}</td>
                <td>{html.escape(result["message"] or "")}</td>
                <td>
""")
            
            # Only add details toggle if there are details
            if result["details"]:
                html_parts.append(f"""
                    <button class="toggle-details" onclick="toggleDetails('{details_id}')">Toggle Details</button>
                    <div id="{details_id}" class="test-details">
{html.escape(json.dumps(result["details"], indent=2))}
                    </div>
""")
            else:
                html_parts.append("None")
                
            html_parts.append("""
                </td>
            </tr>
""")
            
        # Close the table and HTML
        html_parts.append("""
        </tbody>
    </table>
</body>
</html>
""")
        
        return "".join(html_parts)
    
    def save(self, output_path: Optional[str] = None, format: str = "html") -> str:
        """
        Save the report to a file.
        
        Args:
            output_path: The path to save the report to.
                If None, a default path will be generated.
            format: The format to save the report in ("html" or "json")
            
        Returns:
            The path the report was saved to
        """
        if self.end_time is None:
            self.finalize()
            
        # Generate default filename if none provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            transport = self.metadata["transport_type"] or "unknown"
            protocol = self.metadata["protocol_version"] or "unknown"
            filename = f"mcp-report-{transport}-{protocol}-{timestamp}.{format}"
            
            # Create reports directory if it doesn't exist
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            output_path = str(reports_dir / filename)
        
        # Convert report to requested format
        if format.lower() == "html":
            content = self.to_html()
        elif format.lower() == "json":
            content = self.to_json()
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return output_path 