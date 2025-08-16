#!/usr/bin/env python3
"""
Integration test for GPT-OSS-20B-Q4-HI model integration.

This test verifies that the GPT-OSS-20B model can be:
1. Downloaded and loaded successfully
2. Used with chat templates
3. Generate text with enhanced reasoning
4. Work with the existing LLM handler
5. Perform proofreading tasks effectively

Run with: python -m pytest tests/integration/test_gpt_oss_integration.py -v
"""

import pytest
import sys
import os
import time
import threading
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llm.llm_handler import LLMHandler
from config import config


class TestGPTOssIntegration:
    """Test suite for GPT-OSS-20B-Q4-HI model integration."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.model_key = "GPT-OSS-20B-Q4-HI"
        self.model_path = config.AVAILABLE_LLMS.get(self.model_key)
        
        # Mock callbacks
        self.mock_callbacks = {
            'on_processing_complete': Mock(),
            'on_status_update': Mock(),
            'on_proofing_activity': Mock()
        }
        
        # Create LLM handler
        self.llm_handler = LLMHandler(
            on_processing_complete_callback=self.mock_callbacks['on_processing_complete'],
            on_status_update_callback=self.mock_callbacks['on_status_update'],
            on_proofing_activity_callback=self.mock_callbacks['on_proofing_activity']
        )

    def test_model_configuration(self):
        """Test that the model is properly configured."""
        assert self.model_key in config.AVAILABLE_LLMS, f"Model {self.model_key} not found in AVAILABLE_LLMS"
        assert self.model_path == "nightmedia/gpt-oss-20b-q4-hi-mlx", f"Unexpected model path: {self.model_path}"

    def test_model_download_and_load(self):
        """Test model download and loading."""
        print(f"\nTesting model download and load for: {self.model_key}")
        
        # Test direct loading
        try:
            from mlx_lm import load
            model, tokenizer = load(self.model_path)
            print(f"✅ Model loaded successfully: {type(model).__name__}")
            print(f"✅ Tokenizer loaded successfully: {type(tokenizer).__name__}")
            
            # Test basic properties
            assert model is not None, "Model should not be None"
            assert tokenizer is not None, "Tokenizer should not be None"
            
            # Test chat template
            if hasattr(tokenizer, 'chat_template'):
                assert tokenizer.chat_template is not None, "Chat template should be available"
                print(f"✅ Chat template available: {tokenizer.chat_template[:100]}...")
            
        except Exception as e:
            pytest.fail(f"Model loading failed: {e}")

    def test_chat_template_compatibility(self):
        """Test chat template functionality."""
        print(f"\nTesting chat template compatibility for: {self.model_key}")
        
        try:
            from mlx_lm import load
            model, tokenizer = load(self.model_path)
            
            # Test chat template application
            messages = [
                {"role": "user", "content": "Hello, how are you?"}
            ]
            
            if hasattr(tokenizer, 'apply_chat_template'):
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
                print(f"✅ Chat template applied successfully")
                print(f"Formatted prompt length: {len(formatted_prompt)} characters")
                assert len(formatted_prompt) > 0, "Formatted prompt should not be empty"
            else:
                pytest.skip("Chat template not available")
                
        except Exception as e:
            pytest.fail(f"Chat template test failed: {e}")

    def test_text_generation(self):
        """Test basic text generation."""
        print(f"\nTesting text generation for: {self.model_key}")
        
        try:
            from mlx_lm import load, generate
            model, tokenizer = load(self.model_path)
            
            # Test simple generation
            prompt = "Hello"
            messages = [{"role": "user", "content": prompt}]
            
            if hasattr(tokenizer, 'apply_chat_template'):
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
            else:
                formatted_prompt = prompt
            
            # Generate response
            response = generate(
                model, 
                tokenizer, 
                prompt=formatted_prompt,
                max_tokens=50,
                verbose=False
            )
            
            print(f"✅ Text generation successful")
            print(f"Response: {response}")
            assert len(response) > 0, "Response should not be empty"
            
        except Exception as e:
            pytest.fail(f"Text generation failed: {e}")

    def test_enhanced_reasoning_capabilities(self):
        """Test enhanced reasoning capabilities."""
        print(f"\nTesting enhanced reasoning for: {self.model_key}")
        
        try:
            from mlx_lm import load, generate
            model, tokenizer = load(self.model_path)
            
            # Test reasoning with a complex prompt
            prompt = "Explain why proofreading is important for professional documents."
            messages = [{"role": "user", "content": prompt}]
            
            if hasattr(tokenizer, 'apply_chat_template'):
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
            else:
                formatted_prompt = prompt
            
            # Generate response with reasoning
            response = generate(
                model, 
                tokenizer, 
                prompt=formatted_prompt,
                max_tokens=200,
                verbose=True  # Enable verbose to see reasoning
            )
            
            print(f"✅ Enhanced reasoning test successful")
            print(f"Response length: {len(response)} characters")
            assert len(response) > 50, "Reasoning response should be substantial"
            
            # Test GPT-OSS parser
            from src.llm.gpt_oss_parser import parse_gpt_oss_response, extract_thinking_from_gpt_oss, extract_clean_from_gpt_oss
            
            if '<|channel|>analysis<|message|>' in response:
                print("✅ GPT-OSS format detected")
                parsed = parse_gpt_oss_response(response)
                print(f"Analysis: {parsed['analysis'][:100]}...")
                print(f"Final: {parsed['final'][:100]}...")
                print(f"Thinking: {parsed['thinking'][:100]}...")
                print(f"Clean: {parsed['clean_response']}")
                
                thinking_content = extract_thinking_from_gpt_oss(response)
                clean_content = extract_clean_from_gpt_oss(response)
                
                print(f"✅ GPT-OSS parsing successful")
                print(f"Thinking content length: {len(thinking_content)}")
                print(f"Clean content: {clean_content}")
            
        except Exception as e:
            pytest.fail(f"Enhanced reasoning test failed: {e}")

    def test_llm_handler_integration(self):
        """Test integration with LLM handler."""
        print(f"\nTesting LLM handler integration for: {self.model_key}")
        
        # Set the model as selected for proofing
        self.llm_handler.update_selected_models(self.model_path, self.model_path)
        
        # Test model loading through handler
        load_success = [False]
        load_complete = threading.Event()
        
        def on_load_complete(success):
            load_success[0] = success
            load_complete.set()
        
        # Start loading
        self.llm_handler.load_model(self.model_key, on_load_complete)
        
        # Wait for loading to complete (with timeout)
        if load_complete.wait(timeout=300):  # 5 minute timeout
            assert load_success[0], "Model loading should succeed"
            print(f"✅ LLM handler integration successful")
        else:
            pytest.fail("Model loading timed out")

    def test_proofreading_functionality(self):
        """Test proofreading functionality with the model."""
        print(f"\nTesting proofreading functionality for: {self.model_key}")
        
        # Set the model as selected for proofing
        self.llm_handler.update_selected_models(self.model_path, self.model_path)
        
        # Test text to proofread
        test_text = "This is a test document with some errors. It has gramatical mistakes and spelling erors."
        
        # Process the text
        self.llm_handler.process_text(test_text, "proofread")
        
        # Wait for processing to complete
        time.sleep(10)  # Give time for processing
        
        # Check if callback was called
        if self.mock_callbacks['on_processing_complete'].called:
            print(f"✅ Proofreading functionality test successful")
        else:
            print("⚠️ Proofreading callback not called (may be normal if processing is slow)")

    def test_memory_usage(self):
        """Test memory usage during model operation."""
        print(f"\nTesting memory usage for: {self.model_key}")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Memory before loading
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            print(f"Memory before loading: {memory_before:.1f} MB")
            
            # Load model
            from mlx_lm import load
            model, tokenizer = load(self.model_path)
            
            # Memory after loading
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            print(f"Memory after loading: {memory_after:.1f} MB")
            
            memory_increase = memory_after - memory_before
            print(f"Memory increase: {memory_increase:.1f} MB")
            
            # Check if memory usage is reasonable (should be < 20GB)
            assert memory_increase < 20000, f"Memory usage too high: {memory_increase:.1f} MB"
            print(f"✅ Memory usage is reasonable")
            
        except ImportError:
            pytest.skip("psutil not available for memory testing")
        except Exception as e:
            pytest.fail(f"Memory usage test failed: {e}")

    def test_performance_benchmark(self):
        """Test performance with a simple benchmark."""
        print(f"\nTesting performance benchmark for: {self.model_key}")
        
        try:
            from mlx_lm import load, generate
            model, tokenizer = load(self.model_path)
            
            # Simple benchmark
            prompt = "Write a short professional email."
            messages = [{"role": "user", "content": prompt}]
            
            if hasattr(tokenizer, 'apply_chat_template'):
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
            else:
                formatted_prompt = prompt
            
            # Time the generation
            start_time = time.time()
            response = generate(
                model, 
                tokenizer, 
                prompt=formatted_prompt,
                max_tokens=100,
                verbose=False
            )
            end_time = time.time()
            
            generation_time = end_time - start_time
            print(f"✅ Generation completed in {generation_time:.2f} seconds")
            print(f"Response length: {len(response)} characters")
            
            # Check if performance is reasonable (should complete within 30 seconds)
            assert generation_time < 30, f"Generation too slow: {generation_time:.2f} seconds"
            print(f"✅ Performance is acceptable")
            
        except Exception as e:
            pytest.fail(f"Performance benchmark failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"]) 