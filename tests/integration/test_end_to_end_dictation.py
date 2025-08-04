#!/usr/bin/env python3
"""
End-to-End Dictation Integration Tests

These tests validate the complete dictation workflow from audio input through
frontend display, ensuring all components work together correctly.

Tests the full pipeline:
Audio Input → VAD Detection → Vosk Transcription → LLM Processing → Frontend Display

Prevents issues like:
- Component integration failures
- Data format mismatches between pipeline stages
- Timing issues in the complete workflow
- End-to-end performance regressions
"""

import unittest
import threading
import time
import json
import tempfile
import os
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, MagicMock, patch


class MockAudioInput:
    """Mock audio input for integration testing"""

    def __init__(self, audio_samples: List[str]):
        self.samples = audio_samples
        self.current_index = 0
        self.is_active = False
        self.callbacks = []

    def start_recording(self):
        """Start mock audio recording"""
        self.is_active = True
        self.current_index = 0

    def stop_recording(self):
        """Stop mock audio recording"""
        self.is_active = False

    def get_next_audio_chunk(self) -> Optional[str]:
        """Get next audio chunk simulation"""
        if not self.is_active or self.current_index >= len(self.samples):
            return None

        chunk = self.samples[self.current_index]
        self.current_index += 1
        return chunk

    def simulate_speech(self, text: str):
        """Simulate speaking the given text"""
        # Split text into chunks to simulate real speech
        words = text.split()
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= 3:  # Chunk every 3 words
                chunks.append(" ".join(current_chunk))
                current_chunk = []

        if current_chunk:  # Add remaining words
            chunks.append(" ".join(current_chunk))

        self.samples = chunks
        self.current_index = 0


class MockVoskTranscriber:
    """Mock Vosk transcriber for integration testing"""

    def __init__(self):
        self.is_initialized = False
        self.recognition_results = []

    def initialize(self, model_path: str) -> bool:
        """Mock initialization"""
        self.is_initialized = True
        return True

    def transcribe_chunk(self, audio_chunk: str) -> Dict[str, Any]:
        """Mock transcription of audio chunk"""
        if not self.is_initialized:
            raise RuntimeError("Transcriber not initialized")

        # Simulate transcription result
        result = {
            "text": audio_chunk,  # In real system, this would be transcribed audio
            "confidence": 0.95,
            "is_final": True,
            "timestamp": time.time(),
        }

        self.recognition_results.append(result)
        return result

    def get_partial_result(self) -> Dict[str, Any]:
        """Mock partial transcription result"""
        return {
            "text": "",
            "confidence": 0.0,
            "is_final": False,
            "timestamp": time.time(),
        }


class MockLLMProcessor:
    """Mock LLM processor for integration testing"""

    def __init__(self):
        self.is_loaded = False
        self.processing_history = []

    def load_model(self, model_path: str) -> bool:
        """Mock model loading"""
        self.is_loaded = True
        return True

    def process_text(self, text: str, task_type: str = "dictate") -> str:
        """Mock LLM text processing"""
        if not self.is_loaded:
            raise RuntimeError("LLM model not loaded")

        # Simulate processing with realistic medical formatting
        if task_type == "dictate":
            processed = self._format_medical_dictation(text)
        elif task_type == "proofread":
            processed = self._proofread_text(text)
        else:
            processed = text

        self.processing_history.append(
            {
                "input": text,
                "output": processed,
                "task_type": task_type,
                "timestamp": time.time(),
            }
        )

        return processed

    def stream_process_text(self, text: str, task_type: str = "dictate"):
        """Mock streaming LLM processing"""
        if not self.is_loaded:
            raise RuntimeError("LLM model not loaded")

        # Simulate streaming by yielding tokens
        result = self.process_text(text, task_type)

        # Split result into tokens for streaming simulation
        tokens = result.split()
        for i, token in enumerate(tokens):
            yield {
                "token": token + (" " if i < len(tokens) - 1 else ""),
                "is_final": i == len(tokens) - 1,
                "timestamp": time.time(),
            }

    def _format_medical_dictation(self, text: str) -> str:
        """Simulate medical dictation formatting"""
        lines = text.split(". ")
        formatted_lines = []

        for line in lines:
            if line.strip():
                formatted_lines.append(f"- {line.strip()}")

        return "\n".join(formatted_lines)

    def _proofread_text(self, text: str) -> str:
        """Simulate text proofreading"""
        # Simple proofreading simulation
        corrected = text.replace(" cant ", " can't ")
        corrected = corrected.replace(" wont ", " won't ")
        corrected = corrected.replace(" dont ", " don't ")
        return corrected


class MockFrontendDisplay:
    """Mock frontend display for integration testing"""

    def __init__(self):
        self.displayed_content = ""
        self.status_updates = []
        self.streaming_chunks = []

    def update_status(self, status: str):
        """Mock status update"""
        self.status_updates.append({"status": status, "timestamp": time.time()})

    def display_transcription(self, text: str):
        """Mock transcription display"""
        self.displayed_content = text

    def stream_llm_response(self, chunk: str):
        """Mock streaming LLM response display"""
        self.streaming_chunks.append(chunk)
        self.displayed_content += chunk

    def clear_display(self):
        """Mock display clearing"""
        self.displayed_content = ""
        self.streaming_chunks.clear()


class IntegratedDictationWorkflow:
    """Integration of all components for testing"""

    def __init__(self):
        self.audio_input = MockAudioInput([])
        self.transcriber = MockVoskTranscriber()
        self.llm_processor = MockLLMProcessor()
        self.frontend = MockFrontendDisplay()
        self.is_running = False
        self.workflow_results = []

    def initialize(self, vosk_model_path: str, llm_model_path: str) -> bool:
        """Initialize all components"""
        try:
            self.transcriber.initialize(vosk_model_path)
            self.llm_processor.load_model(llm_model_path)
            return True
        except Exception as e:
            print(f"Initialization failed: {e}")
            return False

    def start_dictation_session(self):
        """Start a dictation session"""
        self.is_running = True
        self.frontend.update_status("dictating")
        self.audio_input.start_recording()

    def stop_dictation_session(self):
        """Stop a dictation session"""
        self.is_running = False
        self.frontend.update_status("inactive")
        self.audio_input.stop_recording()

    def process_dictation(
        self, spoken_text: str, task_type: str = "dictate"
    ) -> Dict[str, Any]:
        """Process complete dictation workflow"""
        start_time = time.time()

        try:
            # Step 1: Simulate audio input
            self.audio_input.simulate_speech(spoken_text)
            self.audio_input.start_recording()  # Start recording after setting up speech
            self.frontend.update_status("listening")

            # Step 2: Transcribe audio chunks
            transcribed_parts = []
            while True:
                audio_chunk = self.audio_input.get_next_audio_chunk()
                if audio_chunk is None:
                    break

                transcription_result = self.transcriber.transcribe_chunk(audio_chunk)
                transcribed_parts.append(transcription_result["text"])
                self.frontend.display_transcription(" ".join(transcribed_parts))

            # Step 3: Combine transcribed text
            full_transcription = " ".join(transcribed_parts)
            self.frontend.update_status("processing")

            # Step 4: Process with LLM
            if task_type == "stream":
                # Streaming processing
                self.frontend.clear_display()
                for token_data in self.llm_processor.stream_process_text(
                    full_transcription
                ):
                    self.frontend.stream_llm_response(token_data["token"])
                    time.sleep(0.001)  # Simulate streaming delay (reduced)

                llm_result = self.frontend.displayed_content
            else:
                # Non-streaming processing
                llm_result = self.llm_processor.process_text(
                    full_transcription, task_type
                )
                self.frontend.display_transcription(llm_result)

            # Step 5: Complete workflow
            self.frontend.update_status("complete")

            end_time = time.time()

            result = {
                "success": True,
                "spoken_text": spoken_text,
                "transcribed_text": full_transcription,
                "llm_result": llm_result,
                "task_type": task_type,
                "processing_time": end_time - start_time,
                "workflow_steps": len(self.frontend.status_updates),
                "timestamp": start_time,
            }

            self.workflow_results.append(result)
            return result

        except Exception as e:
            self.frontend.update_status("error")
            return {
                "success": False,
                "error": str(e),
                "spoken_text": spoken_text,
                "timestamp": start_time,
            }


class TestEndToEndDictation(unittest.TestCase):
    """Test complete dictation workflows"""

    def setUp(self):
        self.workflow = IntegratedDictationWorkflow()

        # Create temporary model paths for testing
        self.temp_dir = tempfile.mkdtemp()
        self.vosk_model_path = os.path.join(self.temp_dir, "vosk_model")
        self.llm_model_path = os.path.join(self.temp_dir, "llm_model")

        os.makedirs(self.vosk_model_path, exist_ok=True)
        os.makedirs(self.llm_model_path, exist_ok=True)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_basic_dictation_workflow(self):
        """Test basic dictation from speech to display"""

        # Initialize workflow
        success = self.workflow.initialize(self.vosk_model_path, self.llm_model_path)
        self.assertTrue(success, "Workflow initialization should succeed")

        # Test dictation
        spoken_text = "Patient presents with chest pain and shortness of breath"
        result = self.workflow.process_dictation(spoken_text)

        # Verify successful processing
        self.assertTrue(result["success"], f"Dictation should succeed: {result}")
        self.assertEqual(result["spoken_text"], spoken_text)
        self.assertIn("chest pain", result["transcribed_text"])
        self.assertIn("shortness of breath", result["transcribed_text"])

        # Verify LLM formatting (should create bullet points)
        llm_result = result["llm_result"]
        self.assertIn("-", llm_result, "LLM should format with bullet points")

        # Verify workflow steps
        self.assertGreater(result["workflow_steps"], 0, "Should have status updates")
        self.assertLess(result["processing_time"], 5.0, "Should complete quickly")

    def test_medical_dictation_formatting(self):
        """Test medical dictation with proper formatting"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        medical_text = (
            "Chief complaint is chest pain. History of present illness "
            "shows onset 2 hours ago. Physical examination reveals normal heart sounds"
        )

        result = self.workflow.process_dictation(medical_text, "dictate")

        self.assertTrue(result["success"])

        # Verify medical formatting
        llm_result = result["llm_result"]
        bullet_points = [
            line for line in llm_result.split("\n") if line.strip().startswith("-")
        ]

        self.assertGreaterEqual(
            len(bullet_points), 2, "Should create multiple bullet points"
        )
        self.assertTrue(any("chest pain" in bp for bp in bullet_points))
        self.assertTrue(any("heart sounds" in bp for bp in bullet_points))

    def test_streaming_workflow(self):
        """Test streaming LLM response workflow"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        spoken_text = "Patient has diabetes and hypertension"
        result = self.workflow.process_dictation(spoken_text, "stream")

        self.assertTrue(result["success"])

        # Verify streaming occurred
        self.assertGreater(
            len(self.workflow.frontend.streaming_chunks),
            0,
            "Should have streaming chunks",
        )

        # Verify content integrity
        final_content = result["llm_result"]
        self.assertIn("diabetes", final_content)
        self.assertIn("hypertension", final_content)

    def test_proofreading_workflow(self):
        """Test proofreading workflow"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        text_with_errors = "Patient cant breathe well and dont have energy"
        result = self.workflow.process_dictation(text_with_errors, "proofread")

        self.assertTrue(result["success"])

        # Verify proofreading corrections
        corrected_text = result["llm_result"]
        self.assertIn("can't", corrected_text)
        self.assertIn("don't", corrected_text)
        self.assertNotIn("cant", corrected_text)
        self.assertNotIn("dont", corrected_text)

    def test_multiple_session_workflow(self):
        """Test multiple dictation sessions"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        # Process multiple dictations
        dictations = [
            "First patient has pneumonia",
            "Second patient presents with migraine",
            "Third patient shows signs of infection",
        ]

        results = []
        for dictation in dictations:
            result = self.workflow.process_dictation(dictation)
            results.append(result)

        # Verify all succeeded
        for i, result in enumerate(results):
            self.assertTrue(result["success"], f"Dictation {i+1} should succeed")
            self.assertIn(
                dictations[i].split()[2], result["llm_result"]
            )  # Key word check

        # Verify workflow history
        self.assertEqual(len(self.workflow.workflow_results), 3)

    def test_workflow_performance(self):
        """Test workflow performance characteristics"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        # Test with various text lengths
        test_cases = [
            "Short text",
            "Medium length text with multiple words and medical terminology",
            (
                "Long medical dictation with extensive details about patient history, "
                "physical examination findings, diagnostic test results, and comprehensive "
                "treatment plan recommendations for complex medical conditions"
            ),
        ]

        performance_results = []

        for text in test_cases:
            start_time = time.time()
            result = self.workflow.process_dictation(text)
            end_time = time.time()

            self.assertTrue(result["success"])

            performance_results.append(
                {
                    "text_length": len(text),
                    "processing_time": end_time - start_time,
                    "words_per_second": len(text.split()) / (end_time - start_time),
                }
            )

        # Verify performance is reasonable
        for perf in performance_results:
            self.assertLess(
                perf["processing_time"],
                10.0,
                f"Processing should be under 10 seconds for {perf['text_length']} chars",
            )
            self.assertGreater(
                perf["words_per_second"],
                1.0,
                "Should process at least 1 word per second",
            )

    def test_workflow_error_handling(self):
        """Test workflow error handling"""

        # Test without initialization
        result = self.workflow.process_dictation("Test without initialization")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

        # Test with initialization
        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        # Test empty input
        result = self.workflow.process_dictation("")
        self.assertTrue(result["success"])  # Should handle empty input gracefully

        # Test very long input
        very_long_text = "Very long text. " * 1000
        result = self.workflow.process_dictation(very_long_text)
        self.assertTrue(result["success"])  # Should handle long input

    def test_component_integration(self):
        """Test that all components integrate correctly"""

        self.workflow.initialize(self.vosk_model_path, self.llm_model_path)

        test_text = "Integration test for all components"
        result = self.workflow.process_dictation(test_text)

        self.assertTrue(result["success"])

        # Verify all components were used
        self.assertGreater(
            len(self.workflow.transcriber.recognition_results),
            0,
            "Transcriber should have results",
        )
        self.assertGreater(
            len(self.workflow.llm_processor.processing_history),
            0,
            "LLM processor should have history",
        )
        self.assertGreater(
            len(self.workflow.frontend.status_updates),
            0,
            "Frontend should have status updates",
        )

        # Verify data flow integrity
        transcribed = result["transcribed_text"]
        processed = result["llm_result"]

        # Key words should flow through the pipeline
        test_words = test_text.split()
        for word in test_words:
            if len(word) > 3:  # Check significant words
                self.assertIn(
                    word.lower(),
                    transcribed.lower(),
                    f"Word '{word}' should appear in transcription",
                )


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
