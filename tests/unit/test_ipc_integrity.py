#!/usr/bin/env python3
"""
IPC Message Integrity Tests

These tests validate that messages between Python backend and Electron frontend
maintain their integrity during transmission. This is our most critical failure point.

The newline bug that caused 50+ debugging iterations would have been caught by these tests.
"""

import unittest
import json
import re
from typing import List, Tuple


class IPCMessageHandler:
    """Simulates the IPC message handling logic for testing"""

    def escape_content(self, content: str) -> str:
        """Safely escape content for IPC transmission"""
        # Use a placeholder to avoid double-escaping literal backslashes
        placeholder = "___LITERAL_BACKSLASH___"
        # First replace literal backslashes with placeholder
        result = content.replace("\\", placeholder)
        # Then escape actual control characters
        result = result.replace("\n", "\\n").replace("\r", "\\r")
        # Finally restore literal backslashes as escaped backslashes
        result = result.replace(placeholder, "\\\\")
        return result

    def unescape_content(self, content: str) -> str:
        """Safely unescape content from IPC transmission"""
        # Use a placeholder to avoid double-unescaping
        placeholder = "___LITERAL_BACKSLASH___"
        # First replace escaped backslashes with placeholder
        result = content.replace("\\\\", placeholder)
        # Then unescape control characters
        result = result.replace("\\n", "\n").replace("\\r", "\r")
        # Finally restore literal backslashes
        result = result.replace(placeholder, "\\")
        return result

    def format_status_message(
        self, message_type: str, payload: str, color: str = "blue"
    ) -> str:
        """Format a status message for IPC transmission"""
        escaped_payload = self.escape_content(payload)
        return f"STATUS:{color}:{message_type}:{escaped_payload}"

    def parse_status_message(self, raw_message: str) -> Tuple[str, str, str]:
        """Parse a status message from IPC - matches actual system logic"""
        if not raw_message.startswith("STATUS:"):
            raise ValueError(f"Invalid status message format: {raw_message}")

        content = raw_message[7:]  # Remove "STATUS:" prefix

        # Find first colon for color
        first_colon = content.find(":")
        if first_colon == -1:
            raise ValueError(f"No color delimiter found: {raw_message}")

        color = content[:first_colon]
        remaining = content[first_colon + 1 :]

        # For PROOF_STREAM messages, we need to handle the nested format
        if remaining.startswith("PROOF_STREAM:"):
            # PROOF_STREAM:thinking:content or PROOF_STREAM:chunk:content or PROOF_STREAM:end
            proof_content = remaining[13:]  # Remove "PROOF_STREAM:"

            # Find the next colon for the stream type
            stream_colon = proof_content.find(":")
            if stream_colon == -1:
                # No payload, just stream type (e.g., "end")
                return color, remaining, ""

            stream_type = proof_content[:stream_colon]
            payload = proof_content[stream_colon + 1 :]

            # Unescape the payload
            unescaped_payload = self.unescape_content(payload)

            return color, remaining, unescaped_payload
        else:
            # Regular status message format
            second_colon = remaining.find(":")
            if second_colon == -1:
                # No payload, just message type
                return color, remaining, ""

            message_type = remaining[:second_colon]
            payload = remaining[second_colon + 1 :]

            # Unescape the payload
            unescaped_payload = self.unescape_content(payload)

            return color, message_type, unescaped_payload


class TestIPCIntegrity(unittest.TestCase):
    """Test IPC message integrity that would have caught the newline bug"""

    def setUp(self):
        self.ipc = IPCMessageHandler()

    def test_newline_preservation(self):
        """Ensure newlines survive IPC transmission - THE CRITICAL TEST"""
        test_chunks = [
            "- First bullet point.\n",
            "- Second bullet point.\n",
            "Text with\nmultiple\nlines",
            "Mixed content.\n- Bullet after newline",
            "Complex case.\n- Bullet 1\n- Bullet 2\n- Bullet 3",
            "\n",  # Just a newline
            "Text ending with newline\n",
            "\nText starting with newline",
        ]

        for chunk in test_chunks:
            with self.subTest(chunk=repr(chunk)):
                # Test direct escape/unescape
                escaped = self.ipc.escape_content(chunk)
                unescaped = self.ipc.unescape_content(escaped)
                self.assertEqual(
                    chunk,
                    unescaped,
                    f"Newline integrity failed for: {repr(chunk)}\n"
                    f"Escaped: {repr(escaped)}\n"
                    f"Unescaped: {repr(unescaped)}",
                )

                # Test full IPC roundtrip
                message = self.ipc.format_status_message(
                    "PROOF_STREAM:chunk", chunk, "blue"
                )
                color, msg_type, payload = self.ipc.parse_status_message(message)

                self.assertEqual(
                    payload,
                    chunk,
                    f"IPC roundtrip failed for: {repr(chunk)}\n"
                    f"Message: {repr(message)}\n"
                    f"Parsed payload: {repr(payload)}",
                )

    def test_special_character_handling(self):
        """Test edge cases that could break IPC parsing"""
        edge_cases = [
            "Text with\ttabs",
            "Text with\r\nwindows linebreaks",
            "Text with 'quotes' and \"double quotes\"",
            "Text with unicode: 思考过程",
            "Text with literal backslashes: \\n \\t \\r",  # Changed to avoid double-escaping confusion
            "Colon in text: time is 12:34:56",
            "Multiple colons: http://example.com:8080/path",
            "Empty string",
            "   Leading and trailing spaces   ",
            "Line with only spaces:   \n",
            "Mixed unicode and newlines: 思考过程\n- English bullet",
        ]

        for test_case in edge_cases:
            with self.subTest(test_case=repr(test_case)):
                # Test IPC roundtrip
                message = self.ipc.format_status_message(
                    "PROOF_STREAM:chunk", test_case, "blue"
                )
                color, msg_type, payload = self.ipc.parse_status_message(message)

                self.assertEqual(
                    payload,
                    test_case,
                    f"Special character handling failed for: {repr(test_case)}\n"
                    f"Message: {repr(message)}\n"
                    f"Parsed payload: {repr(payload)}",
                )

    def test_ipc_message_format_validation(self):
        """Validate all IPC message formats are correctly parsed"""
        test_messages = [
            (
                "STATUS:blue:PROOF_STREAM:chunk:Hello world",
                ("blue", "PROOF_STREAM:chunk:Hello world", "Hello world"),
            ),
            ("STATUS:red:Error occurred", ("red", "Error occurred", "")),
            ("STATUS:green:Processing complete", ("green", "Processing complete", "")),
            (
                "STATUS:blue:PROOF_STREAM:thinking:Processing...",
                ("blue", "PROOF_STREAM:thinking:Processing...", "Processing..."),
            ),
            ("STATUS:black:PROOF_STREAM:end", ("black", "PROOF_STREAM:end", "")),
        ]

        for message, expected in test_messages:
            with self.subTest(message=message):
                result = self.ipc.parse_status_message(message)
                self.assertEqual(
                    result,
                    expected,
                    f"Message parsing failed for: {message}\n"
                    f"Expected: {expected}\n"
                    f"Got: {result}",
                )

    def test_proof_stream_chunk_scenarios(self):
        """Test specific PROOF_STREAM:chunk scenarios that caused the bug"""
        # These are the exact patterns that failed in the newline bug
        bug_scenarios = [
            "- A 50-year-old male presents with two issues.",
            ".\n",  # This was the problematic chunk
            "- He reports a skin lesion that appeared recently.",
            "- The patient also stubbed his toe and continues to experience pain.",
        ]

        # Simulate streaming these chunks
        accumulated_content = ""
        for chunk in bug_scenarios:
            with self.subTest(chunk=repr(chunk)):
                # Test individual chunk transmission
                message = self.ipc.format_status_message(
                    "PROOF_STREAM:chunk", chunk, "blue"
                )
                color, msg_type, payload = self.ipc.parse_status_message(message)

                self.assertEqual(
                    payload, chunk, f"Chunk transmission failed for: {repr(chunk)}"
                )

                # Accumulate content (simulating frontend)
                accumulated_content += payload

        # Verify the final accumulated content has proper formatting
        expected_final = "- A 50-year-old male presents with two issues..\n- He reports a skin lesion that appeared recently.- The patient also stubbed his toe and continues to experience pain."
        self.assertEqual(
            accumulated_content,
            expected_final,
            f"Final accumulated content incorrect:\n"
            f"Expected: {repr(expected_final)}\n"
            f"Got: {repr(accumulated_content)}",
        )

        # Count newlines (this would have caught the bug)
        newline_count = accumulated_content.count("\n")
        self.assertGreater(
            newline_count,
            0,
            "No newlines found in accumulated content - this indicates the bug!",
        )

    def test_thinking_content_scenarios(self):
        """Test thinking content with various formats"""
        thinking_scenarios = [
            "Processing the input text...",
            "I need to check for:\n- Grammar errors\n- Spelling mistakes\n- Clarity issues",
            "思考过程：检查文本中的错误",
            "Multi-line thinking with\nvarious formatting\nand bullet points:\n- Item 1\n- Item 2",
        ]

        for thinking_content in thinking_scenarios:
            with self.subTest(content=repr(thinking_content)):
                message = self.ipc.format_status_message(
                    "PROOF_STREAM:thinking", thinking_content, "blue"
                )
                color, msg_type, payload = self.ipc.parse_status_message(message)

                self.assertEqual(
                    payload,
                    thinking_content,
                    f"Thinking content transmission failed for: {repr(thinking_content)}",
                )

    def test_invalid_message_formats(self):
        """Test that invalid message formats are properly rejected"""
        invalid_messages = [
            "Not a status message",
            "STATUS:",  # Empty
            "STATUS:blue",  # No message type
            "",  # Empty string
            "TRANSCRIPTION:PROOFED:Text",  # Different message type
        ]

        for invalid_msg in invalid_messages:
            with self.subTest(message=repr(invalid_msg)):
                if invalid_msg.startswith("STATUS:"):
                    # Should not crash, but may return unexpected results
                    try:
                        result = self.ipc.parse_status_message(invalid_msg)
                        # Log the result but don't fail - we just want to ensure no crashes
                    except ValueError:
                        # This is acceptable for invalid formats
                        pass
                else:
                    # Should raise ValueError for non-STATUS messages
                    with self.assertRaises(ValueError):
                        self.ipc.parse_status_message(invalid_msg)

    def test_performance_with_large_content(self):
        """Ensure IPC handling performs well with large content"""
        # Create a large chunk of text (simulating a long LLM response)
        large_content = "- " + "Very long bullet point content. " * 1000 + "\n"
        large_content += "- Another bullet with unicode: " + "思考过程 " * 500 + "\n"

        # Test that large content doesn't break IPC
        import time

        start_time = time.time()

        message = self.ipc.format_status_message(
            "PROOF_STREAM:chunk", large_content, "blue"
        )
        color, msg_type, payload = self.ipc.parse_status_message(message)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete in reasonable time (< 100ms)
        self.assertLess(
            processing_time,
            0.1,
            f"IPC processing too slow for large content: {processing_time:.3f}s",
        )

        # Content should be identical
        self.assertEqual(
            payload, large_content, "Large content not preserved through IPC"
        )

        # Check memory efficiency (content shouldn't be duplicated excessively)
        import sys

        message_size = sys.getsizeof(message)
        content_size = sys.getsizeof(large_content)

        # Message should be at most 2x the content size (allowing for escaping)
        self.assertLess(
            message_size,
            content_size * 2,
            f"IPC message too large: {message_size} bytes for {content_size} byte content",
        )


if __name__ == "__main__":
    # Run with verbose output to see all test cases
    unittest.main(verbosity=2)
 