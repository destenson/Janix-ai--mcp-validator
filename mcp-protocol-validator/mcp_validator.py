#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Validator

A command-line tool and test suite for validating MCP server implementations.
"""

import os
import sys
import json
import click
import subprocess
import time
from pathlib import Path
import pytest
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import threading
import signal

# Initialize rich console for better output
console = Console()

# Global variable to hold server process for STDIO transport
SERVER_PROCESS = None

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Command-line interface for the MCP Protocol Validator."""
    pass

@cli.command()
@click.option("--url", required=True, help="URL of the MCP server to test")
@click.option("--server-command", help="Command to start a local MCP server")
@click.option("--report", default="./mcp-compliance-report.html", help="Path to save the test report")
@click.option("--format", default="html", type=click.Choice(["html", "json", "markdown"]), help="Report format")
@click.option("--test-modules", help="Comma-separated list of test modules to run (base,resources,tools,prompts,utilities)")
@click.option("--version", default="2025-03-26", type=click.Choice(["2024-11-05", "2025-03-26"]), help="MCP protocol version to test against")
@click.option("--debug", is_flag=True, help="Enable debug output, especially for STDIO transport")
@click.option("--stdio-only", is_flag=True, help="Run only STDIO-compatible tests (avoid HTTP-specific tests)")
def test(url, server_command, report, format, test_modules, version, debug, stdio_only):
    """Run protocol compliance tests against an MCP server."""
    global SERVER_PROCESS
    
    # Set debug mode
    if debug:
        os.environ["MCP_DEBUG_STDIO"] = "1"
        console.print("[bold yellow]Debug mode enabled[/bold yellow]")
    
    console.print(f"[bold green]MCP Protocol Validator[/bold green]")
    console.print(f"Testing server at: [bold]{url}[/bold]")
    console.print(f"Protocol version: [bold]{version}[/bold]")
    
    # Set protocol version environment variable for tests
    os.environ["MCP_PROTOCOL_VERSION"] = version
    
    server_process = None
    if server_command:
        console.print(f"Starting local server: {server_command}")
        server_process = run_server_command(server_command, debug=debug)
        
        if not server_process:
            console.print("Failed to start server process. Exiting.")
            return 1
        
        # Register cleanup handler for proper server shutdown
        import atexit
        
        def cleanup_server():
            if SERVER_PROCESS is not None:
                console.print("Stopping local server...")
                try:
                    # Try to gracefully terminate the process
                    SERVER_PROCESS.terminate()
                    
                    # Give it a moment to shut down
                    for _ in range(3):
                        if SERVER_PROCESS.poll() is not None:
                            break
                        time.sleep(1)
                        
                    # Force kill if still running
                    if SERVER_PROCESS.poll() is None:
                        if debug:
                            console.print("Force killing server process", file=sys.stderr)
                        if os.name == 'nt':  # Windows
                            SERVER_PROCESS.kill()
                        else:  # Unix/Linux/Mac
                            os.killpg(os.getpgid(SERVER_PROCESS.pid), signal.SIGKILL)
                except Exception as e:
                    if debug:
                        console.print(f"Error during server cleanup: {str(e)}", file=sys.stderr)
        
        atexit.register(cleanup_server)
    
    try:
        # Set up environment variables for tests
        os.environ["MCP_SERVER_URL"] = url
        
        # Set STDIO-only mode if specified
        if stdio_only:
            os.environ["MCP_STDIO_ONLY"] = "1"
            console.print("[bold blue]Running STDIO-compatible tests only[/bold blue]")
        
        # Determine transport type and configure environment
        if server_command:
            # Set environment variable to indicate STDIO transport should be used
            os.environ["MCP_TRANSPORT_TYPE"] = "stdio"
            console.print("[bold blue]Using STDIO transport[/bold blue]")
            
            # Import the test_base module to set up the global server process
            try:
                from mcp_protocol_validator.tests.test_base import set_server_process
            except ImportError:
                try:
                    from tests.test_base import set_server_process
                except ImportError:
                    console.print("[bold red]Error: Could not import test_base module![/bold red]")
                    return 1
            
            set_server_process(SERVER_PROCESS)
        else:
            # Using HTTP transport
            os.environ["MCP_TRANSPORT_TYPE"] = "http"
            console.print("[bold blue]Using HTTP transport[/bold blue]")
        
        # Build pytest args
        pytest_args = ["-v"]
        
        # Add report format
        if format == "html":
            pytest_args.extend(["--html", report, "--self-contained-html"])
        
        # Run only STDIO-compatible tests if specified
        if stdio_only:
            # Create a custom marker expression to include only STDIO-compatible tests
            # This will skip any tests that use HTTP-specific methods
            pytest_args.extend(["-k", "not http_only"])
        
        # Filter test modules if specified
        if test_modules:
            module_list = test_modules.split(",")
            test_paths = []
            if "base" in module_list:
                test_paths.append("tests/test_base_protocol.py")
            if "resources" in module_list:
                test_paths.append("tests/test_resources.py")
            if "tools" in module_list:
                test_paths.append("tests/test_tools.py")
            if "prompts" in module_list:
                test_paths.append("tests/test_prompts.py")
            if "utilities" in module_list:
                test_paths.append("tests/test_utilities.py")
            pytest_args.extend(test_paths)
        else:
            # Run all tests
            pytest_args.append("tests/")
        
        # Run tests
        with Progress() as progress:
            task = progress.add_task("[green]Running tests...", total=100)
            progress.update(task, advance=50)
            
            # Execute pytest
            exit_code = pytest.main(pytest_args)
            
            progress.update(task, completed=100)
        
        # Generate summary
        if os.path.exists(report):
            console.print(f"\n[green]Test report saved to:[/green] {report}")
        
        if exit_code == 0:
            console.print("[bold green]✅ All tests passed![/bold green]")
        else:
            console.print(f"[bold red]❌ Some tests failed (exit code: {exit_code})[/bold red]")
        
    finally:
        # Clean up server process if we started one
        if server_process:
            console.print("Stopping local server...")
            server_process.terminate()
        # Clear global reference
        SERVER_PROCESS = None

@cli.command()
@click.option("--version", default="2025-03-26", type=click.Choice(["2024-11-05", "2025-03-26"]), help="MCP protocol version to view")
def schema(version):
    """Print the MCP JSON schema for the specified version."""
    schema_file = f"mcp_schema_{version}.json"
    schema_path = Path(__file__).parent / "schema" / schema_file
    if schema_path.exists():
        with open(schema_path) as f:
            schema = json.load(f)
        console.print_json(json.dumps(schema, indent=2))
    else:
        console.print(f"[bold red]Schema file for version {version} not found![/bold red]")
        return 1

def run_server_command(server_command, debug=False):
    """
    Run a server command and set up global server process for testing.
    
    Args:
        server_command: The command to start the server
        debug: Whether to enable debug mode
    
    Returns:
        The server process
    """
    from tests.test_base import SERVER_PROCESS, start_debug_output_thread
    import subprocess
    import time
    import os
    import signal
    
    # Store the server command in environment for potential restarts
    os.environ["MCP_SERVER_COMMAND"] = server_command
    
    # Kill any existing process
    if SERVER_PROCESS is not None:
        try:
            # Try graceful termination first
            SERVER_PROCESS.terminate()
            
            # Give it a moment to shut down
            for _ in range(3):
                if SERVER_PROCESS.poll() is not None:
                    break
                time.sleep(1)
                
            # Force kill if still running
            if SERVER_PROCESS.poll() is None:
                if debug:
                    print(f"Force killing previous server process", file=sys.stderr)
                if os.name == 'nt':  # Windows
                    SERVER_PROCESS.kill()
                else:  # Unix/Linux/Mac
                    os.killpg(os.getpgid(SERVER_PROCESS.pid), signal.SIGKILL)
        except Exception as e:
            if debug:
                print(f"Error stopping previous server process: {str(e)}", file=sys.stderr)
    
    if debug:
        print(f"Starting server with command: {server_command}", file=sys.stderr)
    
    # Start the server process
    try:
        # For Docker commands, ensure we're using the right parameters
        if 'docker' in server_command and ' -i ' not in server_command and not server_command.startswith("docker run -i"):
            if debug:
                print("Adding -i flag to Docker command to support STDIO", file=sys.stderr)
            # Insert -i flag if not present for Docker commands
            parts = server_command.split("docker run ")
            if len(parts) > 1:
                server_command = f"{parts[0]}docker run -i {parts[1]}"
    
        # Start the server as a new process group to allow killing the entire group
        kwargs = {
            'shell': True,
            'stdout': subprocess.PIPE,
            'stdin': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'bufsize': 1,  # Line buffered
        }
        
        # On non-Windows platforms, create a new process group
        if os.name != 'nt':  # Unix/Linux/Mac
            kwargs['preexec_fn'] = os.setsid
            
        SERVER_PROCESS = subprocess.Popen(server_command, **kwargs)
        
        # Give the server a moment to initialize
        time.sleep(2)
        
        # Check if the process started successfully
        if SERVER_PROCESS.poll() is not None:
            print(f"Server process failed to start (exit code: {SERVER_PROCESS.returncode})", file=sys.stderr)
            # Try to capture stderr output to see what went wrong
            stderr_output = SERVER_PROCESS.stderr.read().decode('utf-8')
            print(f"Server stderr output: {stderr_output}", file=sys.stderr)
            return None
            
        # Start debug output thread if in debug mode
        if debug:
            start_debug_output_thread(SERVER_PROCESS)
            
        return SERVER_PROCESS
        
    except Exception as e:
        print(f"Failed to start server: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None

def main():
    """Main entry point for the MCP Protocol Validator."""
    # Import SERVER_PROCESS at the beginning to avoid linting issues
    from tests.test_base import SERVER_PROCESS as _SERVER_PROCESS
    
    # Run the CLI
    return cli()

if __name__ == "__main__":
    cli() 