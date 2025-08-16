#!/usr/bin/env python3
"""
Test script to verify GPT-OSS streaming fix.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.llm.gpt_oss_parser import parse_gpt_oss_response, extract_thinking_from_gpt_oss, extract_clean_from_gpt_oss

def test_gpt_oss_parsing():
    """Test GPT-OSS parsing with the example output."""
    
    # Test with the actual output from the user's example
    test_response = '''<|channel|>analysis<|message|>We need to produce a response with two parts: PART 1: thought process inside <think> tags. Then PART 2: corrected text as bullet list. The input text: "21 year old male with no specific complaints."

We need to correct grammar, punctuation, and clarity. The phrase "21 year old male" should be "21-year-old male". Also "no specific complaints" maybe "no specific complaints" is fine. The sentence: "21-year-old male with no specific complaints." Should be "21-year-old male with no specific complaints." But we might want to add a period at end. Also maybe "21-year-old male" is correct. The bullet list: "- 21-year-old male with no specific complaints." That is the corrected text.

We need to ensure bullet list only. So output:

<think>
... (thought process)
</think>
- 21-year-old male with no specific complaints.

We need to ensure no extra text after bullet. Also no trailing spaces. Ensure bullet list only. So final answer: Provide the corrected text. Let's produce.<|end|><|start|>assistant<|channel|>final<|message|><think>
The input sentence is: "21 year old male with no specific complaints." I will check for grammatical and punctuation errors. The phrase "21 year old" should be hyphenated as "21-year-old". The rest of the sentence is fine. I will correct the wording and add a period at the end. The corrected sentence is concise and suitable for a medical chart.
</think>
- 21-year-old male with no specific complaints.'''

    print("=== Testing GPT-OSS Parsing ===")
    print(f"Input length: {len(test_response)} characters")
    
    # Test parsing
    parsed = parse_gpt_oss_response(test_response)
    
    print("\n=== Parsed Results ===")
    print(f"Analysis: {parsed['analysis'][:100]}...")
    print(f"Final: {parsed['final'][:100]}...")
    print(f"Thinking: {parsed['thinking'][:100]}...")
    print(f"Clean Response: {parsed['clean_response']}")
    
    # Test thinking extraction
    thinking_content = extract_thinking_from_gpt_oss(test_response)
    print(f"\n=== Thinking Content ===")
    print(f"Length: {len(thinking_content)} characters")
    print(f"Content: {thinking_content[:200]}...")
    
    # Test clean response extraction
    clean_response = extract_clean_from_gpt_oss(test_response)
    print(f"\n=== Clean Response ===")
    print(f"Length: {len(clean_response)} characters")
    print(f"Content: {clean_response}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_gpt_oss_parsing() 