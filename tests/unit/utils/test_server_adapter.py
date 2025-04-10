"""
Unit tests for the server_adapter module.
"""

import asyncio
import pytest
import shlex
from unittest.mock import patch, MagicMock, AsyncMock, call
import os
import sys

from mcp_testing.utils.server_adapter import (
    ServerAdapter,
    StdioServerAdapter,
    HTTPServerAdapter,
    create_server_adapter
)

class TestServerAdapter:
    """Tests for the ServerAdapter base class and its implementations."""
    
    def test_server_adapter_is_abstract(self):
        """Test that ServerAdapter is an abstract base class."""
        with pytest.raises(TypeError):
            ServerAdapter()  # Should raise TypeError due to abstract methods

    @pytest.mark.asyncio
    async def test_stdio_server_adapter_init(self):
        """Test initialization of StdioServerAdapter."""
        # Mock dependencies
        protocol_factory = MagicMock()
        
        # Create adapter
        adapter = StdioServerAdapter(
            server_command="python -m server",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=True,
            use_shell=False
        )
        
        # Verify initialization
        assert adapter.server_command == "python -m server"
        assert adapter.protocol_factory == protocol_factory
        assert adapter.protocol_version == "2023-11-01"
        assert adapter.debug is True
        assert adapter.use_shell is False
        assert adapter.process is None
        assert adapter.transport is None
        assert adapter.protocol is None

    @pytest.mark.asyncio
    async def test_stdio_server_adapter_start(self):
        """Test starting a StdioServerAdapter."""
        # Mock dependencies
        protocol_factory = MagicMock()
        protocol = MagicMock()
        protocol_factory.return_value = protocol
        
        # Create adapter
        adapter = StdioServerAdapter(
            server_command="echo hello",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=True
        )
        
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        
        # Patch asyncio.create_subprocess_exec
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_create_subprocess, \
             patch('mcp_testing.utils.server_adapter.StdioTransportAdapter') as mock_transport_class:
            
            # Mock transport
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport
            
            # Call start method
            await adapter.start()
            
            # Verify subprocess creation
            mock_create_subprocess.assert_called_once()
            # Check that the command was split correctly
            assert mock_create_subprocess.call_args[0] == tuple(shlex.split("echo hello"))
            # Check stdin/stdout/stderr
            assert mock_create_subprocess.call_args[1]['stdin'] == asyncio.subprocess.PIPE
            assert mock_create_subprocess.call_args[1]['stdout'] == asyncio.subprocess.PIPE
            assert mock_create_subprocess.call_args[1]['stderr'] == asyncio.subprocess.PIPE
            
            # Verify transport and protocol creation
            mock_transport_class.assert_called_once_with(
                mock_process.stdin, mock_process.stdout, True, use_shell=False
            )
            protocol_factory.assert_called_once_with("2023-11-01", mock_transport, True)
            
            # Verify attributes set
            assert adapter.process == mock_process
            assert adapter.transport == mock_transport
            assert adapter.protocol == protocol

    @pytest.mark.asyncio
    async def test_stdio_server_adapter_stop_normal(self):
        """Test stopping a StdioServerAdapter with normal exit."""
        # Create adapter
        protocol_factory = MagicMock()
        adapter = StdioServerAdapter(
            server_command="echo hello",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=True
        )
        
        # Setup mocks
        adapter.process = AsyncMock()
        adapter.process.stderr = AsyncMock()
        adapter.process.stderr.read = AsyncMock(return_value=b"Some error output")
        adapter.process.wait = AsyncMock()
        adapter.protocol = AsyncMock()
        adapter.transport = MagicMock()
        
        # Store references to check later
        process_ref = adapter.process
        protocol_ref = adapter.protocol
        
        # Call stop method
        await adapter.stop()
        
        # Verify shutdown sequence
        protocol_ref.shutdown.assert_called_once()
        process_ref.terminate.assert_called_once()
        process_ref.wait.assert_called_once()
        process_ref.stderr.read.assert_called_once()
        
        # Verify adapter state
        assert adapter.process is None
        assert adapter.transport is None
        assert adapter.protocol is None

    @pytest.mark.asyncio
    async def test_stdio_server_adapter_stop_timeout(self):
        """Test stopping a StdioServerAdapter with timeout."""
        # Create adapter
        protocol_factory = MagicMock()
        adapter = StdioServerAdapter(
            server_command="echo hello",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=True
        )
        
        # Setup mocks
        adapter.process = AsyncMock()
        adapter.process.stderr = AsyncMock()
        adapter.process.stderr.read = AsyncMock(return_value=b"")
        
        # Make wait() raise TimeoutError
        adapter.process.wait = AsyncMock()
        
        adapter.protocol = AsyncMock()
        adapter.transport = MagicMock()
        
        # Store reference to check later
        process_ref = adapter.process
        
        # Call stop method
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()
            
            await adapter.stop()
            
            # Verify timeout handling
            process_ref.kill.assert_called_once()
            assert process_ref.wait.call_count >= 1
        
        # Verify adapter state
        assert adapter.process is None
        assert adapter.transport is None
        assert adapter.protocol is None

    @pytest.mark.asyncio
    async def test_stdio_server_adapter_stop_protocol_exception(self):
        """Test stopping a StdioServerAdapter when protocol.shutdown raises an exception."""
        # Create adapter
        protocol_factory = MagicMock()
        adapter = StdioServerAdapter(
            server_command="echo hello",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=True
        )
        
        # Setup mocks
        adapter.process = AsyncMock()
        adapter.process.stderr = AsyncMock()
        adapter.process.stderr.read = AsyncMock(return_value=b"")
        adapter.process.wait = AsyncMock()
        
        # Make protocol.shutdown raise an exception
        adapter.protocol = AsyncMock()
        adapter.protocol.shutdown.side_effect = Exception("Shutdown failed")
        
        adapter.transport = MagicMock()
        
        # Store references to check later
        process_ref = adapter.process
        protocol_ref = adapter.protocol
        
        # Call stop method
        await adapter.stop()
        
        # Verify exception handling
        protocol_ref.shutdown.assert_called_once()
        process_ref.terminate.assert_called_once()
        
        # Verify cleanup still occurred
        assert adapter.process is None
        assert adapter.transport is None
        assert adapter.protocol is None

    def test_stdio_server_adapter_get_transport(self):
        """Test get_transport method of StdioServerAdapter."""
        # Create adapter
        protocol_factory = MagicMock()
        adapter = StdioServerAdapter(
            server_command="echo hello",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=False
        )
        
        # Set mock transport
        mock_transport = MagicMock()
        adapter.transport = mock_transport
        
        # Call get_transport
        transport = adapter.get_transport()
        
        # Verify result
        assert transport == mock_transport

    def test_http_server_adapter_not_implemented(self):
        """Test that HTTPServerAdapter raises NotImplementedError."""
        protocol_factory = MagicMock()
        
        with pytest.raises(NotImplementedError):
            HTTPServerAdapter(
                server_url="http://localhost:8000",
                protocol_factory=protocol_factory,
                protocol_version="2023-11-01",
                debug=False
            )

    def test_create_server_adapter_stdio_default(self):
        """Test create_server_adapter with default stdio type."""
        protocol_factory = MagicMock()
        
        adapter = create_server_adapter(
            server_command="python server.py",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            debug=False
        )
        
        assert isinstance(adapter, StdioServerAdapter)
        assert adapter.server_command == "python server.py"
        assert adapter.protocol_factory == protocol_factory
        assert adapter.protocol_version == "2023-11-01"
        assert adapter.debug is False
        assert adapter.use_shell is False

    def test_create_server_adapter_stdio_explicit(self):
        """Test create_server_adapter with explicit stdio type."""
        protocol_factory = MagicMock()
        
        adapter = create_server_adapter(
            server_command="python server.py",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01",
            server_type="stdio",
            debug=True
        )
        
        assert isinstance(adapter, StdioServerAdapter)
        assert adapter.debug is True

    def test_create_server_adapter_http(self):
        """Test create_server_adapter with HTTP type."""
        protocol_factory = MagicMock()
        
        with pytest.raises(NotImplementedError):
            create_server_adapter(
                server_command="http://localhost:8000",
                protocol_factory=protocol_factory,
                protocol_version="2023-11-01",
                server_type="http",
                debug=False
            )

    def test_create_server_adapter_invalid_type(self):
        """Test create_server_adapter with invalid server type."""
        protocol_factory = MagicMock()
        
        with pytest.raises(ValueError) as excinfo:
            create_server_adapter(
                server_command="python server.py",
                protocol_factory=protocol_factory,
                protocol_version="2023-11-01",
                server_type="invalid",
                debug=False
            )
        
        assert "Unsupported server type: invalid" in str(excinfo.value)

    def test_create_server_adapter_auto_shell_detection(self):
        """Test that create_server_adapter automatically sets use_shell=True when needed."""
        protocol_factory = MagicMock()
        
        # Test with && in command
        adapter = create_server_adapter(
            server_command="cd /tmp && python server.py",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True
        
        # Test with ; in command
        adapter = create_server_adapter(
            server_command="echo hello; python server.py",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True
        
        # Test with > in command
        adapter = create_server_adapter(
            server_command="python server.py > log.txt",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True
        
        # Test with Python module
        adapter = create_server_adapter(
            server_command="python -m server",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True
        
        # Test with fetch in command
        adapter = create_server_adapter(
            server_command="fetch_server start",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True
        
        # Test with arxiv in command
        adapter = create_server_adapter(
            server_command="arxiv_search_server",
            protocol_factory=protocol_factory,
            protocol_version="2023-11-01"
        )
        assert adapter.use_shell is True 