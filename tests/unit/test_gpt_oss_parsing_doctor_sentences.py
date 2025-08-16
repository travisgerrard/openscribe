#!/usr/bin/env python3
import unittest
import os
import sys
from unittest.mock import MagicMock

# Ensure project root is on sys.path for `src` imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.llm.gpt_oss_parser import GPTOssStreamingParser
from src.llm.llm_handler import LLMHandler
from src.config import config


class TestGPTOssDoctorSentences(unittest.TestCase):
    def setUp(self):
        # Create a handler with mocked callbacks
        self.thinking_msgs = []
        self.chunk_msgs = []
        self.ends = 0

        def on_status(message, color):
            # Emulate the renderer_ipc parsing (we only need PROOF_STREAM messages)
            if message.startswith("PROOF_STREAM:thinking:"):
                self.thinking_msgs.append(message.split(":", 2)[2])
            elif message.startswith("PROOF_STREAM:chunk:"):
                self.chunk_msgs.append(message.split(":", 2)[2])
            elif message == "PROOF_STREAM:end":
                self.ends += 1

        self.handler = LLMHandler(
            on_processing_complete_callback=lambda *args, **kwargs: None,
            on_status_update_callback=on_status,
            on_proofing_activity_callback=lambda *_: None,
        )
        # Pretend a GPT-OSS model is selected; we won't actually load it in unit test
        self.handler._selected_proofing_model_id = config.AVAILABLE_LLMS.get("GPT-OSS-20B-Q4-HI")

    def _simulate_stream(self, tokens):
        # Feed tokens to the streaming parser and route as the handler does
        parser = GPTOssStreamingParser()
        cot_accum, ans_accum = "", ""
        for tok in tokens:
            res = parser.parse_stream_token(tok)
            if not res:
                continue
            cot, ans = res
            if cot:
                # Only send incremental portion
                new_cot = cot[len(cot_accum):]
                if new_cot:
                    escaped = new_cot.replace("\n", "\\n").replace("\r", "\\r")
                    self.handler._log_status(f"PROOF_STREAM:thinking:{escaped}", "blue")
                cot_accum = cot
            if ans:
                new_ans = ans[len(ans_accum):]
                if new_ans:
                    # Apply backend stripping to mimic real handler behavior
                    cleaned = self.handler._strip_think_tags(new_ans)
                    if cleaned:
                        escaped = cleaned.replace("\n", "\\n").replace("\r", "\\r")
                        self.handler._log_status(f"PROOF_STREAM:chunk:{escaped}", "blue")
                ans_accum = ans
        # finalize
        cot, ans = parser.finalize()
        if cot:
            new_cot = cot[len(cot_accum):]
            if new_cot:
                escaped = new_cot.replace("\n", "\\n").replace("\r", "\\r")
                self.handler._log_status(f"PROOF_STREAM:thinking:{escaped}", "blue")
        if ans:
            cleaned_full = self.handler._strip_think_tags(ans)
            if cleaned_full:
                base = self.handler._strip_think_tags(ans_accum) if ans_accum else ""
                full_increment = cleaned_full[len(base):]
                if full_increment:
                    escaped = full_increment.replace("\n", "\\n").replace("\r", "\\r")
                    self.handler._log_status(f"PROOF_STREAM:chunk:{escaped}", "blue")

    def test_sentence_simple(self):
        # "this is a twenty-one-year-old male with no specific complaints"
        # Simulate GPT-OSS channels with minimal reasoning and final list
        tokens = [
            "<|start|>assistant<|channel|>analysis<|message|>",
            "Brief reasoning.",
            "<|end|>",
            "<|start|>assistant<|channel|>final<|message|>",
            "- Twenty-one-year-old male presents with no specific complaints.",
            "<|end|>",
        ]
        self._simulate_stream(tokens)
        final_text = "".join(self.chunk_msgs).replace("\\n", "\n")
        self.assertIn("- Twenty-one-year-old male presents with no specific complaints.", final_text)
        # No duplication/dash fragmentation
        self.assertNotIn("A twenty-one-year", final_text)
        # No think tags
        self.assertNotIn("<think>", final_text)
        self.assertGreaterEqual(final_text.count("- "), 1)

    def test_sentence_complex(self):
        # More complex clinical note
        user_sentence = (
            "21 year old male here for annual exam notes he also has had some issues with his right ear uh "
            "itching for the last six months after he tried systemic steroids for an unrelated skin condition. "
            "No loss of hearing, discharge, vertigo, or pain, but just persistent itching which has not gotten better "
            "or worse over a six month period."
        )
        final_bullets = [
            "- Twenty-one-year-old male presents for annual exam.",
            "- Reports right ear itching for six months following systemic steroids for unrelated skin condition.",
            "- Denies hearing loss, discharge, vertigo, or pain.",
            "- Persistent itching without progression over six months.",
        ]
        tokens = [
            "<|start|>assistant<|channel|>analysis<|message|>",
            "Concise reasoning.",
            "<|end|>",
            "<|start|>assistant<|channel|>final<|message|>",
        ] + [line + "\n" for line in final_bullets] + ["<|end|>"]

        self._simulate_stream(tokens)
        final_text = "".join(self.chunk_msgs).replace("\\n", "\n")
        for bullet in final_bullets:
            self.assertIn(bullet, final_text)
        # Ensure bullets are present and formatting intact
        self.assertGreaterEqual(final_text.count("- "), 4)
        # Ensure think tags not present
        self.assertNotIn("<think>", final_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
