#!/usr/bin/env python3
"""
Report Generator Module

Processes pytest test results and generates compliance reports with
weighted scoring based on requirement types (MUST, SHOULD, MAY).
"""

import os
import json
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple, Set, Optional
import markdown
from rich.console import Console
from rich.table import Table

# Constants for requirement weighting
MUST_WEIGHT = 10
SHOULD_WEIGHT = 3
MAY_WEIGHT = 1

# Constants for requirement severity emojis
CRITICAL_EMOJI = "🔴"
MEDIUM_EMOJI = "🟠"
LOW_EMOJI = "🟢"

class MCPReportGenerator:
    """Processes test results and generates MCP compliance reports."""
    
    def __init__(self, junit_xml_path: str, server_info: Dict[str, str]):
        """Initialize the report generator.
        
        Args:
            junit_xml_path: Path to the JUnit XML report from pytest.
            server_info: Dictionary with server information.
        """
        self.junit_xml_path = junit_xml_path
        self.server_info = server_info
        self.test_results = self._parse_junit_xml()
        self.must_results = {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        self.should_results = {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        self.may_results = {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        self.section_results = {}
        self.weighted_score = 0.0
        self.compliance_level = ""
        
    def _parse_junit_xml(self) -> Dict[str, Any]:
        """Parse the JUnit XML report into structured test data.
        
        Returns:
            Dictionary with parsed test results.
        """
        if not os.path.exists(self.junit_xml_path):
            raise FileNotFoundError(f"JUnit XML report not found at {self.junit_xml_path}")
            
        tree = ET.parse(self.junit_xml_path)
        root = tree.getroot()
        
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'tests': []
        }
        
        for testsuite in root.findall('.//testsuite'):
            for testcase in testsuite.findall('.//testcase'):
                test_data = {
                    'name': testcase.get('name'),
                    'classname': testcase.get('classname'),
                    'time': float(testcase.get('time', 0)),
                    'requirements': self._extract_requirements_from_markers(testcase),
                    'status': 'passed',
                    'message': '',
                    'section': self._extract_section_from_classname(testcase.get('classname', ''))
                }
                
                # Check for failures
                failure = testcase.find('failure')
                if failure is not None:
                    test_data['status'] = 'failed'
                    test_data['message'] = failure.get('message', '')
                    results['failed'] += 1
                else:
                    # Check for skips
                    skipped = testcase.find('skipped')
                    if skipped is not None:
                        test_data['status'] = 'skipped'
                        test_data['message'] = skipped.get('message', '')
                        results['skipped'] += 1
                    else:
                        results['passed'] += 1
                
                results['tests'].append(test_data)
                results['total'] += 1
                
        return results
    
    def _extract_requirements_from_markers(self, testcase: ET.Element) -> List[Dict[str, str]]:
        """Extract requirement IDs and levels from test markers.
        
        Args:
            testcase: XML element for the test case.
            
        Returns:
            List of requirement dictionaries.
        """
        requirements = []
        
        # Extract from properties
        properties = testcase.find('properties')
        if properties is not None:
            for prop in properties.findall('property'):
                name = prop.get('name', '')
                value = prop.get('value', '')
                
                if name == 'requirement':
                    # Parse individual requirement
                    req_id = value
                    req_level = self._determine_requirement_level(req_id)
                    req_severity = self._determine_requirement_severity(req_level)
                    
                    requirements.append({
                        'id': req_id,
                        'level': req_level,
                        'severity': req_severity
                    })
                elif name in ['must_requirement', 'should_requirement', 'may_requirement']:
                    # Parse explicitly marked requirements
                    level = name.split('_')[0].upper()
                    requirements.append({
                        'id': value,
                        'level': level,
                        'severity': self._determine_requirement_severity(level)
                    })
        
        return requirements
    
    def _determine_requirement_level(self, req_id: str) -> str:
        """Determine requirement level from ID prefix.
        
        Args:
            req_id: Requirement ID.
            
        Returns:
            Level string ('MUST', 'SHOULD', or 'MAY').
        """
        if req_id.startswith('M'):
            return 'MUST'
        elif req_id.startswith('S'):
            return 'SHOULD'
        elif req_id.startswith('A'):
            return 'MAY'
        return 'MUST'  # Default to MUST
    
    def _determine_requirement_severity(self, level: str) -> str:
        """Map requirement level to severity.
        
        Args:
            level: Requirement level.
            
        Returns:
            Severity string.
        """
        if level == 'MUST':
            return 'Critical'
        elif level == 'SHOULD':
            return 'Medium'
        else:
            return 'Low'
    
    def _extract_section_from_classname(self, classname: str) -> str:
        """Extract test section name from class name.
        
        Args:
            classname: Test class name.
            
        Returns:
            Section name.
        """
        if 'base_protocol' in classname.lower():
            return 'Base Protocol'
        elif 'resources' in classname.lower():
            return 'Resources'
        elif 'tools' in classname.lower():
            return 'Tools'
        elif 'prompts' in classname.lower():
            return 'Prompts'
        elif 'utilities' in classname.lower():
            return 'Utilities'
        elif 'roots' in classname.lower():
            return 'Roots'
        elif 'sampling' in classname.lower():
            return 'Sampling'
        return 'Other'
    
    def _count_requirements_by_type(self) -> None:
        """Count requirements by type (MUST, SHOULD, MAY)."""
        for test in self.test_results['tests']:
            for req in test['requirements']:
                if req['level'] == 'MUST':
                    self.must_results['total'] += 1
                    if test['status'] == 'passed':
                        self.must_results['passed'] += 1
                    elif test['status'] == 'failed':
                        self.must_results['failed'] += 1
                    else:
                        self.must_results['skipped'] += 1
                elif req['level'] == 'SHOULD':
                    self.should_results['total'] += 1
                    if test['status'] == 'passed':
                        self.should_results['passed'] += 1
                    elif test['status'] == 'failed':
                        self.should_results['failed'] += 1
                    else:
                        self.should_results['skipped'] += 1
                elif req['level'] == 'MAY':
                    self.may_results['total'] += 1
                    if test['status'] == 'passed':
                        self.may_results['passed'] += 1
                    elif test['status'] == 'failed':
                        self.may_results['failed'] += 1
                    else:
                        self.may_results['skipped'] += 1
    
    def _calculate_section_scores(self) -> None:
        """Calculate compliance scores by section."""
        # Initialize section data
        sections = set(test['section'] for test in self.test_results['tests'])
        for section in sections:
            self.section_results[section] = {
                'MUST': {'passed': 0, 'total': 0},
                'SHOULD': {'passed': 0, 'total': 0},
                'MAY': {'passed': 0, 'total': 0},
                'weighted_score': 0.0
            }
        
        # Count requirements by section and type
        for test in self.test_results['tests']:
            section = test['section']
            for req in test['requirements']:
                level = req['level']
                if test['status'] != 'skipped':
                    self.section_results[section][level]['total'] += 1
                    if test['status'] == 'passed':
                        self.section_results[section][level]['passed'] += 1
        
        # Calculate weighted scores for each section
        for section, data in self.section_results.items():
            must_score = data['MUST']['passed'] * MUST_WEIGHT
            should_score = data['SHOULD']['passed'] * SHOULD_WEIGHT
            may_score = data['MAY']['passed'] * MAY_WEIGHT
            
            must_total = data['MUST']['total'] * MUST_WEIGHT
            should_total = data['SHOULD']['total'] * SHOULD_WEIGHT
            may_total = data['MAY']['total'] * MAY_WEIGHT
            
            denominator = must_total + should_total + may_total
            if denominator > 0:
                data['weighted_score'] = (must_score + should_score + may_score) / denominator * 100
            else:
                data['weighted_score'] = 0.0
    
    def _calculate_weighted_score(self) -> float:
        """Calculate the overall weighted compliance score.
        
        Returns:
            Weighted compliance score as a percentage.
        """
        must_score = self.must_results['passed'] * MUST_WEIGHT
        should_score = self.should_results['passed'] * SHOULD_WEIGHT
        may_score = self.may_results['passed'] * MAY_WEIGHT
        
        must_total = (self.must_results['passed'] + self.must_results['failed']) * MUST_WEIGHT
        should_total = (self.should_results['passed'] + self.should_results['failed']) * SHOULD_WEIGHT
        may_total = (self.may_results['passed'] + self.may_results['failed']) * MAY_WEIGHT
        
        denominator = must_total + should_total + may_total
        if denominator > 0:
            score = (must_score + should_score + may_score) / denominator * 100
        else:
            score = 0.0
            
        return score
    
    def _determine_compliance_level(self, score: float) -> str:
        """Determine compliance level based on weighted score.
        
        Args:
            score: Weighted compliance score.
            
        Returns:
            Compliance level string.
        """
        if score == 100 and self.must_results['failed'] == 0:
            return "Fully Compliant"
        elif score >= 90:
            return "Substantially Compliant"
        elif score >= 75:
            return "Partially Compliant"
        elif score >= 50:
            return "Minimally Compliant"
        else:
            return "Non-Compliant"
    
    def _get_failed_tests_by_severity(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group failed tests by severity level.
        
        Returns:
            Dictionary of failed tests grouped by severity.
        """
        failed_tests = {
            'Critical': [],
            'Medium': [],
            'Low': []
        }
        
        for test in self.test_results['tests']:
            if test['status'] == 'failed':
                # Determine highest severity among requirements
                highest_severity = 'Low'
                req_ids = []
                
                for req in test['requirements']:
                    req_ids.append(req['id'])
                    if req['severity'] == 'Critical':
                        highest_severity = 'Critical'
                    elif req['severity'] == 'Medium' and highest_severity != 'Critical':
                        highest_severity = 'Medium'
                
                failed_tests[highest_severity].append({
                    'test_name': test['name'],
                    'req_ids': req_ids,
                    'message': test['message'],
                    'section': test['section']
                })
        
        return failed_tests
    
    def generate_report(self, format: str = 'markdown', output_path: str = None) -> str:
        """Generate a compliance report in the specified format.
        
        Args:
            format: Report format ('markdown', 'html', or 'json').
            output_path: Path to save the report.
            
        Returns:
            Report content.
        """
        # Process test results
        self._count_requirements_by_type()
        self._calculate_section_scores()
        self.weighted_score = self._calculate_weighted_score()
        self.compliance_level = self._determine_compliance_level(self.weighted_score)
        
        # Generate report in requested format
        if format == 'markdown':
            report_content = self._generate_markdown_report()
        elif format == 'html':
            markdown_content = self._generate_markdown_report()
            report_content = markdown.markdown(markdown_content, extensions=['tables'])
        elif format == 'json':
            report_content = self._generate_json_report()
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_content)
        
        return report_content
    
    def _generate_markdown_report(self) -> str:
        """Generate a markdown formatted compliance report.
        
        Returns:
            Markdown report as string.
        """
        report = [
            "# MCP Compliance Report",
            "",
            "## Server Information"
        ]
        
        # Server info
        for key, value in self.server_info.items():
            report.append(f"- **{key}**: {value}")
        
        report.append(f"- **Test Date**: {datetime.datetime.now().strftime('%Y-%m-%d')}")
        report.append(f"- **Report Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")
        
        # Compliance summary
        report.append("## Compliance Summary")
        report.append("")
        report.append("| Compliance Level | Score | Status |")
        report.append("|------------------|-------|--------|")
        report.append(f"| **Overall Weighted Score** | **{self.weighted_score:.1f}%** | {self.compliance_level} |")
        report.append("")
        
        # Requirement type breakdown
        report.append("### Requirement Type Breakdown")
        report.append("")
        report.append("| Requirement Type | Total | Passed | Failed | Skipped | Compliance |")
        report.append("|------------------|-------|--------|--------|---------|------------|")
        
        must_compliance = (self.must_results['passed'] / self.must_results['total'] * 100) if self.must_results['total'] > 0 else 0
        should_compliance = (self.should_results['passed'] / self.should_results['total'] * 100) if self.should_results['total'] > 0 else 0
        may_compliance = (self.may_results['passed'] / self.may_results['total'] * 100) if self.may_results['total'] > 0 else 0
        
        report.append(f"| {CRITICAL_EMOJI} **MUST** (Critical) | {self.must_results['total']} | {self.must_results['passed']} | {self.must_results['failed']} | {self.must_results['skipped']} | {must_compliance:.1f}% |")
        report.append(f"| {MEDIUM_EMOJI} **SHOULD** (Medium) | {self.should_results['total']} | {self.should_results['passed']} | {self.should_results['failed']} | {self.should_results['skipped']} | {should_compliance:.1f}% |")
        report.append(f"| {LOW_EMOJI} **MAY** (Low) | {self.may_results['total']} | {self.may_results['passed']} | {self.may_results['failed']} | {self.may_results['skipped']} | {may_compliance:.1f}% |")
        report.append("")
        
        # Section breakdown
        report.append("### Section Breakdown")
        report.append("")
        report.append("| Section | MUST | SHOULD | MAY | Weighted Score |")
        report.append("|---------|------|--------|-----|---------------|")
        
        for section, data in sorted(self.section_results.items()):
            must_str = f"{data['MUST']['passed']}/{data['MUST']['total']} ({data['MUST']['passed']/data['MUST']['total']*100:.1f}%)" if data['MUST']['total'] > 0 else "N/A"
            should_str = f"{data['SHOULD']['passed']}/{data['SHOULD']['total']} ({data['SHOULD']['passed']/data['SHOULD']['total']*100:.1f}%)" if data['SHOULD']['total'] > 0 else "N/A"
            may_str = f"{data['MAY']['passed']}/{data['MAY']['total']} ({data['MAY']['passed']/data['MAY']['total']*100:.1f}%)" if data['MAY']['total'] > 0 else "N/A"
            
            report.append(f"| {section} | {must_str} | {should_str} | {may_str} | {data['weighted_score']:.1f}% |")
        
        report.append("")
        
        # Failed tests by severity
        failed_tests = self._get_failed_tests_by_severity()
        
        # Critical failures (MUST requirements)
        if failed_tests['Critical']:
            report.append(f"## Critical Issues ({CRITICAL_EMOJI} MUST Requirements)")
            report.append("")
            
            for i, test in enumerate(failed_tests['Critical']):
                report.append(f"### {test['section']}: {test['test_name']}")
                report.append(f"- **Requirements**: {', '.join(test['req_ids'])}")
                report.append(f"- **Severity**: {CRITICAL_EMOJI} Critical")
                report.append(f"- **Issue**: {test['message']}")
                report.append("")
        
        # Medium issues (SHOULD requirements)
        if failed_tests['Medium']:
            report.append(f"## Medium Issues ({MEDIUM_EMOJI} SHOULD Requirements)")
            report.append("")
            
            for i, test in enumerate(failed_tests['Medium']):
                report.append(f"### {test['section']}: {test['test_name']}")
                report.append(f"- **Requirements**: {', '.join(test['req_ids'])}")
                report.append(f"- **Severity**: {MEDIUM_EMOJI} Medium")
                report.append(f"- **Issue**: {test['message']}")
                report.append("")
        
        # Low issues (MAY requirements)
        if failed_tests['Low']:
            report.append(f"## Low Issues ({LOW_EMOJI} MAY Requirements)")
            report.append("")
            
            for i, test in enumerate(failed_tests['Low']):
                report.append(f"### {test['section']}: {test['test_name']}")
                report.append(f"- **Requirements**: {', '.join(test['req_ids'])}")
                report.append(f"- **Severity**: {LOW_EMOJI} Low")
                report.append(f"- **Issue**: {test['message']}")
                report.append("")
        
        # Remediation plan
        report.append("## Remediation Plan")
        report.append("")
        
        if failed_tests['Critical']:
            report.append("### Priority 1: Critical Issues (Required for compliance)")
            for test in failed_tests['Critical']:
                report.append(f"- Fix {test['test_name']} ({', '.join(test['req_ids'])})")
            report.append("")
        
        if failed_tests['Medium']:
            report.append("### Priority 2: Medium Issues (Recommended for best practices)")
            for test in failed_tests['Medium']:
                report.append(f"- Fix {test['test_name']} ({', '.join(test['req_ids'])})")
            report.append("")
        
        if failed_tests['Low']:
            report.append("### Priority 3: Low Issues (Optional enhancements)")
            for test in failed_tests['Low']:
                report.append(f"- Consider fixing {test['test_name']} ({', '.join(test['req_ids'])})")
            report.append("")
        
        # Final notes
        report.append("---")
        report.append("")
        report.append("*This report was generated using the weighted scoring system described in the MCP Protocol Validator documentation.*")
        
        return "\n".join(report)
    
    def _generate_json_report(self) -> str:
        """Generate a JSON formatted compliance report.
        
        Returns:
            JSON report as string.
        """
        report_data = {
            'server_info': self.server_info,
            'test_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'report_generated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'compliance': {
                'level': self.compliance_level,
                'weighted_score': self.weighted_score,
                'must': {
                    'total': self.must_results['total'],
                    'passed': self.must_results['passed'],
                    'failed': self.must_results['failed'],
                    'skipped': self.must_results['skipped'],
                    'compliance': (self.must_results['passed'] / self.must_results['total'] * 100) if self.must_results['total'] > 0 else 0
                },
                'should': {
                    'total': self.should_results['total'],
                    'passed': self.should_results['passed'],
                    'failed': self.should_results['failed'],
                    'skipped': self.should_results['skipped'],
                    'compliance': (self.should_results['passed'] / self.should_results['total'] * 100) if self.should_results['total'] > 0 else 0
                },
                'may': {
                    'total': self.may_results['total'],
                    'passed': self.may_results['passed'],
                    'failed': self.may_results['failed'],
                    'skipped': self.may_results['skipped'],
                    'compliance': (self.may_results['passed'] / self.may_results['total'] * 100) if self.may_results['total'] > 0 else 0
                }
            },
            'sections': self.section_results,
            'failed_tests': self._get_failed_tests_by_severity(),
            'all_tests': self.test_results['tests']
        }
        
        return json.dumps(report_data, indent=2)
    
    def print_summary(self) -> None:
        """Print a summary of the compliance report to the console."""
        console = Console()
        
        console.print(f"\n[bold]MCP Compliance Summary[/bold]")
        console.print(f"Weighted Score: [bold]{self.weighted_score:.1f}%[/bold] - {self.compliance_level}")
        
        # Create summary table
        table = Table(title="Requirement Type Breakdown")
        table.add_column("Type", style="bold")
        table.add_column("Total")
        table.add_column("Passed")
        table.add_column("Failed")
        table.add_column("Skipped")
        table.add_column("Compliance")
        
        must_compliance = (self.must_results['passed'] / self.must_results['total'] * 100) if self.must_results['total'] > 0 else 0
        should_compliance = (self.should_results['passed'] / self.should_results['total'] * 100) if self.should_results['total'] > 0 else 0
        may_compliance = (self.may_results['passed'] / self.may_results['total'] * 100) if self.may_results['total'] > 0 else 0
        
        table.add_row(f"{CRITICAL_EMOJI} MUST", str(self.must_results['total']), str(self.must_results['passed']), 
                     str(self.must_results['failed']), str(self.must_results['skipped']), f"{must_compliance:.1f}%")
        table.add_row(f"{MEDIUM_EMOJI} SHOULD", str(self.should_results['total']), str(self.should_results['passed']), 
                     str(self.should_results['failed']), str(self.should_results['skipped']), f"{should_compliance:.1f}%")
        table.add_row(f"{LOW_EMOJI} MAY", str(self.may_results['total']), str(self.may_results['passed']), 
                     str(self.may_results['failed']), str(self.may_results['skipped']), f"{may_compliance:.1f}%")
        
        console.print(table)
        
        # Failed tests summary
        failed_tests = self._get_failed_tests_by_severity()
        
        if failed_tests['Critical'] or failed_tests['Medium'] or failed_tests['Low']:
            console.print(f"\n[bold]Failed Tests Summary:[/bold]")
            
            if failed_tests['Critical']:
                console.print(f"\n{CRITICAL_EMOJI} [bold red]Critical Issues:[/bold red] {len(failed_tests['Critical'])}")
                for test in failed_tests['Critical']:
                    console.print(f"  - {test['test_name']} ({', '.join(test['req_ids'])})")
            
            if failed_tests['Medium']:
                console.print(f"\n{MEDIUM_EMOJI} [bold yellow]Medium Issues:[/bold yellow] {len(failed_tests['Medium'])}")
                for test in failed_tests['Medium']:
                    console.print(f"  - {test['test_name']} ({', '.join(test['req_ids'])})")
            
            if failed_tests['Low']:
                console.print(f"\n{LOW_EMOJI} [bold green]Low Issues:[/bold green] {len(failed_tests['Low'])}")
                for test in failed_tests['Low']:
                    console.print(f"  - {test['test_name']} ({', '.join(test['req_ids'])})")
        else:
            console.print("\n[bold green]All tests passed! ✓[/bold green]")


def generate_report(junit_xml_path: str, 
                   server_info: Dict[str, str], 
                   format: str = 'markdown', 
                   output_path: Optional[str] = None,
                   print_summary: bool = True) -> str:
    """Generate an MCP compliance report.
    
    Args:
        junit_xml_path: Path to JUnit XML report.
        server_info: Dictionary with server information.
        format: Report format ('markdown', 'html', or 'json').
        output_path: Path to save the report.
        print_summary: Whether to print a summary to the console.
        
    Returns:
        Report content.
    """
    generator = MCPReportGenerator(junit_xml_path, server_info)
    report = generator.generate_report(format, output_path)
    
    if print_summary:
        generator.print_summary()
    
    return report 