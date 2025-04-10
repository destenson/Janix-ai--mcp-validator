"""
Unit tests for the server_compatibility module.
"""

import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock, call
from pathlib import Path

from mcp_testing.utils.server_compatibility import (
    is_shutdown_skipped,
    load_server_configs,
    prepare_environment_for_server,
    get_server_specific_test_config,
    get_recommended_protocol_version,
    SERVER_CONFIG_DIR
)


class TestServerCompatibility:
    """Tests for the server_compatibility module."""

    def test_is_shutdown_skipped_true(self):
        """Test is_shutdown_skipped returns True when environment variable is set."""
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "true"}):
            assert is_shutdown_skipped() is True

        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "1"}):
            assert is_shutdown_skipped() is True

        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "yes"}):
            assert is_shutdown_skipped() is True

    def test_is_shutdown_skipped_false(self):
        """Test is_shutdown_skipped returns False when environment variable is not set or invalid."""
        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": "false"}):
            assert is_shutdown_skipped() is False

        with patch.dict(os.environ, {"MCP_SKIP_SHUTDOWN": ""}):
            assert is_shutdown_skipped() is False

        with patch.dict(os.environ, {}, clear=True):
            assert is_shutdown_skipped() is False

    def test_load_server_configs_empty(self):
        """Test load_server_configs when directory is empty."""
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_glob.return_value = []
            
            configs = load_server_configs()
            
            assert configs == {}
            mock_mkdir.assert_called_once_with(exist_ok=True, parents=True)

    def test_load_server_configs_valid(self):
        """Test load_server_configs with valid configuration files."""
        mock_files = [
            Path("test1.json"),
            Path("test2.json")
        ]
        
        mock_data = [
            {
                "identifiers": ["server1", "server-1"],
                "name": "Server 1",
                "environment": {}
            },
            {
                "identifiers": ["server2"],
                "name": "Server 2",
                "environment": {}
            }
        ]
        
        mock_file_content = [json.dumps(data) for data in mock_data]
        
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('builtins.open', side_effect=[
                 mock_open(read_data=mock_file_content[0]).return_value,
                 mock_open(read_data=mock_file_content[1]).return_value
             ]):
            
            mock_glob.return_value = mock_files
            
            configs = load_server_configs()
            
            assert "server1" in configs
            assert "server-1" in configs
            assert "server2" in configs
            assert configs["server1"]["name"] == "Server 1"
            assert configs["server2"]["name"] == "Server 2"
            mock_mkdir.assert_called_once_with(exist_ok=True, parents=True)

    def test_load_server_configs_invalid(self):
        """Test load_server_configs with invalid configuration files."""
        mock_files = [
            Path("valid.json"),
            Path("invalid.json"),
            Path("missing_identifiers.json")
        ]
        
        mock_data = [
            {
                "identifiers": ["valid-server"],
                "name": "Valid Server",
                "environment": {}
            },
            "not_a_json_object",  # Invalid JSON structure
            {
                "name": "Missing Identifiers",
                "environment": {}
            }  # Missing identifiers
        ]
        
        mock_file_content = [
            json.dumps(mock_data[0]),
            mock_data[1],  # Not JSON serialized
            json.dumps(mock_data[2])
        ]
        
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('builtins.open', side_effect=[
                 mock_open(read_data=mock_file_content[0]).return_value,
                 mock_open(read_data=mock_file_content[1]).return_value,
                 mock_open(read_data=mock_file_content[2]).return_value
             ]), \
             patch('builtins.print') as mock_print:
            
            mock_glob.return_value = mock_files
            
            configs = load_server_configs()
            
            assert "valid-server" in configs
            assert len(configs) == 1  # Only one valid config was loaded
            assert mock_print.call_count >= 2  # Warning messages were printed

    def test_prepare_environment_for_server_no_match(self):
        """Test prepare_environment_for_server when no matching server config is found."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            
            mock_load_configs.return_value = {}
            
            env_vars = prepare_environment_for_server("unknown-server")
            
            assert env_vars == os.environ.copy()

    def test_prepare_environment_for_server_match(self):
        """Test prepare_environment_for_server when a matching server config is found."""
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "environment": {
                    "SERVER_ENV": "needed for test server",
                    "MCP_SKIP_SHUTDOWN": "true"
                }
            }
        }
        
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch.dict(os.environ, {"EXISTING_VAR": "existing"}), \
             patch('builtins.print') as mock_print:
            
            mock_load_configs.return_value = server_configs
            
            env_vars = prepare_environment_for_server("test-server-command")
            
            assert "EXISTING_VAR" in env_vars
            assert env_vars["EXISTING_VAR"] == "existing"
            assert "MCP_SKIP_SHUTDOWN" in env_vars
            assert env_vars["MCP_SKIP_SHUTDOWN"] == "true"
            assert mock_print.call_count >= 1  # Info messages were printed

    def test_prepare_environment_for_server_with_defaults(self):
        """Test prepare_environment_for_server using default environment variables."""
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "environment": {
                    "SERVER_ENV": "needed for test server",
                    "WITH_DEFAULT": "has default value"
                }
            }
        }
        
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch.dict(os.environ, {
                 "EXISTING_VAR": "existing",
                 "MCP_DEFAULT_WITH_DEFAULT": "default_value"
             }), \
             patch('builtins.print') as mock_print:
            
            mock_load_configs.return_value = server_configs
            
            env_vars = prepare_environment_for_server("test-server-command")
            
            assert "WITH_DEFAULT" in env_vars
            assert env_vars["WITH_DEFAULT"] == "default_value"
            assert mock_print.call_count >= 1  # Info messages were printed

    def test_prepare_environment_for_server_with_missing_vars(self):
        """Test prepare_environment_for_server with missing environment variables."""
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "environment": {
                    "SERVER_ENV": "needed for test server",
                    "REQUIRED_VAR": "This is required and has no default",
                    "ANOTHER_VAR": "Another required variable",
                    "MCP_SKIP_SHUTDOWN": "description for skip shutdown"
                }
            }
        }
        
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch.dict(os.environ, {"EXISTING_VAR": "existing"}), \
             patch('builtins.print') as mock_print:
            
            mock_load_configs.return_value = server_configs
            
            env_vars = prepare_environment_for_server("test-server-command")
            
            # Check that warnings were printed for missing variables
            assert mock_print.call_count >= 2
            
            # Verify the method warned about missing required vars
            warning_calls = [
                call for call in mock_print.call_args_list
                if "Warning:" in str(call) and "requires" in str(call)
            ]
            assert len(warning_calls) >= 2
            
            # Verify MCP_SKIP_SHUTDOWN was set automatically
            assert "MCP_SKIP_SHUTDOWN" in env_vars
            assert env_vars["MCP_SKIP_SHUTDOWN"] == "true"
            
            # Other variables should not be set automatically
            assert "SERVER_ENV" not in env_vars
            assert "REQUIRED_VAR" not in env_vars
            assert "ANOTHER_VAR" not in env_vars

    def test_prepare_environment_brave_search_fallback(self):
        """Test prepare_environment_for_server fallback for Brave Search."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump, \
             patch('builtins.print') as mock_print:
            
            mock_load_configs.return_value = {}
            
            env_vars = prepare_environment_for_server("server-brave-search")
            
            assert "MCP_SKIP_SHUTDOWN" in env_vars
            assert env_vars["MCP_SKIP_SHUTDOWN"] == "true"
            mock_makedirs.assert_called_once_with(SERVER_CONFIG_DIR, exist_ok=True)
            mock_json_dump.assert_called_once()  # Default config was saved

    def test_prepare_environment_brave_search_fallback_with_exception(self):
        """Test prepare_environment_for_server fallback for Brave Search when saving config fails."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open') as mock_file, \
             patch('builtins.print') as mock_print:
            
            mock_load_configs.return_value = {}
            mock_makedirs.side_effect = Exception("Permission denied")
            
            env_vars = prepare_environment_for_server("server-brave-search")
            
            # Should still set the environment variable even if saving fails
            assert "MCP_SKIP_SHUTDOWN" in env_vars
            assert env_vars["MCP_SKIP_SHUTDOWN"] == "true"
            
            # Verify warning was printed
            warning_calls = [
                call for call in mock_print.call_args_list
                if "Warning: Couldn't save default Brave Search config" in str(call)
            ]
            assert len(warning_calls) >= 1

    def test_get_server_specific_test_config_match(self):
        """Test get_server_specific_test_config when a matching server config is found."""
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "skip_tests": ["test_shutdown"],
                "required_tools": ["test_tool"]
            }
        }
        
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = server_configs
            
            config = get_server_specific_test_config("test-server-command")
            
            assert "skip_tests" in config
            assert "required_tools" in config
            assert config["skip_tests"] == ["test_shutdown"]
            assert config["required_tools"] == ["test_tool"]

    def test_get_server_specific_test_config_no_match(self):
        """Test get_server_specific_test_config when no matching server config is found."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = {}
            
            config = get_server_specific_test_config("unknown-server")
            
            assert config == {}

    def test_get_server_specific_test_config_brave_search_fallback(self):
        """Test get_server_specific_test_config fallback for Brave Search."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = {}
            
            config = get_server_specific_test_config("server-brave-search")
            
            assert "skip_tests" in config
            assert "required_tools" in config
            assert "test_shutdown" in config["skip_tests"]
            assert "brave_web_search" in config["required_tools"]

    def test_get_recommended_protocol_version_match(self):
        """Test get_recommended_protocol_version when a matching server config is found."""
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "recommended_protocol": "2024-12-01"
            }
        }
        
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = server_configs
            
            version = get_recommended_protocol_version("test-server-command")
            
            assert version == "2024-12-01"

    def test_get_recommended_protocol_version_no_match(self):
        """Test get_recommended_protocol_version when no matching server config is found."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = {}
            
            version = get_recommended_protocol_version("unknown-server")
            
            assert version is None

    def test_get_recommended_protocol_version_brave_search_fallback(self):
        """Test get_recommended_protocol_version fallback for Brave Search."""
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs:
            mock_load_configs.return_value = {}
            
            version = get_recommended_protocol_version("server-brave-search")
            
            assert version == "2024-11-05"

    def test_prepare_environment_for_server_with_skip_shutdown(self):
        """Test prepare_environment_for_server auto-setting of MCP_SKIP_SHUTDOWN."""
        # Directly testing the scenario where MCP_SKIP_SHUTDOWN needs to be set
        server_configs = {
            "test-server": {
                "name": "Test Server",
                "identifiers": ["test-server"],
                "environment": {
                    "MCP_SKIP_SHUTDOWN": "This is a description for MCP_SKIP_SHUTDOWN"
                }
            }
        }
        
        # Clear all environment variables to ensure we're testing the right path
        with patch('mcp_testing.utils.server_compatibility.load_server_configs') as mock_load_configs, \
             patch.dict(os.environ, {}, clear=True):
            
            mock_load_configs.return_value = server_configs
            
            # Call the function and verify the environment variable was set
            env_vars = prepare_environment_for_server("test-server-command")
            assert "MCP_SKIP_SHUTDOWN" in env_vars
            assert env_vars["MCP_SKIP_SHUTDOWN"] == "true" 