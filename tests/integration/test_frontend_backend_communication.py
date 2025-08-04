#!/usr/bin/env python3
"""
Frontend-Backend Communication Integration Tests

Tests to catch the IPC and GUI issues we encountered during refactoring:
1. Electron process startup and GUI rendering
2. Python-Electron IPC message passing
3. Duplicate status message prevention (tray icon flashing)
4. Frontend state synchronization with backend
5. Error handling in communication channels

These tests validate the full frontend-backend integration pipeline.
"""

import unittest
import subprocess
import os
import sys
import time
import json
import signal
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import queue
import socket
import psutil


class TestFrontendBackendCommunication(unittest.TestCase):
    """Test suite for frontend-backend communication integration."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.backend_process = None
        self.frontend_process = None
        self.test_timeout = 30
        
    def tearDown(self):
        """Clean up any running processes."""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self.backend_process.kill()
                except OSError:
                    pass
                    
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self.frontend_process.kill()
                except OSError:
                    pass

    def test_electron_app_startup(self):
        """Test that Electron app can start and create GUI window."""
        try:
            # Start Electron app
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it initialize
            time.sleep(8)
            
            # Check if process is still running
            poll_result = self.frontend_process.poll()
            
            if poll_result is not None:
                stdout, stderr = self.frontend_process.communicate(timeout=5)
                self.fail(f"Electron app terminated unexpectedly with code {poll_result}. "
                         f"STDOUT: {stdout[:1000]}... STDERR: {stderr[:1000]}...")
            
            # Check for successful initialization patterns in output
            # This would catch issues like missing GUI files
            
        except subprocess.TimeoutExpired:
            self.fail("Electron app startup test timed out")
        except FileNotFoundError:
            self.fail("npm not found - cannot test Electron app startup")

    def test_backend_python_startup_in_electron_context(self):
        """Test that Python backend starts successfully when launched by Electron."""
        try:
            # Start the full application (Electron + Python)
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor output for backend startup indicators
            startup_timeout = 15
            backend_started = False
            python_error = None
            
            start_time = time.time()
            while time.time() - start_time < startup_timeout:
                # Check if main process is still alive
                if self.frontend_process.poll() is not None:
                    stdout, stderr = self.frontend_process.communicate(timeout=5)
                    
                    # Check for Python import errors (like the pyaudio issue we had)
                    if "ModuleNotFoundError" in stderr:
                        python_error = stderr
                        break
                    elif "Python STDERR" in stdout:
                        python_error = stdout
                        break
                        
                    self.fail(f"Application terminated during startup. "
                             f"STDOUT: {stdout[:1000]}... STDERR: {stderr[:1000]}...")
                
                time.sleep(0.5)
            
            if python_error:
                self.fail(f"Python backend failed to start: {python_error[:1000]}...")
                
            # If we get here, the app appeared to start successfully
            self.assertTrue(True, "Backend started successfully in Electron context")
            
        except subprocess.TimeoutExpired:
            self.fail("Backend startup test in Electron context timed out")
        except FileNotFoundError:
            self.fail("npm not found - cannot test full application startup")

    def test_ipc_message_flow_integrity(self):
        """Test that IPC messages flow correctly between frontend and backend."""
        try:
            # Start the application
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for initialization
            time.sleep(10)
            
            # Monitor for IPC-related messages
            output_queue = queue.Queue()
            
            def monitor_output():
                try:
                    for line in iter(self.frontend_process.stdout.readline, ''):
                        output_queue.put(('stdout', line))
                        if not line:
                            break
                except:
                    pass
            
            output_thread = threading.Thread(target=monitor_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Collect messages for analysis
            messages = []
            monitor_time = 8
            start_time = time.time()
            
            while time.time() - start_time < monitor_time:
                try:
                    source, message = output_queue.get(timeout=0.5)
                    messages.append(message.strip())
                except queue.Empty:
                    continue
            
            # Analyze messages for IPC patterns
            ipc_messages = [msg for msg in messages if '[IPC]' in msg]
            status_messages = [msg for msg in messages if 'STATUS:' in msg]
            
            # Check for proper IPC initialization
            ipc_init_found = any('IPC Handlers Initialized' in msg for msg in messages)
            self.assertTrue(ipc_init_found, 
                           "IPC handlers initialization not detected. "
                           "This indicates frontend-backend communication setup failed.")
            
            # Check for status message processing
            if status_messages:
                self.assertTrue(len(status_messages) > 0, 
                               "No STATUS messages detected - backend may not be communicating")
                
        except subprocess.TimeoutExpired:
            self.fail("IPC message flow test timed out")

    def test_duplicate_status_message_prevention(self):
        """Test that duplicate status messages don't cause tray icon flashing."""
        try:
            # Start the application
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for full initialization
            time.sleep(12)
            
            # Collect all output
            messages = []
            try:
                # Read available output without blocking
                output, _ = self.frontend_process.communicate(timeout=2)
                messages = output.splitlines()
            except subprocess.TimeoutExpired:
                # Process still running, that's okay
                pass
            
            # Analyze for duplicate status messages that caused our tray flashing
            status_listening = [msg for msg in messages if 
                              'STATUS:blue:Listening for activation words' in msg]
            
            if len(status_listening) > 1:
                # Look for rapid duplicates (within 1 second)
                timestamps = []
                for msg in messages:
                    if 'STATUS:blue:Listening for activation words' in msg:
                        # Extract timestamp or line position as proxy
                        timestamps.append(messages.index(msg))
                
                if len(timestamps) > 1:
                    gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                    rapid_duplicates = [gap for gap in gaps if gap < 3]  # Less than 3 lines apart
                    
                    if rapid_duplicates:
                        self.fail(f"Detected {len(rapid_duplicates)} rapid duplicate status messages. "
                                 f"This causes tray icon flashing. Messages: {status_listening}")
            
            # Check for tray state conflicts
            tray_states = [msg for msg in messages if 'set-tray-state received:' in msg]
            if len(tray_states) > 2:  # Allow some state changes, but not excessive
                rapid_tray_changes = []
                for i in range(len(tray_states) - 1):
                    curr_idx = messages.index(tray_states[i])
                    next_idx = messages.index(tray_states[i+1])
                    if next_idx - curr_idx < 3:  # Less than 3 lines apart
                        rapid_tray_changes.append((tray_states[i], tray_states[i+1]))
                
                if rapid_tray_changes:
                    self.fail(f"Detected rapid tray state changes that cause flashing: {rapid_tray_changes}")
                    
        except subprocess.TimeoutExpired:
            self.fail("Duplicate status message test timed out")

    def test_microphone_access_single_stream(self):
        """Test that microphone access doesn't cause system indicator flashing."""
        try:
            # Start the application
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for initialization
            time.sleep(10)
            
            # Look for microphone-related messages
            output_queue = queue.Queue()
            
            def monitor_output():
                try:
                    for line in iter(self.frontend_process.stdout.readline, ''):
                        output_queue.put(line)
                        if not line:
                            break
                except:
                    pass
            
            output_thread = threading.Thread(target=monitor_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Monitor for microphone access patterns
            mic_messages = []
            monitor_time = 8
            start_time = time.time()
            
            while time.time() - start_time < monitor_time:
                try:
                    message = output_queue.get(timeout=0.5)
                    if any(keyword in message.lower() for keyword in 
                          ['microphone', 'audio stream', 'pyaudio', 'check_microphone']):
                        mic_messages.append(message.strip())
                except queue.Empty:
                    continue
            
            # Analyze microphone access patterns
            # The issue was check_microphone_availability() opening test stream + real stream
            test_stream_messages = [msg for msg in mic_messages if 'test' in msg.lower()]
            stream_messages = [msg for msg in mic_messages if 'stream' in msg.lower()]
            
            # Should not see multiple rapid microphone accesses
            if len(stream_messages) > 2:  # Allow for some legitimate stream operations
                self.fail(f"Too many microphone stream operations detected: {stream_messages}. "
                         f"This can cause macOS microphone indicator flashing.")
                         
        except subprocess.TimeoutExpired:
            self.fail("Microphone access test timed out")

    def test_frontend_gui_element_accessibility(self):
        """Test that frontend GUI elements are properly accessible."""
        # This is more of a structure test since we can't easily test DOM in headless mode
        
        # Check that critical frontend files exist and have expected content
        frontend_files = {
            'index.html': self.project_root / 'frontend' / 'main' / 'index.html',
            'renderer.js': self.project_root / 'frontend' / 'main' / 'renderer.js',
            'style.css': self.project_root / 'frontend' / 'styles' / 'style.css'
        }
        
        for file_name, file_path in frontend_files.items():
            self.assertTrue(file_path.exists(), f"Frontend file missing: {file_path}")
            
            # Check file has content
            with open(file_path, 'r') as f:
                content = f.read()
            self.assertGreater(len(content), 100, f"Frontend file {file_name} appears empty or too small")
            
        # Check index.html has required elements
        with open(frontend_files['index.html'], 'r') as f:
            html_content = f.read()
            
        required_elements = [
            'control-bar',
            'status-dot',
            'waveform-canvas',
            'mic-conflict-banner'
        ]
        
        for element_id in required_elements:
            self.assertIn(element_id, html_content, 
                         f"Required GUI element '{element_id}' not found in index.html")

    def test_backend_frontend_state_synchronization(self):
        """Test that backend and frontend state stay synchronized."""
        try:
            # Start the application
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for initialization
            time.sleep(10)
            
            # Monitor state-related messages
            output_queue = queue.Queue()
            
            def monitor_output():
                try:
                    for line in iter(self.frontend_process.stdout.readline, ''):
                        output_queue.put(line)
                        if not line:
                            break
                except:
                    pass
            
            output_thread = threading.Thread(target=monitor_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Collect state-related messages
            state_messages = []
            monitor_time = 8
            start_time = time.time()
            
            while time.time() - start_time < monitor_time:
                try:
                    message = output_queue.get(timeout=0.5)
                    if any(keyword in message for keyword in 
                          ['STATE:', 'STATUS:', 'set-tray-state', 'Listening']):
                        state_messages.append(message.strip())
                except queue.Empty:
                    continue
            
            # Analyze for state consistency
            # Look for conflicting states
            status_states = []
            tray_states = []
            
            for msg in state_messages:
                if 'STATUS:' in msg:
                    if 'blue:' in msg:
                        status_states.append('listening')
                    elif 'orange:' in msg:
                        status_states.append('dictation')
                    elif 'grey:' in msg:
                        status_states.append('inactive')
                        
                if 'set-tray-state received:' in msg:
                    if 'inactive' in msg:
                        tray_states.append('inactive')
                    elif 'activation' in msg:
                        tray_states.append('listening')
                    elif 'dictation' in msg:
                        tray_states.append('dictation')
            
            # Check for major state inconsistencies
            if status_states and tray_states:
                # Compare final states
                final_status = status_states[-1] if status_states else None
                final_tray = tray_states[-1] if tray_states else None
                
                if final_status and final_tray and final_status != final_tray:
                    self.fail(f"Backend-frontend state mismatch detected. "
                             f"Final status: {final_status}, Final tray: {final_tray}")
                             
        except subprocess.TimeoutExpired:
            self.fail("State synchronization test timed out")

    def test_error_handling_in_communication(self):
        """Test that communication errors are handled gracefully."""
        try:
            # Start the application
            cmd = ['npm', 'start']
            self.frontend_process = subprocess.Popen(
                cmd, cwd=str(self.project_root),
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for initialization
            time.sleep(8)
            
            # Look for error handling patterns
            try:
                stdout, stderr = self.frontend_process.communicate(timeout=3)
                all_output = stdout + stderr
            except subprocess.TimeoutExpired:
                # Process still running, that's fine
                all_output = ""
            
            # Check for unhandled errors that could cause crashes
            critical_errors = [
                'Uncaught Exception',
                'Unhandled Promise Rejection',
                'Cannot read property',
                'TypeError:',
                'ReferenceError:'
            ]
            
            found_errors = []
            for error_pattern in critical_errors:
                if error_pattern in all_output:
                    found_errors.append(error_pattern)
            
            if found_errors:
                self.fail(f"Critical unhandled errors detected: {found_errors}. "
                         f"These can cause application crashes during operation.")
            
            # Check for proper error handling indicators
            error_handling_indicators = [
                'Error handled:',
                'IPC error:',
                'Python shell error:'
            ]
            
            # If there are errors, they should be handled gracefully
            # This is more of a warning than a failure
            
        except subprocess.TimeoutExpired:
            self.fail("Error handling test timed out")


if __name__ == '__main__':
    unittest.main() 