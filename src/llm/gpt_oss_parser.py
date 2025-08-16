#!/usr/bin/env python3
"""
GPT-OSS Model Streaming Parser

This module handles the specialized streaming output format of GPT-OSS models, 
which use channel-based output with analysis and final channels.

Based on the minimal MLX pattern for parsing GPT-OSS output with proper
streaming support and state machine logic.

Format:
<|start|>assistant<|channel|>analysis<|message|>...<|end|>
<|start|>assistant<|channel|>final<|message|>...<|end|>
"""

from typing import Iterator, Tuple, Optional, Generator
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)


class GPTOssStreamingParser:
    """Streaming parser for GPT-OSS model output format using state machine."""
    
    # Tag constants taken from the GPT-OSS spec (support both long and short forms)
    TAG_ANALYSIS_LONG = "<|start|>assistant<|channel|>analysis<|message|>"
    TAG_FINAL_LONG = "<|start|>assistant<|channel|>final<|message|>"
    TAG_ANALYSIS_SHORT = "<|channel|>analysis<|message|>"
    TAG_FINAL_SHORT = "<|channel|>final<|message|>"
    TAG_END = "<|end|>"
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state for a new stream."""
        self.buf = ""
        self.state = None  # None, "cot", "final"
        self.cot_parts = []
        self.final_parts = []
    
    def parse_stream_token(self, token: str) -> Optional[Tuple[str, str]]:
        """
        Parse a single token from the stream.
        
        Args:
            token: Single token from the MLX stream
            
        Returns:
            (cot, answer) tuple if parsing is complete, None otherwise
        """
        if not token:
            return None
            
        self.buf += token
        
        while True:
            # 1) Flip state when a start-tag appears (support both long/short variants)
            if self.state is None and (
                self.TAG_ANALYSIS_LONG in self.buf
                or self.TAG_FINAL_LONG in self.buf
                or self.TAG_ANALYSIS_SHORT in self.buf
                or self.TAG_FINAL_SHORT in self.buf
            ):
                if self.TAG_ANALYSIS_LONG in self.buf or self.TAG_ANALYSIS_SHORT in self.buf:
                    tag = (
                        self.TAG_ANALYSIS_LONG
                        if self.TAG_ANALYSIS_LONG in self.buf
                        else self.TAG_ANALYSIS_SHORT
                    )
                    self.state = "cot"
                else:
                    tag = (
                        self.TAG_FINAL_LONG
                        if self.TAG_FINAL_LONG in self.buf
                        else self.TAG_FINAL_SHORT
                    )
                    self.state = "final"
                
                self.buf = self.buf.split(tag, 1)[1]  # drop the tag itself
                continue
            
            # 2) Capture until we hit the universal <|end|> tag
            if self.state and self.TAG_END in self.buf:
                chunk, self.buf = self.buf.split(self.TAG_END, 1)
                if self.state == "cot":
                    self.cot_parts.append(chunk)
                else:  # final
                    self.final_parts.append(chunk)
                self.state = None
                # loop again: there might be another start-tag already queued
                continue
            
            # 3) No complete tag found → keep buffering and request more
            if self.state:
                if self.state == "cot":
                    self.cot_parts.append(self.buf)
                else:  # final
                    self.final_parts.append(self.buf)
                self.buf = ""
            break  # exit inner while and wait for next token
        
        # Return results if we have content in both channels
        if self.cot_parts and self.final_parts:
            chain_of_thought = "".join(self.cot_parts).strip()
            answer = "".join(self.final_parts).strip()
            return chain_of_thought, answer
        
        return None
    
    def finalize(self) -> Tuple[str, str]:
        """
        Finalize parsing and return results.
        
        Returns:
            (cot, answer) tuple with whatever content was captured
        """
        chain_of_thought = "".join(self.cot_parts).strip()
        answer = "".join(self.final_parts).strip()
        return chain_of_thought, answer


def parse_gpt_oss_stream(model, tokenizer, prompt: str, **generation_kwargs) -> Generator[Tuple[str, str], None, None]:
    """
    Parse GPT-OSS stream and yield (cot, answer) tuples as they become available.
    
    Args:
        model: MLX model instance
        tokenizer: MLX tokenizer instance  
        prompt: Input prompt for the model
        **generation_kwargs: Additional generation parameters
        
    Yields:
        (cot, answer) tuples as parsing completes
    """
    try:
        from mlx_lm import stream_generate
    except ImportError:
        logger.error("mlx_lm not available for GPT-OSS streaming")
        return
    
    parser = GPTOssStreamingParser()
    
    try:
        for response_obj in stream_generate(
            model, 
            tokenizer, 
            prompt=prompt, 
            **generation_kwargs
        ):
            token = response_obj.text if hasattr(response_obj, 'text') else str(response_obj)
            result = parser.parse_stream_token(token)
            if result:
                yield result
                
        # Yield final results if any content remains
        final_result = parser.finalize()
        if final_result[0] or final_result[1]:  # If either COT or answer has content
            yield final_result
            
    except Exception as e:
        logger.error(f"Error in GPT-OSS stream parsing: {e}")
        # Return whatever we managed to parse
        final_result = parser.finalize()
        if final_result[0] or final_result[1]:
            yield final_result


def create_gpt_oss_chat_prompt(tokenizer, system_content: str, user_content: str) -> str:
    """
    Create a properly formatted chat prompt for GPT-OSS models.
    
    Args:
        tokenizer: MLX tokenizer instance
        system_content: System message content
        user_content: User message content
        
    Returns:
        Formatted prompt string
    """
    if hasattr(tokenizer, 'apply_chat_template'):
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        return tokenizer.apply_chat_template(
            messages, 
            add_generation_prompt=True,
            tokenize=False
        )
    else:
        # Fallback for tokenizers without chat template support
        return f"System: {system_content}\n\nUser: {user_content}\n\nAssistant:"


# Legacy compatibility functions for existing code
class GPTOssParser:
    """Legacy parser class for backward compatibility."""
    
    def __init__(self):
        self.streaming_parser = GPTOssStreamingParser()
    
    def parse_response(self, response: str) -> dict:
        """
        Parse a complete GPT-OSS response (legacy compatibility).
        
        Args:
            response: Complete response string
            
        Returns:
            Dictionary with analysis, final, thinking, and clean_response keys
        """
        # Reset parser for new response
        self.streaming_parser.reset()
        
        # Feed the entire response through the streaming parser
        result = self.streaming_parser.parse_stream_token(response)
        if not result:
            # Try to finalize in case the response was incomplete
            result = self.streaming_parser.finalize()
        
        cot, answer = result if result else ("", "")
        
        return {
            'analysis': cot,
            'final': answer,
            'thinking': cot,  # For compatibility
            'clean_response': answer
        }
    
    def extract_thinking_content(self, response: str) -> str:
        """Extract thinking content (analysis channel)."""
        parsed = self.parse_response(response)
        return parsed.get('analysis', '')
    
    def extract_clean_response(self, response: str) -> str:
        """Extract clean response (final channel).""" 
        parsed = self.parse_response(response)
        return parsed.get('clean_response', '')
    
    def is_gpt_oss_format(self, response: str) -> bool:
        """Check if response uses GPT-OSS format."""
        return (
            GPTOssStreamingParser.TAG_ANALYSIS_LONG in response
            or GPTOssStreamingParser.TAG_FINAL_LONG in response
            or GPTOssStreamingParser.TAG_ANALYSIS_SHORT in response
            or GPTOssStreamingParser.TAG_FINAL_SHORT in response
        )


# Convenience functions for backward compatibility
def parse_gpt_oss_response(response: str) -> dict:
    """Convenience function to parse GPT-OSS response."""
    parser = GPTOssParser()
    return parser.parse_response(response)


def extract_thinking_from_gpt_oss(response: str) -> str:
    """Convenience function to extract thinking content."""
    parser = GPTOssParser()
    return parser.extract_thinking_content(response)


def extract_clean_from_gpt_oss(response: str) -> str:
    """Convenience function to extract clean response."""
    parser = GPTOssParser()
    return parser.extract_clean_response(response)


# Example usage for testing
if __name__ == "__main__":
    # Test the new streaming parser
    print("GPT-OSS Streaming Parser Test")
    
    # Example GPT-OSS response for testing
    test_response = (
        "<|start|>assistant<|channel|>analysis<|message|>"
        "Let me analyze this text. The input has some spelling errors that need correction."
        "<|end|>"
        "<|start|>assistant<|channel|>final<|message|>"
        "- Patient complained of fever and chills for 3 days."
        "<|end|>"
    )
    
    # Test legacy parser
    parser = GPTOssParser()
    result = parser.parse_response(test_response)
    print("\nLegacy parser result:")
    print(f"Analysis: {result['analysis']}")
    print(f"Final: {result['final']}")
    
    # Test streaming parser
    streaming_parser = GPTOssStreamingParser()
    final_result = streaming_parser.parse_stream_token(test_response)
    print("\nStreaming parser result:")
    if final_result:
        cot, answer = final_result
        print(f"COT: {cot}")
        print(f"Answer: {answer}")
    else:
        print("No result from streaming parser")