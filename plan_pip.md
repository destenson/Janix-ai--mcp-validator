# Testing Pip-Installed MCP Servers

This document outlines the necessary changes to make the MCP testing framework compatible with servers installed via pip, such as `mcp-server-fetch`.

## Root Cause Analysis

The primary issue preventing the validator from working with pip-installed servers is **environment isolation**. When a server is installed with pip, it's installed in a specific Python environment (system, user, or virtual environment). The testing framework may be running in a different environment than where the server was installed, causing the following cascade of issues:

1. **Path Resolution Failure**: The `python -m mcp_server_fetch` command can't find the module because it's not in the Python path of the environment where the tests are running.

2. **Dependency Availability**: Dependencies like `sseclient-py` might be installed in the environment where the server is installed, but not available in the test execution environment.

3. **Transport Startup Failures**: The error "Failed to start transport" occurs because the process fails to start, either because the module can't be found or its dependencies can't be loaded.

## CONFIRMED SOLUTION

We have confirmed that the simplest solution is to install the pip package in the same environment as the testing framework:

```bash
# Ensure you're in the correct virtual environment
source .venv/bin/activate  # Or activate the appropriate environment

# Install the server package and required dependencies
pip install mcp-server-fetch sseclient-py==1.7.2

# Run the tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --debug
```

This approach works because:
1. The server module is now available in the same Python path
2. All dependencies are resolved in the same environment
3. The Python interpreter running the tests is the same one that has access to the module

## Long-Term Improvements

While the above solution works for simple cases, we still need longer-term improvements to the testing framework to make it more robust when dealing with pip-installed servers across different environments.

### 1. Improve Environment Isolation Handling

The most critical change is to ensure the test framework either uses the same environment where the server is installed, or has the necessary path and dependency information to find and run the server:

```python
def ensure_server_environment(server_command):
    """Ensure the environment is properly set up for the server."""
    # Check if this is a module-style command
    if " -m " in server_command:
        module_name = parse_module_name(server_command)
        
        # Try to locate the module in available environments
        module_path = find_module_in_environments(module_name)
        
        if not module_path:
            # Module not found in any environment, need to install it
            print(f"Module {module_name} not found in any available environment.")
            print(f"Installing {module_name}...")
            try:
                # Try to install the module in the current environment
                subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
                return True
            except subprocess.CalledProcessError:
                print(f"Failed to install {module_name}")
                return False
        else:
            # Found the module, ensure we're using the correct environment
            env_path = os.path.dirname(os.path.dirname(module_path))
            if os.path.exists(os.path.join(env_path, "bin", "activate")):
                # This is a virtual environment, modify our PATH to use it
                bin_dir = os.path.join(env_path, "bin")
                os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"
                os.environ["PYTHONPATH"] = f"{env_path}:{os.environ.get('PYTHONPATH', '')}"
                return True
    
    return True  # Not a module command or already in the right environment
```

### 2. Improve Transport Adapter

#### StdioTransportAdapter Enhancements

```python
def start(self) -> bool:
    """
    Start the server process.
    
    Returns:
        True if started successfully, False otherwise
    """
    if self.is_started:
        return True
        
    try:
        if self.debug:
            print(f"Starting server process: {self.server_command}")
            print(f"Environment variables: {self.env_vars}")
            print(f"Current PATH: {os.environ.get('PATH')}")
            print(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH')}")
        
        # Ensure we're in the right environment for this server
        if not ensure_server_environment(self.server_command):
            print("Failed to set up the correct environment for the server.")
            return False
        
        # Handle module-style commands (python -m something)
        command_parts = self.server_command.split()
        
        # Launch the server process
        self.process = subprocess.Popen(
            command_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env=self.env_vars
        )
        
        # Give the server a moment to start
        time.sleep(2.0)  # Increase from 0.5 to 2.0 seconds for pip-installed servers
        
        # Check if the process is still running
        if self.process.poll() is not None:
            if self.debug:
                print(f"Server process failed to start. Exit code: {self.process.returncode}")
                stderr = self.process.stderr.read()
                print(f"Server error output: {stderr}")
            return False
            
        self.is_started = True
        return True
        
    except Exception as e:
        if self.debug:
            print(f"Failed to start server process: {str(e)}")
            import traceback
            print(traceback.format_exc())
        return False
```

### 3. Module Detection and Path Resolution

Add functionality to detect modules and find their paths across environments:

```python
def find_module_in_environments(module_name):
    """Find a module in available Python environments."""
    # Try to import the module in the current environment
    try:
        module_spec = importlib.util.find_spec(module_name)
        if module_spec and module_spec.origin:
            return module_spec.origin
    except (ImportError, AttributeError):
        pass
    
    # Check common virtual environment locations
    venv_paths = [
        ".venv",
        "venv",
        "env",
        os.path.expanduser("~/.virtualenvs")
    ]
    
    for venv_path in venv_paths:
        if not os.path.exists(venv_path):
            continue
            
        # Check if this is a directory of virtual environments
        if os.path.isdir(venv_path) and not os.path.exists(os.path.join(venv_path, "bin")):
            # This might be a directory containing multiple virtual environments
            for subdir in os.listdir(venv_path):
                full_path = os.path.join(venv_path, subdir)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "bin", "python")):
                    # This looks like a virtual environment, check if it has our module
                    result = subprocess.run(
                        [os.path.join(full_path, "bin", "python"), "-c", f"import {module_name}; print({module_name}.__file__)"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
        else:
            # This might be a virtual environment itself
            if os.path.exists(os.path.join(venv_path, "bin", "python")):
                result = subprocess.run(
                    [os.path.join(venv_path, "bin", "python"), "-c", f"import {module_name}; print({module_name}.__file__)"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
    
    return None
```

### 4. Dependency Verification

Add a step to verify that all required dependencies are installed:

```python
def verify_dependencies(dependencies, environment=None):
    """Verify that all required dependencies are installed."""
    python_exe = sys.executable
    if environment and os.path.exists(os.path.join(environment, "bin", "python")):
        python_exe = os.path.join(environment, "bin", "python")
    
    missing_deps = []
    for dep in dependencies:
        # Extract package name from version specifier
        pkg_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
        
        # Check if the package is installed
        result = subprocess.run(
            [python_exe, "-c", f"import {pkg_name}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"Missing dependencies: {', '.join(missing_deps)}")
        print("Installing missing dependencies...")
        for dep in missing_deps:
            try:
                subprocess.check_call([python_exe, "-m", "pip", "install", dep])
            except subprocess.CalledProcessError:
                print(f"Failed to install {dep}")
                return False
    
    return True
```

## Implementation Plan

1. **Phase 1**: Document the current confirmed solution
   - Add clear instructions in the README.md
   - Create a troubleshooting section for common issues

2. **Phase 2**: Implement environment isolation detection and resolution
   - Add module detection across environments
   - Ensure the correct Python interpreter is used
   - Modify PATH and PYTHONPATH as needed

3. **Phase 3**: Enhance subprocess management
   - Improve error reporting from server startup
   - Increase timeouts for pip-installed servers
   - Add detailed logging of environment variables and paths

4. **Phase 4**: Add dependency verification
   - Check for required dependencies before starting tests
   - Install missing dependencies automatically when possible
   - Provide clear error messages when dependencies can't be resolved

5. **Phase 5**: Create specific configurations for common pip-installed servers
   - Predefined configurations for servers like mcp-server-fetch
   - Default dependency lists for known servers
   - Recommended protocol versions and test configurations

6. **Phase 6**: Update documentation and examples
   - Clear instructions for testing pip-installed servers
   - Troubleshooting guide for common issues
   - Examples for different server types and environments

## Troubleshooting Guide for Pip-Installed Servers

### Common Issues and Solutions

1. **"Failed to start transport" error**
   - **Solution**: Install the server module in the same environment as the testing framework
   - **Command**: `pip install mcp-server-fetch sseclient-py==1.7.2`

2. **Module not found errors**
   - **Solution**: Verify the module is installed in the correct environment
   - **Check**: Run `python -c "import mcp_server_fetch"` to verify installation

3. **Dependency conflicts**
   - **Solution**: Create a dedicated virtual environment for testing
   - **Commands**:
     ```bash
     python -m venv test_venv
     source test_venv/bin/activate
     pip install -r requirements.txt mcp-server-fetch
     ```

4. **Path resolution issues**
   - **Solution**: Use the full path to the Python interpreter that has the module installed
   - **Example**: `/path/to/venv/bin/python -m mcp_server_fetch`

5. **Timeout during startup**
   - **Solution**: Increase the startup timeout in the test configuration
   - **Parameter**: Add `--timeout 10` to the command line arguments

## Example Usage

```bash
# Install a pip package in the current environment
pip install mcp-server-fetch

# Run a simple basic interaction test
python -m mcp_testing.scripts.basic_interaction --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05

# Run compliance tests with limited scope
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --test-mode tools --debug

# Run all compliance tests
python -m mcp_testing.scripts.compliance_report --server-command "python -m mcp_server_fetch" --protocol-version 2024-11-05 --debug
```

## Next Steps

1. Update the main README.md with a section on testing pip-installed servers
2. Implement the environment detection and resolution functionality
3. Create server configuration files for common pip-installed servers
4. Add automated tests for the environmental isolation handling 