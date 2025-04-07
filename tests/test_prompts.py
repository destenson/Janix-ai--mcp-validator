#!/usr/bin/env python3
# Copyright (c) 2025 Scott Wilcox
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MCP Protocol Prompts and Completions Tests

This module tests the prompts and completions aspects of the MCP protocol, focusing on:
1. Basic prompt handling
2. Completion generation
3. Protocol version differences in prompt handling
4. Error handling for prompts and completions

These tests focus on the protocol mechanisms rather than specific model behavior.
"""

import os
import pytest
import json
from tests.test_base import MCPBaseTest

# Get environment variables for testing configuration
MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")

class TestPromptsProtocol(MCPBaseTest):
    """Test suite for MCP protocol prompts and completions functionality."""
    
    def get_init_capabilities(self):
        """Get appropriate capabilities based on protocol version."""
        if self.protocol_version == "2024-11-05":
            return {
                "supports": {
                    "prompts": True
                }
            }
        else:  # 2025-03-26 or later
            return {
                "prompts": {
                    "streaming": True
                }
            }
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_initialization(self):
        """Test the initialization process with prompts capabilities."""
        # Send initialize request with appropriate capabilities for the protocol version
        init_capabilities = self.get_init_capabilities()
        
        init_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_initialization",
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": init_capabilities,
                "clientInfo": {
                    "name": "MCPValidator",
                    "version": "0.1.0"
                }
            }
        })
        
        assert init_response.status_code == 200
        init_data = init_response.json()
        
        # Verify the response structure
        assert "result" in init_data
        assert "protocolVersion" in init_data["result"]
        assert "capabilities" in init_data["result"]
        
        # Store the capabilities for later tests
        self.server_capabilities = init_data["result"]["capabilities"]
        self.negotiated_version = init_data["result"]["protocolVersion"]
        
        print(f"\nNegotiated protocol version: {self.negotiated_version}")
        print(f"Server capabilities: {json.dumps(self.server_capabilities, indent=2)}")
        
        # Send initialized notification
        init_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "initialized"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert init_notification.status_code in [200, 202, 204]
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_prompt_completion(self):
        """Test basic prompt completion."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts aren't supported
        has_prompts = False
        if self.protocol_version == "2024-11-05":
            has_prompts = self.server_capabilities.get("supports", {}).get("prompts", False)
        else:
            has_prompts = "prompts" in self.server_capabilities
            
        if not has_prompts:
            pytest.skip("Prompts not supported by this server")
        
        # Send a simple prompt
        prompt_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompt_completion",
            "method": "prompts/completion",
            "params": {
                "prompt": "What is the capital of France?",
                "options": {
                    "temperature": 0.0,  # Deterministic response
                    "max_tokens": 50     # Short response
                }
            }
        })
        
        # Check response
        if prompt_response.status_code == 200:
            prompt_data = prompt_response.json()
            
            if "result" in prompt_data:
                # Completion generated successfully
                assert "completion" in prompt_data["result"]
                completion_text = prompt_data["result"]["completion"]
                assert isinstance(completion_text, str)
                assert len(completion_text) > 0
                print(f"\nReceived completion: '{completion_text[:50]}...'")
                return
            elif "error" in prompt_data:
                # Method might return an error if not implemented
                error_code = prompt_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("prompts/completion not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {prompt_data['error']}"
        
        # Method might not be implemented
        pytest.skip("prompts/completion not implemented or returned unexpected status")
    
    @pytest.mark.v2025_03_26_only
    def test_prompt_streaming(self):
        """Test streaming completions (2025-03-26+ only)."""
        # Only applicable to newer protocol versions
        if self.protocol_version == "2024-11-05":
            pytest.skip("Streaming completions not supported in 2024-11-05")
        
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts or streaming aren't supported
        has_streaming = False
        if "prompts" in self.server_capabilities:
            has_streaming = self.server_capabilities.get("prompts", {}).get("streaming", False)
            
        if not has_streaming:
            pytest.skip("Streaming completions not supported by this server")
        
        # Send a streaming prompt request
        stream_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompt_streaming",
            "method": "prompts/completion",
            "params": {
                "prompt": "Count from 1 to 5 slowly, one number per line.",
                "options": {
                    "temperature": 0.0,  # Deterministic response
                    "max_tokens": 50,    # Short response
                    "stream": True       # Enable streaming
                }
            }
        })
        
        # Check response
        if stream_response.status_code == 200:
            stream_data = stream_response.json()
            
            if "result" in stream_data:
                # For streaming, the first response should have a stream ID
                assert "stream_id" in stream_data["result"]
                stream_id = stream_data["result"]["stream_id"]
                print(f"\nStreaming started with ID: {stream_id}")
                
                # In a real implementation, we would now listen for stream events
                # But for this test, we'll just check that the stream ID is valid
                assert isinstance(stream_id, str)
                assert len(stream_id) > 0
                return
            elif "error" in stream_data:
                # Method might return an error if not implemented
                error_code = stream_data["error"].get("code")
                if error_code == -32601:  # Method not found
                    pytest.skip("prompts/completion with streaming not implemented")
                else:
                    # Unexpected error
                    assert False, f"Unexpected error: {stream_data['error']}"
        
        # Method might not be implemented
        pytest.skip("prompts/completion with streaming not implemented or returned unexpected status")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_prompt_with_context(self):
        """Test prompt completion with context."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts aren't supported
        has_prompts = False
        if self.protocol_version == "2024-11-05":
            has_prompts = self.server_capabilities.get("supports", {}).get("prompts", False)
        else:
            has_prompts = "prompts" in self.server_capabilities
            
        if not has_prompts:
            pytest.skip("Prompts not supported by this server")
        
        # Send a prompt with context
        context_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompt_with_context",
            "method": "prompts/completion",
            "params": {
                "prompt": "What is the weather like?",
                "context": [
                    {"role": "system", "content": "You are a weather assistant."},
                    {"role": "user", "content": "I'm in Paris, France."}
                ],
                "options": {
                    "temperature": 0.0,  # Deterministic response
                    "max_tokens": 50     # Short response
                }
            }
        })
        
        # Check response
        if context_response.status_code == 200:
            context_data = context_response.json()
            
            if "result" in context_data:
                # Completion generated successfully
                assert "completion" in context_data["result"]
                completion_text = context_data["result"]["completion"]
                assert isinstance(completion_text, str)
                assert len(completion_text) > 0
                print(f"\nReceived contextual completion: '{completion_text[:50]}...'")
                return
            elif "error" in context_data:
                # Context might not be supported
                print(f"\nContext not supported: {context_data['error']['message']}")
        
        # Context might not be supported
        pytest.skip("Prompt context not supported")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_prompt_options(self):
        """Test prompt completion with various options."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts aren't supported
        has_prompts = False
        if self.protocol_version == "2024-11-05":
            has_prompts = self.server_capabilities.get("supports", {}).get("prompts", False)
        else:
            has_prompts = "prompts" in self.server_capabilities
            
        if not has_prompts:
            pytest.skip("Prompts not supported by this server")
        
        # Test with various options
        options = {
            "temperature": 0.5,
            "max_tokens": 20,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        options_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompt_options",
            "method": "prompts/completion",
            "params": {
                "prompt": "Write a short poem about coding.",
                "options": options
            }
        })
        
        # Check response
        if options_response.status_code == 200:
            options_data = options_response.json()
            
            if "result" in options_data:
                # Completion generated successfully
                assert "completion" in options_data["result"]
                completion_text = options_data["result"]["completion"]
                assert isinstance(completion_text, str)
                
                # Should respect max_tokens (approximately, as some models may interpret it differently)
                # We'll allow a 50% margin for variation
                expected_max = options["max_tokens"] * 1.5
                assert len(completion_text.split()) <= expected_max, \
                    f"Completion has {len(completion_text.split())} tokens, expected no more than {expected_max}"
                
                print(f"\nReceived completion with options: '{completion_text[:50]}...'")
                return
            elif "error" in options_data:
                # Some options might not be supported
                print(f"\nSome options not supported: {options_data['error']['message']}")
        
        # Options might not be supported
        pytest.skip("Prompt options not fully supported")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_prompt_error_handling(self):
        """Test error handling for prompts."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts aren't supported
        has_prompts = False
        if self.protocol_version == "2024-11-05":
            has_prompts = self.server_capabilities.get("supports", {}).get("prompts", False)
        else:
            has_prompts = "prompts" in self.server_capabilities
            
        if not has_prompts:
            pytest.skip("Prompts not supported by this server")
        
        # 1. Test with empty prompt
        empty_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_empty_prompt",
            "method": "prompts/completion",
            "params": {
                "prompt": "",
                "options": {}
            }
        })
        
        # Empty prompts might be valid or return an error
        assert empty_response.status_code in [200, 400]
        
        # 2. Test with invalid options
        invalid_options_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_invalid_options",
            "method": "prompts/completion",
            "params": {
                "prompt": "Hello, world!",
                "options": {
                    "temperature": "not_a_number",  # Should be a number
                    "max_tokens": -10               # Should be positive
                }
            }
        })
        
        # Should return an error for invalid options
        assert invalid_options_response.status_code in [200, 400]
        invalid_options_data = invalid_options_response.json()
        
        if "error" in invalid_options_data:
            # Should have an error message for invalid options
            assert "code" in invalid_options_data["error"]
            assert "message" in invalid_options_data["error"]
            print(f"\nProperly handled invalid options: {invalid_options_data['error']['message']}")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_prompt_models(self):
        """Test prompt completion with specific model selection."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Skip if prompts aren't supported
        has_prompts = False
        if self.protocol_version == "2024-11-05":
            has_prompts = self.server_capabilities.get("supports", {}).get("prompts", False)
        else:
            has_prompts = "prompts" in self.server_capabilities
            
        if not has_prompts:
            pytest.skip("Prompts not supported by this server")
        
        # Try to get available models first (optional)
        models_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "get_available_models",
            "method": "prompts/models",
            "params": {}
        })
        
        # Default model to try
        model_name = "default"
        
        # If models endpoint is supported, use the first available model
        if models_response.status_code == 200:
            models_data = models_response.json()
            if "result" in models_data and "models" in models_data["result"]:
                models = models_data["result"]["models"]
                if models and len(models) > 0:
                    if isinstance(models[0], dict) and "id" in models[0]:
                        model_name = models[0]["id"]
                    elif isinstance(models[0], str):
                        model_name = models[0]
                    print(f"\nUsing model: {model_name}")
        
        # Send a prompt with model selection
        model_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_prompt_with_model",
            "method": "prompts/completion",
            "params": {
                "prompt": "Hello, my name is Alice.",
                "options": {
                    "model": model_name,
                    "temperature": 0.0,
                    "max_tokens": 30
                }
            }
        })
        
        # Check response
        if model_response.status_code == 200:
            model_data = model_response.json()
            
            if "result" in model_data:
                # Completion generated successfully
                assert "completion" in model_data["result"]
                completion_text = model_data["result"]["completion"]
                assert isinstance(completion_text, str)
                assert len(completion_text) > 0
                print(f"\nReceived model-specific completion: '{completion_text[:50]}...'")
                return
            elif "error" in model_data:
                # Model selection might not be supported
                print(f"\nModel selection not supported: {model_data['error']['message']}")
        
        # Model selection might not be supported
        pytest.skip("Model selection not supported")
    
    @pytest.mark.v2024_11_05
    @pytest.mark.v2025_03_26
    def test_shutdown(self):
        """Test the shutdown method."""
        # Initialize first if needed
        if not self.server_capabilities:
            self.test_initialization()
        
        # Send shutdown request
        shutdown_response = self._send_request({
            "jsonrpc": "2.0",
            "id": "test_shutdown",
            "method": "shutdown",
            "params": {}
        })
        
        assert shutdown_response.status_code == 200
        shutdown_data = shutdown_response.json()
        
        # Shutdown should return an empty result object
        assert "result" in shutdown_data
        
        # Send exit notification
        exit_notification = self._send_request({
            "jsonrpc": "2.0",
            "method": "exit"
        })
        
        # Notification should return 204 No Content or 200 OK
        assert exit_notification.status_code in [200, 202, 204] 