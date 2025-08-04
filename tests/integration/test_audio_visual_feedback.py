#!/usr/bin/env python3
"""
Audio Visual Feedback Tests

Tests to ensure audio amplitude feedback and waveform visualization continue
working after log cleanup. This prevents breaking the GUI components that
depend on audio amplitude data.
"""

import unittest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.visual_feedback
@pytest.mark.integration
class TestAudioVisualFeedback(unittest.TestCase):
    """Test suite for audio amplitude feedback and visual components."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        
    @patch('pyaudio.PyAudio')
    def test_audio_amplitude_messages_sent(self, mock_pyaudio):
        """Test that AUDIO_AMP messages are still sent for waveform visualization."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        # Mock status update callback to capture amplitude messages
        amplitude_messages = []
        def mock_status_update(message, color):
            if message.startswith("AUDIO_AMP:"):
                amplitude_messages.append(message)
        
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler.on_status_update = mock_status_update
            handler._listening_state = "dictation"
            
            # Create test audio frame with some amplitude
            frame_size = 480  # Standard frame size
            test_audio = np.random.randint(-500, 500, frame_size, dtype=np.int16)
            frame_bytes = test_audio.tobytes()
            
            # Process the frame
            handler._process_dictation_frame(frame_bytes)
            
            # Should have received amplitude message
            self.assertEqual(len(amplitude_messages), 1)
            self.assertTrue(amplitude_messages[0].startswith("AUDIO_AMP:"))
            
            # Extract amplitude value
            amp_value = int(amplitude_messages[0].split(":")[1])
            self.assertGreaterEqual(amp_value, 0)
            self.assertLessEqual(amp_value, 100)

    def test_frontend_amplitude_processing(self):
        """Test that frontend can process AUDIO_AMP messages."""
        
        # Read the renderer IPC file to verify amplitude processing exists
        ipc_file = self.project_root / "frontend" / "shared" / "renderer_ipc.js"
        self.assertTrue(ipc_file.exists(), "renderer_ipc.js not found")
        
        with open(ipc_file, 'r') as f:
            content = f.read()
            
        # Verify amplitude processing logic exists
        self.assertIn("AUDIO_AMP:", content)
        self.assertIn("amplitudes.push", content)
        self.assertIn("amplitudes.shift", content)
        self.assertIn("parseInt", content)

    @patch('pyaudio.PyAudio')
    def test_zero_amplitude_for_silent_frames(self, mock_pyaudio):
        """Test that silent frames generate AUDIO_AMP:0 messages."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        amplitude_messages = []
        def mock_status_update(message, color):
            if message.startswith("AUDIO_AMP:"):
                amplitude_messages.append(message)
        
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler.on_status_update = mock_status_update
            handler._listening_state = "dictation"
            
            # Create silent frame
            frame_size = 480
            silent_frame = b'\x00' * (frame_size * 2)  # All zeros
            
            # Process the silent frame
            handler._process_dictation_frame(silent_frame)
            
            # Should receive zero amplitude
            self.assertEqual(len(amplitude_messages), 1)
            self.assertEqual(amplitude_messages[0], "AUDIO_AMP:0")

    def test_main_py_amplitude_forwarding(self):
        """Test that main.py forwards AUDIO_AMP messages to frontend."""
        
        main_file = self.project_root / "main.py"
        self.assertTrue(main_file.exists(), "main.py not found")
        
        with open(main_file, 'r') as f:
            content = f.read()
            
        # Verify amplitude message forwarding exists
        self.assertIn('message.startswith("AUDIO_AMP:")', content)
        self.assertIn("print(message, flush=True)", content)

    @patch('pyaudio.PyAudio')
    def test_amplitude_calculation_accuracy(self, mock_pyaudio):
        """Test that amplitude calculation produces reasonable values."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        amplitude_messages = []
        def mock_status_update(message, color):
            if message.startswith("AUDIO_AMP:"):
                amplitude_messages.append(message)
        
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler.on_status_update = mock_status_update
            handler._listening_state = "dictation"
            
            # Test different amplitude levels
            test_cases = [
                (100, 1),    # Low amplitude should produce ~1
                (1000, 10),  # Medium amplitude should produce ~10  
                (5000, 50),  # High amplitude should produce ~50
            ]
            
            for max_val, expected_amp in test_cases:
                amplitude_messages.clear()
                
                # Create audio with specific amplitude
                frame_size = 480
                test_audio = np.array([max_val, -max_val] * (frame_size // 2), dtype=np.int16)
                frame_bytes = test_audio.tobytes()
                
                # Process the frame
                handler._process_dictation_frame(frame_bytes)
                
                # Check amplitude value
                self.assertEqual(len(amplitude_messages), 1)
                amp_value = int(amplitude_messages[0].split(":")[1])
                
                # Should be close to expected (within ±5)
                self.assertGreaterEqual(amp_value, expected_amp - 5)
                self.assertLessEqual(amp_value, expected_amp + 5)

    def test_silence_detection_functionality_preserved(self):
        """Test that silence detection still works without verbose debug logs."""
        
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler._listening_state = "dictation"
            handler._triggered = True  # Simulate active recording
            
            # Mock the audio processing callback
            processing_called = []
            original_request = handler._request_audio_processing
            def mock_request():
                processing_called.append(True)
                # Don't call original to avoid side effects
                
            handler._request_audio_processing = mock_request
            
            # Create frames with low but non-zero amplitude (to bypass essentially_silent check)
            frame_size = 480
            low_audio = np.array([15, -15] * (frame_size // 2), dtype=np.int16)  # Low but detectable
            frame_bytes = low_audio.tobytes()
            
            # Mock VAD to return False (no speech)
            with patch.object(handler, '_vad') as mock_vad:
                mock_vad.is_speech.return_value = False
                
                # Mock config.SILENCE_THRESHOLD_SECONDS
                with patch('src.config.config.SILENCE_THRESHOLD_SECONDS', 0.1):
                    # Process frames to start silence timer
                    handler._process_dictation_frame(frame_bytes)
                    self.assertIsNotNone(handler._silence_start_time)
                    
                    # Wait a bit and process another frame to trigger timeout
                    time.sleep(0.15)
                    handler._process_dictation_frame(frame_bytes)
                    
                    # Should have triggered audio processing
                    self.assertTrue(len(processing_called) > 0)

    def test_low_amplitude_audio_reaches_vad(self):
        """Test that low-amplitude audio (amplitude 10-50) reaches VAD processing.
        
        This test specifically prevents regression of the bug where is_essentially_silent
        was blocking VAD processing for normal low-amplitude audio.
        """
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler._listening_state = "dictation"
            
            # Track VAD calls to ensure it's being called for low-amplitude audio
            vad_calls = []
            
            with patch.object(handler, '_vad') as mock_vad:
                def track_vad_call(frame_bytes, sample_rate):
                    vad_calls.append((frame_bytes, sample_rate))
                    return False  # Return False to simulate silence
                
                mock_vad.is_speech.side_effect = track_vad_call
                
                # Test different amplitude levels that should reach VAD
                test_amplitudes = [15, 25, 50, 100]  # All above the old threshold of 10
                
                for amplitude in test_amplitudes:
                    frame_size = 480
                    test_audio = np.array([amplitude, -amplitude] * (frame_size // 2), dtype=np.int16)
                    frame_bytes = test_audio.tobytes()
                    
                    # Reset VAD call tracking
                    vad_calls.clear()
                    
                    # Process the frame
                    handler._process_dictation_frame(frame_bytes)
                    
                    # Verify VAD was called for this amplitude
                    self.assertTrue(len(vad_calls) > 0, 
                        f"VAD should be called for amplitude {amplitude}, but was not. "
                        f"This indicates is_essentially_silent is too aggressive.")
                    
                    # Verify the correct frame was passed to VAD
                    called_frame, called_sample_rate = vad_calls[0]
                    self.assertEqual(called_frame, frame_bytes)
                    self.assertEqual(called_sample_rate, handler._sample_rate)

    def test_truly_silent_frames_skip_vad(self):
        """Test that truly silent (all-zero) frames still skip VAD processing for efficiency."""
        try:
            from src.audio.audio_handler import AudioHandler
        except ImportError:
            self.skipTest("AudioHandler not available for testing")
            
        with patch('pyaudio.PyAudio'):
            handler = AudioHandler()
            handler._listening_state = "dictation"
            
            # Track VAD calls
            vad_calls = []
            
            with patch.object(handler, '_vad') as mock_vad:
                mock_vad.is_speech.side_effect = lambda fb, sr: vad_calls.append((fb, sr)) or False
                
                # Create completely silent frame (all zeros)
                frame_size = 480
                silent_audio = np.zeros(frame_size, dtype=np.int16)
                frame_bytes = silent_audio.tobytes()
                
                # Process the frame
                handler._process_dictation_frame(frame_bytes)
                
                # Verify VAD was NOT called for all-zero frames
                self.assertEqual(len(vad_calls), 0, 
                    "VAD should NOT be called for all-zero frames for efficiency.")

    def test_frontend_waveform_canvas_exists(self):
        """Test that the waveform canvas element exists in the HTML."""
        
        index_file = self.project_root / "frontend" / "main" / "index.html"
        self.assertTrue(index_file.exists(), "index.html not found")
        
        with open(index_file, 'r') as f:
            content = f.read()
            
        # Verify waveform canvas exists
        self.assertIn("waveform-canvas", content)
        self.assertIn("<canvas", content)

    def test_waveform_rendering_components_exist(self):
        """Test that waveform rendering JavaScript components exist."""
        
        waveform_file = self.project_root / "frontend" / "shared" / "renderer_waveform.js"
        if waveform_file.exists():
            with open(waveform_file, 'r') as f:
                content = f.read()
                
            # Check for waveform rendering functions
            self.assertIn("canvas", content.lower())
            # These are likely function names or variable names related to waveform
            
    def test_electron_message_forwarding_preserved(self):
        """Test that Electron still forwards AUDIO_AMP messages to renderer after log cleanup."""
        
        electron_python_file = self.project_root / "electron_python.js"
        self.assertTrue(electron_python_file.exists(), "electron_python.js not found")
        
        with open(electron_python_file, 'r') as f:
            content = f.read()
            
        # Verify message forwarding logic still exists
        self.assertIn("mainWindow.webContents.send('from-python'", content)
        self.assertIn("forwarding", content.lower())
        
        # Verify AUDIO_AMP messages are not filtered out
        # (They should reach the renderer for waveform visualization)
        self.assertNotIn("filter.*AUDIO_AMP", content)
        self.assertNotIn("skip.*AUDIO_AMP", content)

    def test_renderer_audio_amp_handling_preserved(self):
        """Test that renderer can still handle AUDIO_AMP messages after log cleanup."""
        
        renderer_ipc_file = self.project_root / "frontend" / "shared" / "renderer_ipc.js"
        self.assertTrue(renderer_ipc_file.exists(), "renderer_ipc.js not found")
        
        with open(renderer_ipc_file, 'r') as f:
            content = f.read()
            
        # Verify AUDIO_AMP handling logic exists
        self.assertIn("AUDIO_AMP:", content)
        self.assertIn("amplitudes.push", content)
        self.assertIn("amplitudes.shift", content)

if __name__ == '__main__':
    unittest.main() 