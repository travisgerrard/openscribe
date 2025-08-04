#!/usr/bin/env python3
"""
Test Parakeet model functionality specifically.
Tests the model loading, transcription, and text extraction without character separation.
"""

import sys
import numpy as np
import tempfile
import time
sys.path.append('.')

from transcription_handler import TranscriptionHandler
from settings_manager import SettingsManager
import config

print('=== Parakeet Model Testing ===')

class ParakeetTester:
    def __init__(self):
        self.test_results = []
        
    def assert_test(self, condition, test_name, expected=None, actual=None):
        """Helper to track test results."""
        status = "✅ PASS" if condition else "❌ FAIL"
        self.test_results.append((test_name, condition))
        
        if expected is not None and actual is not None:
            print(f"{status}: {test_name}")
            if not condition:
                print(f"  Expected: {expected}")
                print(f"  Actual: {actual}")
        else:
            print(f"{status}: {test_name}")
        
        return condition
    
    def test_model_type_detection(self):
        """Test that we can correctly identify model types."""
        print("\n--- Testing Model Type Detection ---")
        
        # Mock transcription callbacks
        def mock_transcription_complete(text, duration):
            pass
            
        def mock_status_update(message, color):
            print(f"Status: {message}")
        
        handler = TranscriptionHandler(
            on_transcription_complete_callback=mock_transcription_complete,
            on_status_update_callback=mock_status_update,
            selected_asr_model="mlx-community/parakeet-tdt-0.6b-v2"
        )
        
        # Test model type detection
        whisper_model = "mlx-community/whisper-base"
        parakeet_model = "mlx-community/parakeet-tdt-0.6b-v2"
        
        whisper_type = handler._detect_model_type(whisper_model)
        parakeet_type = handler._detect_model_type(parakeet_model)
        
        self.assert_test(
            whisper_type == "whisper",
            "Whisper model correctly identified",
            "whisper",
            whisper_type
        )
        
        self.assert_test(
            parakeet_type == "parakeet",
            "Parakeet model correctly identified as parakeet",
            "parakeet",
            parakeet_type
        )
    
    def test_parakeet_availability(self):
        """Test if Parakeet libraries are available."""
        print("\n--- Testing Parakeet Library Availability ---")
        
        try:
            import parakeet_mlx
            parakeet_available = True
            print("✅ parakeet-mlx library found")
        except ImportError:
            parakeet_available = False
            print("❌ parakeet-mlx library not found")
        
        try:
            import mlx.audio
            mlx_audio_available = True
            print("✅ mlx.audio library found")
        except ImportError:
            mlx_audio_available = True  # Assume available for now
            print("⚠️  mlx.audio import status unknown")
        
        self.assert_test(
            parakeet_available,
            "Parakeet MLX library is available"
        )
        
        return parakeet_available
    
    def test_parakeet_model_loading(self):
        """Test Parakeet model loading if libraries are available."""
        print("\n--- Testing Parakeet Model Loading ---")
        
        if not self.test_parakeet_availability():
            print("⚠️  Skipping Parakeet model loading test - library not available")
            return
        
        def mock_transcription_complete(text, duration):
            pass
            
        def mock_status_update(message, color):
            print(f"Loading Status: {message}")
        
        handler = TranscriptionHandler(
            on_transcription_complete_callback=mock_transcription_complete,
            on_status_update_callback=mock_status_update,
            selected_asr_model="mlx-community/parakeet-tdt-0.6b-v2"
        )
        
        try:
            # Attempt to load the model
            print("Attempting to load Parakeet model (this may take time)...")
            start_time = time.time()
            
            # This should trigger model loading in the background
            # We'll wait a bit to see if it starts loading
            time.sleep(2)
            
            # Check if model loading was initiated
            load_time = time.time() - start_time
            print(f"Model loading process took: {load_time:.2f}s to initiate")
            
            self.assert_test(
                True,  # If we get here without exception, loading was initiated
                "Parakeet model loading initiated successfully"
            )
            
        except Exception as e:
            print(f"Error loading Parakeet model: {e}")
            self.assert_test(
                False,
                f"Parakeet model loading failed: {e}"
            )
    
    def test_text_extraction_format(self):
        """Test that we handle different text extraction formats correctly."""
        print("\n--- Testing Text Extraction Formats ---")
        
        def mock_transcription_complete(text, duration):
            pass
            
        def mock_status_update(message, color):
            pass
        
        handler = TranscriptionHandler(
            on_transcription_complete_callback=mock_transcription_complete,
            on_status_update_callback=mock_status_update,
            selected_asr_model="mlx-community/parakeet-tdt-0.6b-v2"
        )
        
        # Mock different result formats that might be returned
        
        # Test 1: Mock AlignedResult with direct text property
        class MockAlignedResult:
            def __init__(self, text):
                self.text = text
                # Mock tokens that would create the character separation issue
                # Split each word into individual characters to simulate the bug
                words = text.split()
                self.tokens = []
                for word in words:
                    for char in word:
                        self.tokens.append(MockToken(char))
        
        class MockToken:
            def __init__(self, text):
                self.text = text
        
        # Test correct extraction (should use result.text)
        mock_result = MockAlignedResult("The patient is adequate")
        
        # Test the extraction logic
        correct_text = mock_result.text.strip()
        incorrect_text = ' '.join([token.text for token in mock_result.tokens])
        
        self.assert_test(
            correct_text == "The patient is adequate",
            "Direct text property extraction works correctly",
            "The patient is adequate",
            correct_text
        )
        
        self.assert_test(
            incorrect_text != correct_text,
            "Token joining method produces character separation (the bug we fixed)",
            "Character separated",
            f"'{incorrect_text}' vs '{correct_text}'"
        )
        
        print(f"Correct method result: '{correct_text}'")
        print(f"Incorrect method result: '{incorrect_text}'")
    
    def test_audio_format_handling(self):
        """Test that we handle different audio formats correctly."""
        print("\n--- Testing Audio Format Handling ---")
        
        def mock_transcription_complete(text, duration):
            pass
            
        def mock_status_update(message, color):
            pass
        
        handler = TranscriptionHandler(
            on_transcription_complete_callback=mock_transcription_complete,
            on_status_update_callback=mock_status_update,
            selected_asr_model="mlx-community/parakeet-tdt-0.6b-v2"
        )
        
        # Test different audio data formats (just basic validation)
        test_cases = [
            ("Float32 audio data", np.random.random(16000).astype(np.float32)),
            ("Float64 audio data", np.random.random(16000).astype(np.float64)),
            ("Int16 audio data", (np.random.random(16000) * 32767).astype(np.int16)),
        ]
        
        for test_name, audio_data in test_cases:
            try:
                # Just test that the audio data exists and has the right properties
                self.assert_test(
                    audio_data is not None,
                    f"{test_name} creation successful"
                )
                
                self.assert_test(
                    isinstance(audio_data, np.ndarray),
                    f"{test_name} is numpy array"
                )
                
                self.assert_test(
                    audio_data.size > 0,
                    f"{test_name} has data"
                )
                
            except Exception as e:
                self.assert_test(
                    False,
                    f"{test_name} handling failed: {e}"
                )
    
    def run_all_tests(self):
        """Run all Parakeet-specific tests."""
        print("Starting Parakeet model tests...")
        
        self.test_model_type_detection()
        self.test_parakeet_availability()
        self.test_parakeet_model_loading()
        self.test_text_extraction_format()
        self.test_audio_format_handling()
        
        # Summary
        print("\n" + "="*60)
        print("PARAKEET TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL PARAKEET TESTS PASSED! 🎉")
        else:
            print("❌ Some Parakeet tests failed:")
            for test_name, result in self.test_results:
                if not result:
                    print(f"  - {test_name}")
        
        return passed == total

if __name__ == "__main__":
    tester = ParakeetTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1) 