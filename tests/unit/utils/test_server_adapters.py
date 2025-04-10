#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the server_adapters.py module.
"""

import unittest
from unittest.mock import patch, Mock
import os
from mcp_testing.utils.server_adapters import (
    ServerAdapter,
    GenericServerAdapter,
    FetchServerAdapter,
    GitHubServerAdapter,
    BraveSearchServerAdapter,
    PostgresServerAdapter,
    MinimalServerAdapter,
    create_server_adapter,
    detect_server_type,
    SERVER_TYPES
)


class TestServerAdapters(unittest.TestCase):
    """Test cases for the server adapters module."""

    def test_base_server_adapter_init(self):
        """Test initialization of the base ServerAdapter."""
        adapter = ServerAdapter("python server.py", debug=True)
        self.assertEqual(adapter.server_command, "python server.py")
        self.assertTrue(adapter.debug)
        self.assertEqual(adapter.server_config, {})

    def test_base_server_adapter_get_transport_config(self):
        """Test getting transport config from the base ServerAdapter."""
        adapter = ServerAdapter("python server.py")
        config = adapter.get_transport_config()
        self.assertFalse(config["use_shell"])
        self.assertIsNone(config["command_prefix"])

    def test_base_server_adapter_get_server_config(self):
        """Test getting server config from the base ServerAdapter."""
        adapter = ServerAdapter("python server.py")
        config = adapter.get_server_config()
        self.assertEqual(config, {})

    def test_base_server_adapter_get_environment_vars(self):
        """Test getting environment vars from the base ServerAdapter."""
        adapter = ServerAdapter("python server.py")
        base_env = {"TEST_VAR": "test_value"}
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env, base_env)

    def test_base_server_adapter_should_skip_shutdown(self):
        """Test should_skip_shutdown from the base ServerAdapter."""
        adapter = ServerAdapter("python server.py")
        self.assertFalse(adapter.should_skip_shutdown())

    def test_generic_server_adapter_shell_detection(self):
        """Test shell detection in GenericServerAdapter."""
        # Command without shell operators
        adapter = GenericServerAdapter("python server.py")
        config = adapter.get_transport_config()
        self.assertFalse(config["use_shell"])

        # Command with && operator
        adapter = GenericServerAdapter("cd /tmp && python server.py")
        config = adapter.get_transport_config()
        self.assertTrue(config["use_shell"])

        # Command with ; operator
        adapter = GenericServerAdapter("cd /tmp; python server.py")
        config = adapter.get_transport_config()
        self.assertTrue(config["use_shell"])

        # Command with source
        adapter = GenericServerAdapter("source venv/bin/activate && python server.py")
        config = adapter.get_transport_config()
        self.assertTrue(config["use_shell"])

    def test_fetch_server_adapter(self):
        """Test FetchServerAdapter."""
        adapter = FetchServerAdapter("python fetch_server.py", debug=True)
        
        # Check server config
        server_config = adapter.get_server_config()
        self.assertTrue(server_config["skip_shutdown"])
        self.assertIn("fetch", server_config["required_tools"])
        
        # Check transport config
        transport_config = adapter.get_transport_config()
        self.assertTrue(transport_config["use_shell"])
        
        # Check should_skip_shutdown
        self.assertTrue(adapter.should_skip_shutdown())
        
        # Test with venv in command
        adapter = FetchServerAdapter("source venv/bin/activate && python fetch_server.py")
        transport_config = adapter.get_transport_config()
        self.assertTrue(transport_config["use_shell"])

    def test_github_server_adapter(self):
        """Test GitHubServerAdapter."""
        adapter = GitHubServerAdapter("python github_server.py", debug=True)
        
        # Check server config
        server_config = adapter.get_server_config()
        self.assertTrue(server_config["skip_shutdown"])
        self.assertIn("create_or_update_file", server_config["required_tools"])
        self.assertIn("push_files", server_config["required_tools"])
        self.assertIn("search_repositories", server_config["required_tools"])
        self.assertIn("get_file_contents", server_config["required_tools"])
        
        # Check should_skip_shutdown
        self.assertTrue(adapter.should_skip_shutdown())
        
        # Test environment variables with no tokens
        base_env = {"PATH": "/usr/bin"}
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env, base_env)
        
        # Test environment variables with default token
        base_env = {"PATH": "/usr/bin", "MCP_DEFAULT_GITHUB_TOKEN": "default_token"}
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env["GITHUB_PERSONAL_ACCESS_TOKEN"], "default_token")
        
        # Test with explicit token (should not be overridden)
        base_env = {
            "PATH": "/usr/bin", 
            "MCP_DEFAULT_GITHUB_TOKEN": "default_token",
            "GITHUB_PERSONAL_ACCESS_TOKEN": "explicit_token"
        }
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env["GITHUB_PERSONAL_ACCESS_TOKEN"], "explicit_token")

    def test_brave_search_server_adapter(self):
        """Test BraveSearchServerAdapter."""
        adapter = BraveSearchServerAdapter("python brave_search_server.py", debug=True)
        
        # Check server config
        server_config = adapter.get_server_config()
        self.assertTrue(server_config["skip_shutdown"])
        self.assertIn("brave_web_search", server_config["required_tools"])
        self.assertIn("brave_local_search", server_config["required_tools"])
        
        # Check should_skip_shutdown
        self.assertTrue(adapter.should_skip_shutdown())
        
        # Test environment variables with no keys
        base_env = {"PATH": "/usr/bin"}
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env, base_env)
        
        # Test environment variables with default key
        base_env = {"PATH": "/usr/bin", "MCP_DEFAULT_BRAVE_API_KEY": "default_key"}
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env["BRAVE_API_KEY"], "default_key")
        
        # Test with explicit key (should not be overridden)
        base_env = {
            "PATH": "/usr/bin", 
            "MCP_DEFAULT_BRAVE_API_KEY": "default_key",
            "BRAVE_API_KEY": "explicit_key"
        }
        env = adapter.get_environment_vars(base_env)
        self.assertEqual(env["BRAVE_API_KEY"], "explicit_key")

    def test_postgres_server_adapter(self):
        """Test PostgresServerAdapter."""
        adapter = PostgresServerAdapter("python postgres_server.py", debug=True)
        
        # Check server config
        server_config = adapter.get_server_config()
        self.assertTrue(server_config["skip_shutdown"])
        self.assertIn("query", server_config["required_tools"])
        
        # Check should_skip_shutdown
        self.assertTrue(adapter.should_skip_shutdown())
        
        # Check transport config with python command
        transport_config = adapter.get_transport_config()
        self.assertTrue(transport_config["use_shell"])
        
        # Check with non-python command
        adapter = PostgresServerAdapter("./postgres_server")
        transport_config = adapter.get_transport_config()
        self.assertFalse(transport_config["use_shell"])
        
        # Check with mcp_server in command
        adapter = PostgresServerAdapter("./mcp_server_postgres")
        transport_config = adapter.get_transport_config()
        self.assertTrue(transport_config["use_shell"])

    def test_minimal_server_adapter(self):
        """Test MinimalServerAdapter."""
        adapter = MinimalServerAdapter("python minimal_server.py", debug=True)
        
        # Check server config
        server_config = adapter.get_server_config()
        self.assertIn("echo", server_config["required_tools"])
        self.assertIn("add", server_config["required_tools"])

    @patch('mcp_testing.utils.server_adapters.detect_server_type')
    def test_create_server_adapter_with_auto_detection(self, mock_detect):
        """Test create_server_adapter with auto-detection."""
        mock_detect.return_value = "github"
        
        adapter = create_server_adapter("python server.py", debug=True)
        self.assertIsInstance(adapter, GitHubServerAdapter)
        mock_detect.assert_called_once_with("python server.py")

    def test_create_server_adapter_with_explicit_type(self):
        """Test create_server_adapter with explicit server type."""
        # Test all server types
        adapter = create_server_adapter("cmd", server_type="generic")
        self.assertIsInstance(adapter, GenericServerAdapter)
        
        adapter = create_server_adapter("cmd", server_type="fetch")
        self.assertIsInstance(adapter, FetchServerAdapter)
        
        adapter = create_server_adapter("cmd", server_type="github")
        self.assertIsInstance(adapter, GitHubServerAdapter)
        
        adapter = create_server_adapter("cmd", server_type="brave-search")
        self.assertIsInstance(adapter, BraveSearchServerAdapter)
        
        adapter = create_server_adapter("cmd", server_type="postgres")
        self.assertIsInstance(adapter, PostgresServerAdapter)
        
        adapter = create_server_adapter("cmd", server_type="minimal")
        self.assertIsInstance(adapter, MinimalServerAdapter)

    def test_server_types_constant(self):
        """Test the SERVER_TYPES constant."""
        self.assertIn("generic", SERVER_TYPES)
        self.assertIn("fetch", SERVER_TYPES)
        self.assertIn("github", SERVER_TYPES)
        self.assertIn("brave-search", SERVER_TYPES)
        self.assertIn("postgres", SERVER_TYPES)
        self.assertIn("minimal", SERVER_TYPES)

    def test_detect_server_type(self):
        """Test the detect_server_type function."""
        # Test fetch detection
        self.assertEqual(detect_server_type("python fetch_server.py"), "fetch")
        self.assertEqual(detect_server_type("./fetch_mcp_server"), "fetch")
        
        # Test GitHub detection
        self.assertEqual(detect_server_type("python github_server.py"), "github")
        self.assertEqual(detect_server_type("./github_mcp_server"), "github")
        
        # Test Brave Search detection
        self.assertEqual(detect_server_type("python brave_search_server.py"), "brave-search")
        self.assertEqual(detect_server_type("./brave_mcp_server"), "brave-search")
        
        # Test PostgreSQL detection
        self.assertEqual(detect_server_type("python postgres_server.py"), "postgres")
        self.assertEqual(detect_server_type("./postgres_mcp_server"), "postgres")
        
        # Test Minimal detection
        self.assertEqual(detect_server_type("python minimal_server.py"), "minimal")
        self.assertEqual(detect_server_type("./minimal_mcp_server"), "minimal")
        
        # Test fallback to generic
        self.assertEqual(detect_server_type("python unknown_server.py"), "generic")
        self.assertEqual(detect_server_type("./custom_server"), "generic")


if __name__ == "__main__":
    unittest.main() 