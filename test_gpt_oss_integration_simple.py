#!/usr/bin/env python3
"""
Simple test for GPT-OSS integration with LLM handler.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.llm.llm_handler import LLMHandler
from src.config import config

def test_gpt_oss_integration():
    """Test GPT-OSS integration with LLM handler."""
    
    print("Testing GPT-OSS integration...")
    
    # Create LLM handler
    handler = LLMHandler()
    
    # Set GPT-OSS model
    handler.update_selected_models('nightmedia/gpt-oss-20b-q4-hi-mlx', 'nightmedia/gpt-oss-20b-q4-hi-mlx')
    
    # Test text
    test_text = "21 year old male here with no specific complaints."
    
    print(f"Input text: {test_text}")
    print("Processing with GPT-OSS model...")
    
    # Process the text
    handler.process_text(test_text, "proofread")
    
    print("Test completed. Check the application for results.")

if __name__ == "__main__":
    test_gpt_oss_integration() 