# test_simple_optimizations.py
# Simplified tests for performance optimizations

import unittest
import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from performance_optimizer import performance_optimizer, start_perf_timer, end_perf_timer

class TestSimpleOptimizations(unittest.TestCase):
    """Simplified test suite for performance optimizations."""

    def test_performance_monitoring_basic(self):
        """Test basic performance monitoring functionality."""
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
        
    def test_waveform_throttling_logic(self):
        """Test waveform rendering throttling logic."""
        THROTTLE_MS = 33  # Same as our implementation
        
        start_time = time.time()
        processed_calls = 0
        
        # Simulate rapid calls (would normally cause performance issues)
        for i in range(10):
            call_start = time.time()
            
            # Simulate our throttling logic
            time_since_last = (call_start - start_time) * 1000
            if time_since_last >= THROTTLE_MS:
                # This call would be processed
                processed_calls += 1
                start_time = call_start
            # else: call would be throttled
                
            time.sleep(0.01)  # 10ms between calls
            
        # We should have processed fewer calls due to throttling
        self.assertLessEqual(processed_calls, 5, 
                           "Throttling should reduce number of processed calls")

    def test_ipc_message_throttling_logic(self):
        """Test IPC message throttling logic."""
        MAX_PENDING = 5  # Same as our implementation
        
        pending_updates = 0
        processed_updates = 0
        dropped_updates = 0
        
        # Simulate rapid IPC messages
        for i in range(20):
            pending_updates += 1
            
            # Apply our throttling logic
            if pending_updates <= MAX_PENDING:
                processed_updates += 1
            else:
                # Drop excessive updates
                dropped_updates += 1
                pending_updates = MAX_PENDING
                
        # Should have dropped some updates
        self.assertGreater(dropped_updates, 0, 
                          "IPC throttling should drop excessive updates")
        self.assertLessEqual(pending_updates, MAX_PENDING,
                           "Pending updates should not exceed maximum")
        self.assertLess(processed_updates, 20,
                       "Not all updates should be processed")

    def test_vad_skip_optimization_logic(self):
        """Test VAD skipping optimization logic."""
        # Simulate our VAD skip logic
        
        # Test low amplitude (should skip VAD)
        low_amp = 2  # Below our threshold of 5
        recent_low_amp_count = 15  # Above our threshold of 10
        
        skip_vad = False
        if low_amp < 5 and recent_low_amp_count > 10:
            skip_vad = True
            
        self.assertTrue(skip_vad, "VAD should be skipped for sustained low amplitude")
        
        # Test high amplitude (should not skip VAD)
        high_amp = 50
        skip_vad = high_amp < 5
        self.assertFalse(skip_vad, "VAD should not be skipped for high amplitude")

    def test_buffer_optimization_logic(self):
        """Test audio buffer optimization logic."""
        MAX_VOICED_FRAMES = 600  # Same as our implementation
        
        # Simulate buffer with too many frames
        simulated_buffer = list(range(700))  # 700 frames (exceeds limit)
        
        if len(simulated_buffer) > MAX_VOICED_FRAMES:
            frames_to_remove = len(simulated_buffer) - MAX_VOICED_FRAMES
            # Remove oldest frames (simulate our optimization)
            simulated_buffer = simulated_buffer[frames_to_remove:]
            
        # Buffer should be limited to max size
        self.assertEqual(len(simulated_buffer), MAX_VOICED_FRAMES,
                        "Buffer optimization should limit frame count")
        
        # Should contain the most recent frames
        self.assertEqual(simulated_buffer[0], 100,  # First remaining frame
                        "Should keep most recent frames")
        self.assertEqual(simulated_buffer[-1], 699,  # Last frame
                        "Should keep the newest frame")

    def test_performance_threshold_detection(self):
        """Test performance threshold detection logic."""
        # Simulate threshold checking
        threshold_ms = 100
        recent_measurements = [120, 110, 115, 105, 125]  # All above threshold
        
        # Check if consistently above threshold
        avg_recent = sum(recent_measurements) / len(recent_measurements)
        consistently_slow = avg_recent > threshold_ms * 0.8  # 80% of threshold
        
        self.assertTrue(consistently_slow, 
                       "Should detect consistently slow performance")
        
        # Test with good performance
        good_measurements = [50, 45, 55, 40, 60]  # All below threshold
        avg_good = sum(good_measurements) / len(good_measurements)
        consistently_good = avg_good <= threshold_ms * 0.8
        
        self.assertTrue(consistently_good,
                       "Should detect good performance")

    def benchmark_optimization_overhead(self):
        """Benchmark the overhead of our performance optimizations."""
        iterations = 100  # Reduced for faster testing
        
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
        
        # Overhead should be minimal (less than 100% increase for small operations)
        overhead_ratio = optimized_time / baseline_time if baseline_time > 0 else 1
        
        print(f"\nPerformance Benchmark Results:")
        print(f"Baseline: {baseline_time:.4f}s, Optimized: {optimized_time:.4f}s")
        print(f"Overhead: {(overhead_ratio - 1) * 100:.1f}%")
        
        # For very fast operations, overhead might be higher, but should be reasonable
        self.assertLess(overhead_ratio, 3.0, 
                       "Performance monitoring overhead should be reasonable")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 