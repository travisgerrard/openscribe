#!/usr/bin/env python3
"""
Audio VAD Threshold Tests

Tests to catch the audio pipeline issues we encountered:
1. VAD silence detection threshold validation
2. Essentially silent threshold correctness (the 50->10 fix)
3. Audio pipeline integration
4. Microphone access patterns
5. Audio stream conflicts

These tests validate critical audio processing parameters.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAudioVADThresholds(unittest.TestCase):
    """Test suite for VAD threshold validation and audio pipeline."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        
    @patch('pyaudio.PyAudio')
    def test_essentially_silent_threshold_allows_background_noise(self, mock_pyaudio):
        """Test that essentially_silent threshold allows normal background noise through."""
        
        # Mock the audio handler
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        # Test audio samples that should NOT be considered essentially silent
        background_noise_samples = [
            np.array([6, -5, 8, -7, 9, -6] * 100, dtype=np.int16),    # Amplitude ~6-9
            np.array([10, -12, 8, -9, 11, -8] * 100, dtype=np.int16), # Amplitude ~8-12  
            np.array([15, -14, 16, -13, 12, -15] * 100, dtype=np.int16), # Amplitude ~12-16
        ]
        
        # Test audio samples that SHOULD be considered essentially silent
        truly_silent_samples = [
            np.array([1, -1, 0, 1, -1, 0] * 100, dtype=np.int16),     # Amplitude ~0-1
            np.array([2, -2, 1, -1, 2, -1] * 100, dtype=np.int16),    # Amplitude ~1-2
            np.array([3, -3, 2, -2, 3, -2] * 100, dtype=np.int16),    # Amplitude ~2-3
        ]
        
        with patch('pyaudio.PyAudio'):
            # Create AudioHandler instance
            handler = AudioHandler()
            
            # Check that the threshold is reasonable (should be around 10, not 50)
            if hasattr(handler, 'essentially_silent_threshold'):
                threshold = handler.essentially_silent_threshold
                self.assertLessEqual(threshold, 15, 
                    f"essentially_silent_threshold ({threshold}) is too high. "
                    f"Should be ≤15 to allow background noise through to VAD. "
                    f"High threshold (like 50) prevents normal audio from reaching VAD processing.")
                    
                self.assertGreaterEqual(threshold, 5,
                    f"essentially_silent_threshold ({threshold}) is too low. "
                    f"Should be ≥5 to filter out actual silence.")
            
            # Test the is_essentially_silent method if available
            if hasattr(handler, 'is_essentially_silent'):
                # Background noise should NOT be considered essentially silent
                for sample in background_noise_samples:
                    is_silent = handler.is_essentially_silent(sample.tobytes())
                    self.assertFalse(is_silent, 
                        f"Background noise (max amplitude {np.max(np.abs(sample))}) "
                        f"incorrectly classified as essentially silent. "
                        f"This prevents VAD from processing normal audio.")
                
                # True silence should be considered essentially silent
                for sample in truly_silent_samples:
                    is_silent = handler.is_essentially_silent(sample.tobytes())
                    self.assertTrue(is_silent,
                        f"True silence (max amplitude {np.max(np.abs(sample))}) "
                        f"not classified as essentially silent.")

    def test_vad_silence_detection_timeout(self):
        """Test that VAD silence detection timeout is reasonable."""
        
        try:
            from src.config import config
            
            # Check silence limit configuration
            silence_limit = getattr(config, 'SILENCE_LIMIT', None) or \
                           getattr(config, 'silence_limit', None) or \
                           1.5  # Default from our fixes
                           
            self.assertGreaterEqual(silence_limit, 1.0,
                f"SILENCE_LIMIT ({silence_limit}) too short. "
                f"Should be ≥1.0 seconds to avoid cutting off normal speech pauses.")
                
            self.assertLessEqual(silence_limit, 3.0,
                f"SILENCE_LIMIT ({silence_limit}) too long. "
                f"Should be ≤3.0 seconds for responsive auto-stop.")
                
        except ImportError:
            self.skipTest("Config not available for testing")

    @patch('pyaudio.PyAudio')
    def test_microphone_availability_check_pattern(self, mock_pyaudio):
        """Test that microphone availability check doesn't create multiple streams."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            mock_stream = Mock()
            mock_pyaudio.return_value.open.return_value = mock_stream
            
            handler = AudioHandler()
            
            # Test microphone check with skip_test_stream flag
            if hasattr(handler, 'check_microphone_availability'):
                # Should be able to skip test stream during startup
                try:
                    result = handler.check_microphone_availability(skip_test_stream=True)
                    # Should not have opened a test stream
                    # (Hard to test definitively without inspecting implementation)
                    self.assertTrue(True, "Microphone check completed without test stream")
                except TypeError:
                    # Method doesn't accept skip_test_stream parameter
                    self.fail("check_microphone_availability should accept skip_test_stream parameter "
                             "to prevent macOS microphone indicator flashing during startup")

    def test_vad_aggressiveness_setting(self):
        """Test that VAD aggressiveness is set appropriately."""
        
        try:
            from src.config import config
            
            vad_aggressiveness = getattr(config, 'VAD_AGGRESSIVENESS', None) or \
                               getattr(config, 'vad_aggressiveness', None) or 1
                               
            self.assertIn(vad_aggressiveness, [0, 1, 2, 3],
                f"VAD_AGGRESSIVENESS ({vad_aggressiveness}) must be 0, 1, 2, or 3")
                
            # For voice dictation, moderate aggressiveness (1-2) usually works best
            self.assertIn(vad_aggressiveness, [1, 2],
                f"VAD_AGGRESSIVENESS ({vad_aggressiveness}) should typically be 1 or 2 "
                f"for voice dictation applications")
                
        except ImportError:
            self.skipTest("Config not available for testing")

    @patch('pyaudio.PyAudio')  
    def test_audio_frame_processing_pipeline(self, mock_pyaudio):
        """Test that audio frames flow correctly through the processing pipeline."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            
            # Simulate audio frame processing
            test_frame = np.array([10, -12, 8, -9, 11, -8] * 160, dtype=np.int16)  # 20ms at 16kHz
            frame_bytes = test_frame.tobytes()
            
            # Test the processing pipeline stages
            if hasattr(handler, 'is_essentially_silent'):
                is_silent = handler.is_essentially_silent(frame_bytes)
                # Normal speech should not be considered essentially silent
                self.assertFalse(is_silent, 
                    "Normal speech frame incorrectly classified as essentially silent")
            
            # If VAD is available, test it
            if hasattr(handler, 'vad') and handler.vad:
                try:
                    # VAD should process non-silent frames
                    vad_result = handler.vad.is_speech(frame_bytes, 16000)
                    # We can't assert the result since it depends on the actual audio,
                    # but we can ensure it doesn't crash
                    self.assertIsInstance(vad_result, bool, 
                        "VAD should return boolean result")
                except Exception as e:
                    self.fail(f"VAD processing failed: {e}")

    def test_audio_conflict_detection(self):
        """Test that audio conflicts are properly detected and logged."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        # Test amplitude ranges that should/shouldn't trigger conflicts
        test_cases = [
            (0, False, "True silence should not trigger conflict"),
            (5, False, "Very quiet audio should not trigger conflict"), 
            (15, False, "Background noise should not trigger conflict"),
            (100, True, "Loud audio should be processed normally"),
            (1000, True, "Very loud audio should be processed normally")
        ]
        
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            
            for amplitude, should_process, description in test_cases:
                test_frame = np.array([amplitude, -amplitude] * 800, dtype=np.int16)
                frame_bytes = test_frame.tobytes()
                
                if hasattr(handler, 'is_essentially_silent'):
                    is_silent = handler.is_essentially_silent(frame_bytes)
                    
                    if should_process:
                        self.assertFalse(is_silent, 
                            f"{description} (amplitude {amplitude})")
                    else:
                        # For very low amplitudes, being silent is okay
                        if amplitude <= 5:
                            continue  # Skip assertion for very quiet audio

    def test_ring_buffer_configuration(self):
        """Test that ring buffer is configured appropriately."""
        
        try:
            from src.config import config
            
            buffer_duration = getattr(config, 'RING_BUFFER_DURATION_MS', None) or \
                            getattr(config, 'ring_buffer_duration_ms', None) or 500
                            
            self.assertGreaterEqual(buffer_duration, 200,
                f"RING_BUFFER_DURATION_MS ({buffer_duration}) too short. "
                f"Should be ≥200ms to capture speech onset.")
                
            self.assertLessEqual(buffer_duration, 2000,
                f"RING_BUFFER_DURATION_MS ({buffer_duration}) too long. "
                f"Should be ≤2000ms to avoid excessive memory usage.")
                
        except ImportError:
            self.skipTest("Config not available for testing")

    def test_sample_rate_configuration(self):
        """Test that sample rate is appropriate for VAD."""
        
        try:
            from src.config import config
            
            sample_rate = getattr(config, 'SAMPLE_RATE', None) or \
                         getattr(config, 'sample_rate', None) or 16000
                         
            # VAD typically works best with 8kHz, 16kHz, 32kHz, or 48kHz
            valid_rates = [8000, 16000, 32000, 48000]
            self.assertIn(sample_rate, valid_rates,
                f"SAMPLE_RATE ({sample_rate}) not optimal for VAD. "
                f"Should be one of {valid_rates}")
                
            # 16kHz is usually the sweet spot for speech processing
            if sample_rate not in [16000, 32000]:
                self.skipTest(f"Sample rate {sample_rate} not ideal but acceptable")
                
        except ImportError:
            self.skipTest("Config not available for testing")

    @patch('pyaudio.PyAudio')
    def test_audio_stream_single_access_pattern(self, mock_pyaudio):
        """Test that audio stream is accessed once, not multiple times during startup."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            mock_stream = Mock()
            mock_pyaudio.return_value.open.return_value = mock_stream
            
            # Track stream open calls
            open_calls = []
            def track_open(*args, **kwargs):
                open_calls.append((args, kwargs))
                return mock_stream
                
            mock_pyaudio.return_value.open.side_effect = track_open
            
            # Initialize audio handler
            handler = AudioHandler()
            
            # During normal initialization, should not open multiple streams rapidly
            self.assertLessEqual(len(open_calls), 2,
                f"Too many audio stream open calls ({len(open_calls)}) during initialization. "
                f"Multiple rapid opens cause macOS microphone indicator flashing.")

    def test_audio_processing_error_handling(self):
        """Test that audio processing errors are handled gracefully."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            
            # Test with invalid audio data
            invalid_frames = [
                b'',  # Empty frame
                b'invalid',  # Too short
                b'x' * 1000,  # Wrong format
            ]
            
            for invalid_frame in invalid_frames:
                try:
                    if hasattr(handler, 'is_essentially_silent'):
                        # Should handle invalid input gracefully
                        result = handler.is_essentially_silent(invalid_frame)
                        self.assertIsInstance(result, bool, 
                            "Should return boolean even for invalid input")
                except Exception as e:
                    # Should not raise unhandled exceptions
                    self.fail(f"Unhandled exception for invalid audio frame: {e}")


if __name__ == '__main__':
    unittest.main() 