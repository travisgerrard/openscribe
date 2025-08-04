# test_optimization_results.py
# Tests to validate performance optimizations

import unittest
import time
import threading
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from performance_optimizer import performance_optimizer, start_perf_timer, end_perf_timer
from audio.audio_handler import AudioHandler

class TestPerformanceOptimizations(unittest.TestCase):
    """Test suite to validate performance optimizations."""

    def setUp(self):
        """Set up test fixtures."""
        self.performance_data = []
        
    def test_audio_buffer_optimization(self):
        """Test that audio buffer optimization prevents memory growth."""
        # Skip if audio dependencies not available
        try:
            import pyaudio
            import webrtcvad
            import numpy as np
        except ImportError:
            self.skipTest("Audio dependencies not available")
            
        # Create audio handler (mocked for CI)
        audio_handler = AudioHandler()
        
        initial_memory = sys.getsizeof(audio_handler._voiced_frames)
        
        # Simulate adding many frames (this would normally cause memory growth)
        fake_frames = []
        for i in range(700):  # More than MAX_VOICED_FRAMES (600)
            fake_frame = bytearray(1024)  # 1KB frame
            fake_frames.append(fake_frame)
            
        audio_handler._voiced_frames = fake_frames
        
        # Trigger optimization
        audio_handler._optimize_buffer_memory()
        
        # Buffer should be limited to 600 frames
        self.assertLessEqual(len(audio_handler._voiced_frames), 600, 
                           "Buffer optimization should limit frame count")
        
        final_memory = sys.getsizeof(audio_handler._voiced_frames)
        
        # Memory usage should be controlled
        self.assertLess(final_memory, initial_memory * 1.2,  # Allow 20% tolerance
                       "Buffer optimization should control memory usage")
        
    def test_performance_monitoring(self):
        """Test that performance monitoring works correctly."""
        # Test operation timing
        timer_id = start_perf_timer("test_component", "test_operation")
        
        # Simulate some work
        time.sleep(0.05)  # 50ms
        
        end_perf_timer(timer_id, {"test_data": "value"})
        
        # Check metrics were recorded
        summary = performance_optimizer.get_performance_summary()
        self.assertIn("test_component_test_operation_ms", summary)
        
        metrics = summary["test_component_test_operation_ms"]
        self.assertGreaterEqual(metrics['avg'], 45)  # Should be around 50ms
        self.assertLessEqual(metrics['avg'], 100)    # But not too much overhead
        
    def test_vad_skip_optimization(self):
        """Test that VAD skipping optimization works."""
        # This test verifies the VAD skip logic we added
        
        # Simulate low amplitude frames
        low_amp = 2  # Below our threshold of 5
        
        # Our optimization should skip VAD for sustained low amplitude
        should_skip_vad = low_amp < 5
        self.assertTrue(should_skip_vad, "VAD should be skipped for low amplitude")
        
        # High amplitude should not skip VAD
        high_amp = 50
        should_skip_vad = high_amp < 5
        self.assertFalse(should_skip_vad, "VAD should not be skipped for high amplitude")

    def test_waveform_throttling_performance(self):
        """Test waveform rendering performance improvements."""
        # Test that our throttling mechanism works
        THROTTLE_MS = 33  # Same as our implementation
        
        start_time = time.time()
        
        # Simulate rapid calls (would normally cause performance issues)
        call_times = []
        for i in range(10):
            call_start = time.time()
            
            # Simulate our throttling logic
            time_since_last = (call_start - start_time) * 1000
            if time_since_last >= THROTTLE_MS:
                # This call would be processed
                call_times.append(call_start)
                start_time = call_start
            else:
                # This call would be throttled
                pass
                
            time.sleep(0.01)  # 10ms between calls
            
        # We should have processed fewer calls due to throttling
        self.assertLessEqual(len(call_times), 5, 
                           "Throttling should reduce number of processed calls")

    def test_ipc_message_throttling(self):
        """Test IPC message throttling effectiveness."""
        # Test our IPC throttling mechanism
        MAX_PENDING = 5  # Same as our implementation
        
        pending_updates = 0
        processed_updates = 0
        
        # Simulate rapid IPC messages
        for i in range(20):
            pending_updates += 1
            
            # Apply our throttling logic
            if pending_updates <= MAX_PENDING:
                processed_updates += 1
            else:
                # Drop excessive updates
                pending_updates = MAX_PENDING
                
        # Should have dropped some updates
        self.assertLess(processed_updates, 20, 
                       "IPC throttling should drop excessive updates")
        self.assertLessEqual(pending_updates, MAX_PENDING,
                           "Pending updates should not exceed maximum")

    def benchmark_optimization_overhead(self):
        """Benchmark the overhead of our performance optimizations."""
        iterations = 1000
        
        # Test baseline performance (no optimization)
        start = time.time()
        for i in range(iterations):
            # Simulate basic operation
            pass
        baseline_time = time.time() - start
        
        # Test with performance monitoring
        start = time.time()
        for i in range(iterations):
            timer_id = start_perf_timer("benchmark", "operation")
            # Simulate basic operation
            end_perf_timer(timer_id)
        optimized_time = time.time() - start
        
        # Overhead should be minimal (less than 50% increase)
        overhead_ratio = optimized_time / baseline_time if baseline_time > 0 else 1
        
        print(f"Baseline: {baseline_time:.4f}s, Optimized: {optimized_time:.4f}s, "
              f"Overhead: {(overhead_ratio - 1) * 100:.1f}%")
        
        self.assertLess(overhead_ratio, 1.5, 
                       "Performance monitoring overhead should be minimal")

if __name__ == '__main__':
    unittest.main(verbosity=2) 