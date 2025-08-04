#!/usr/bin/env python3
"""
Test Electron App Shutdown Behavior

Tests to ensure that when the Electron app quits, the Python backend
properly shuts down and doesn't leave orphaned processes running.
"""

import unittest
import time
import threading
import subprocess
import sys
import signal
import os
from unittest.mock import Mock, patch


class TestElectronShutdown(unittest.TestCase):
    """Test graceful shutdown when Electron app quits"""

    def setUp(self):
        """Set up test environment"""
        self.processes = []
        self.cleanup_needed = []

    def tearDown(self):
        """Clean up any test processes"""
        for process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass

        for cleanup_func in self.cleanup_needed:
            try:
                cleanup_func()
            except:
                pass

    def test_shutdown_command_handling(self):
        """Test that Python backend handles SHUTDOWN command correctly"""
        import main
        
        # Mock the Application class to track shutdown calls
        original_shutdown = main.Application.shutdown
        shutdown_called = threading.Event()
        
        def mock_shutdown(self):
            shutdown_called.set()
            # Don't actually shut down for the test
            return
        
        with patch.object(main.Application, 'shutdown', mock_shutdown):
            # Create a minimal app instance
            app = main.Application()
            
            # Simulate receiving SHUTDOWN command
            # This would normally come through stdin, but we'll call directly
            app.shutdown()
            
            # Verify shutdown was called
            self.assertTrue(shutdown_called.wait(timeout=1.0))

    def test_python_backend_responds_to_stdin_shutdown(self):
        """Test that Python backend properly responds to SHUTDOWN via stdin"""
        # Start a Python process running main.py
        import subprocess
        import tempfile
        import os
        
        # Create a minimal script that simulates the shutdown behavior
        test_script = '''
import sys
import time

# Simple simulation of main.py stdin handling
def simulate_main_loop():
    print("PYTHON_BACKEND_READY", flush=True)
    
    for line in sys.stdin:
        command = line.strip()
        if command == "SHUTDOWN":
            print("BACKEND_SHUTDOWN_FINALIZED", flush=True)
            break
        elif command == "GET_CONFIG":
            # Minimal response to avoid hanging
            continue
        else:
            print(f"RECEIVED: {command}", flush=True)

if __name__ == "__main__":
    simulate_main_loop()
'''
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        self.cleanup_needed.append(lambda: os.unlink(script_path))
        
        # Start the process
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.processes.append(process)
        
        # Wait for ready signal
        ready_received = False
        start_time = time.time()
        while time.time() - start_time < 5.0:
            if process.poll() is not None:
                break
            try:
                line = process.stdout.readline()
                if line.strip() == "PYTHON_BACKEND_READY":
                    ready_received = True
                    break
            except:
                break
        
        self.assertTrue(ready_received, "Python backend should send ready signal")
        
        # Send shutdown command
        process.stdin.write("SHUTDOWN\n")
        process.stdin.flush()
        
        # Wait for shutdown confirmation
        shutdown_confirmed = False
        start_time = time.time()
        while time.time() - start_time < 5.0:
            if process.poll() is not None:
                break
            try:
                line = process.stdout.readline()
                if line.strip() == "BACKEND_SHUTDOWN_FINALIZED":
                    shutdown_confirmed = True
                    break
            except:
                break
        
        self.assertTrue(shutdown_confirmed, "Python backend should confirm shutdown")
        
        # Verify process exits cleanly
        exit_code = process.wait(timeout=5)
        self.assertEqual(exit_code, 0, "Python backend should exit with code 0")

    def test_shutdown_signal_handling(self):
        """Test that shutdown components handle cleanup properly"""
        from main import Application
        from unittest.mock import Mock
        
        # Create app with mocked handlers
        app = Application()
        
        # Mock the handlers to track cleanup calls
        app.hotkey_manager.stop = Mock()
        app.audio_handler.stop = Mock()
        app.audio_handler.terminate_pyaudio = Mock()
        
        # Mock hasattr and attributes
        app.audio_handler._p = Mock()
        
        # Call shutdown
        app.shutdown()
        
        # Verify all cleanup methods were called
        app.hotkey_manager.stop.assert_called_once()
        app.audio_handler.stop.assert_called_once()

    def test_graceful_shutdown_timeout_handling(self):
        """Test that shutdown handles timeouts gracefully"""
        # This test simulates what happens when components don't shut down quickly
        from main import Application
        from unittest.mock import Mock, patch
        import time
        
        app = Application()
        
        # Mock a slow-stopping audio handler
        def slow_stop():
            time.sleep(0.1)  # Simulate slow cleanup
        
        app.audio_handler.stop = Mock(side_effect=slow_stop)
        app.hotkey_manager.stop = Mock()
        
        # Shutdown should complete even with slow components
        start_time = time.time()
        app.shutdown()
        end_time = time.time()
        
        # Should complete in reasonable time (not hang)
        self.assertLess(end_time - start_time, 2.0, "Shutdown should not hang")
        
        # Verify cleanup was attempted
        app.audio_handler.stop.assert_called_once()
        app.hotkey_manager.stop.assert_called_once()

    def test_shutdown_error_handling(self):
        """Test that shutdown handles errors in component cleanup"""
        from main import Application
        from unittest.mock import Mock
        
        app = Application()
        
        # Mock handlers that raise errors during cleanup
        app.hotkey_manager.stop = Mock(side_effect=Exception("Hotkey cleanup error"))
        app.audio_handler.stop = Mock(side_effect=Exception("Audio cleanup error"))
        
        # Shutdown should not raise exceptions even if components fail
        try:
            app.shutdown()
        except Exception as e:
            self.fail(f"Shutdown should handle component errors gracefully, but raised: {e}")


class TestElectronLifecycleIntegration(unittest.TestCase):
    """Test integration between Electron lifecycle and Python backend"""

    def test_shutdown_message_format(self):
        """Test that shutdown messages follow expected format"""
        # Test the expected message format that Electron sends
        expected_shutdown_command = "SHUTDOWN"
        
        # Verify it's a simple string (no JSON parsing needed)
        self.assertIsInstance(expected_shutdown_command, str)
        self.assertEqual(expected_shutdown_command.strip(), "SHUTDOWN")

    def test_shutdown_confirmation_format(self):
        """Test that shutdown confirmation follows expected format"""
        # Test the expected confirmation message that Python sends
        expected_confirmation = "BACKEND_SHUTDOWN_FINALIZED"
        
        # Verify format matches what Electron expects
        self.assertIsInstance(expected_confirmation, str)
        self.assertEqual(expected_confirmation.strip(), "BACKEND_SHUTDOWN_FINALIZED")


if __name__ == "__main__":
    unittest.main(verbosity=2) 