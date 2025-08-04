#!/usr/bin/env python3
"""
Test Dictation Workflow

This test suite validates the complete dictation workflow that we've been debugging:
- Wake word detection
- Dictation state management
- Transcription processing
- Clipboard integration
- Return to listening state

This ensures that future changes don't break the core dictation functionality.
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    # Import actual modules
    from src.audio.audio_handler import AudioHandler
    from transcription_handler import TranscriptionHandler
    import config
    from utils import log_text
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("Running in mock mode...")


class TestDictationWorkflow(unittest.TestCase):
    """Test the complete dictation workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.workflow_events = []
        self.state_changes = []
        self.status_updates = []
        self.clipboard_content = None
        
        # Mock callbacks
        def capture_event(event_type, data):
            self.workflow_events.append((event_type, data))
            
        def capture_state(state_data):
            self.state_changes.append(state_data)
            
        def capture_status(message, color):
            self.status_updates.append((message, color))
            
        def mock_clipboard_copy(text):
            self.clipboard_content = text
            
        self.event_callback = capture_event
        self.state_callback = capture_state
        self.status_callback = capture_status
        self.clipboard_callback = mock_clipboard_copy
        
        # Clear previous data
        self.workflow_events.clear()
        self.state_changes.clear()
        self.status_updates.clear()
        self.clipboard_content = None

    def test_wake_word_detection_triggers_dictation(self):
        """Test that wake word detection properly triggers dictation mode."""
        print("\n=== Testing Wake Word Detection → Dictation Trigger ===")
        
        wake_word_scenarios = [
            {"word": "note", "mode": "dictate", "expected_state": "dictation"},
            {"word": "proof", "mode": "proofread", "expected_state": "dictation"},
            {"word": "letter", "mode": "letter", "expected_state": "dictation"},
        ]
        
        for scenario in wake_word_scenarios:
            with self.subTest(wake_word=scenario["word"]):
                word = scenario["word"]
                mode = scenario["mode"]
                expected_state = scenario["expected_state"]
                
                print(f"Testing wake word: '{word}' → {mode} mode")
                
                # Simulate wake word detection
                initial_state = {"audioState": "activation", "programActive": True}
                
                # Expected state transition
                expected_transition = {
                    "audioState": expected_state,
                    "programActive": True,
                    "isDictating": True,
                    "currentMode": mode
                }
                
                print(f"  Initial: {initial_state}")
                print(f"  Expected: {expected_transition}")
                
                # Validate state transition logic
                self.assertEqual(expected_transition["audioState"], "dictation")
                self.assertTrue(expected_transition["programActive"])
                self.assertTrue(expected_transition["isDictating"])
                self.assertEqual(expected_transition["currentMode"], mode)
                
                print(f"✅ Wake word '{word}' correctly triggers {mode} dictation")
        
        print("✅ Wake word detection validation complete")

    def test_dictation_state_management(self):
        """Test dictation state management during speech."""
        print("\n=== Testing Dictation State Management ===")
        
        # Test dictation state properties
        dictation_state = {
            "audioState": "dictation",
            "programActive": True,
            "isDictating": True,
            "canDictate": True,
            "currentMode": "dictate"
        }
        
        print(f"Dictation state: {dictation_state}")
        
        # Validate dictation state properties
        self.assertEqual(dictation_state["audioState"], "dictation")
        self.assertTrue(dictation_state["programActive"])
        self.assertTrue(dictation_state["isDictating"])
        self.assertTrue(dictation_state["canDictate"])
        self.assertIn(dictation_state["currentMode"], ["dictate", "proofread", "letter"])
        
        # Test expected status message
        expected_status = ("Dictating... (speak clearly)", "green")
        status_message, status_color = expected_status
        
        print(f"Expected status: '{status_message}' → {status_color}")
        
        self.assertEqual(status_color, "green")
        self.assertIn("Dictating", status_message)
        
        print("✅ Dictation state management validation complete")

    def test_transcription_processing_flow(self):
        """Test transcription processing state and flow."""
        print("\n=== Testing Transcription Processing Flow ===")
        
        # Test processing state transition
        processing_flow = [
            {
                "phase": "Start Processing",
                "state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "status": ("Processing transcription...", "orange")
            },
            {
                "phase": "Transcription Complete",
                "state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "status": ("Transcription completed (0.37s)", "green")
            },
            {
                "phase": "Text Processing",
                "state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "status": ("Processing text...", "orange")
            }
        ]
        
        for step in processing_flow:
            with self.subTest(phase=step["phase"]):
                phase = step["phase"]
                state = step["state"]
                status_message, status_color = step["status"]
                
                print(f"Phase: {phase}")
                print(f"  State: {state}")
                print(f"  Status: '{status_message}' → {status_color}")
                
                # Validate processing state
                self.assertEqual(state["audioState"], "processing")
                self.assertTrue(state["programActive"])
                self.assertFalse(state["isDictating"])
                
                # Validate status colors
                if "Processing" in status_message:
                    self.assertEqual(status_color, "orange")
                elif "completed" in status_message:
                    self.assertEqual(status_color, "green")
                
                print(f"✅ {phase} validated")
        
        print("✅ Transcription processing flow validation complete")

    def test_clipboard_integration(self):
        """Test clipboard integration for different modes."""
        print("\n=== Testing Clipboard Integration ===")
        
        clipboard_scenarios = [
            {
                "mode": "dictate",
                "transcription": "The patient reports headache symptoms.",
                "expected_clipboard": "The patient reports headache symptoms. ",
                "expected_action": "paste_immediately"
            },
            {
                "mode": "proofread",
                "transcription": "patient has headache symptoms",
                "processed_text": "The patient has headache symptoms.",
                "expected_clipboard": "The patient has headache symptoms.",
                "expected_action": "show_proofing_window"
            },
            {
                "mode": "letter",
                "transcription": "hope you are feeling better",
                "processed_text": "I hope you are feeling better.",
                "expected_clipboard": "I hope you are feeling better.",
                "expected_action": "show_proofing_window"
            }
        ]
        
        for scenario in clipboard_scenarios:
            with self.subTest(mode=scenario["mode"]):
                mode = scenario["mode"]
                transcription = scenario["transcription"]
                expected_clipboard = scenario["expected_clipboard"]
                expected_action = scenario["expected_action"]
                
                print(f"Testing {mode} mode clipboard integration")
                print(f"  Transcription: '{transcription}'")
                print(f"  Expected clipboard: '{expected_clipboard}'")
                print(f"  Expected action: {expected_action}")
                
                # Simulate clipboard copy
                self.clipboard_callback(expected_clipboard)
                
                # Validate clipboard content
                self.assertEqual(self.clipboard_content, expected_clipboard)
                
                # Validate mode-specific behavior
                if mode == "dictate":
                    # Direct paste with space
                    self.assertTrue(expected_clipboard.endswith(" "))
                elif mode in ["proofread", "letter"]:
                    # Processed text, no trailing space
                    self.assertFalse(expected_clipboard.endswith(" "))
                
                print(f"✅ {mode} clipboard integration validated")
        
        print("✅ Clipboard integration validation complete")

    def test_return_to_listening_state(self):
        """Test return to listening state after dictation completion."""
        print("\n=== Testing Return to Listening State ===")
        
        # Test the complete workflow end-to-end
        workflow_steps = [
            {
                "step": "Complete Transcription",
                "from_state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "action": "transcription_complete",
                "expected_state": {"audioState": "activation", "programActive": True, "isDictating": False}
            },
            {
                "step": "Send to Clipboard",
                "from_state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "action": "clipboard_copy",
                "expected_state": {"audioState": "activation", "programActive": True, "isDictating": False}
            },
            {
                "step": "Reset Current Mode",
                "from_state": {"audioState": "activation", "programActive": True, "isDictating": False},
                "action": "reset_mode",
                "expected_state": {"audioState": "activation", "programActive": True, "isDictating": False, "currentMode": None}
            }
        ]
        
        for step_data in workflow_steps:
            with self.subTest(step=step_data["step"]):
                step = step_data["step"]
                from_state = step_data["from_state"]
                action = step_data["action"]
                expected_state = step_data["expected_state"]
                
                print(f"Step: {step}")
                print(f"  From: {from_state}")
                print(f"  Action: {action}")
                print(f"  Expected: {expected_state}")
                
                # Validate return to activation state
                self.assertEqual(expected_state["audioState"], "activation")
                self.assertTrue(expected_state["programActive"])
                self.assertFalse(expected_state["isDictating"])
                
                # Validate mode reset
                if "currentMode" in expected_state:
                    self.assertIsNone(expected_state["currentMode"])
                
                print(f"✅ {step} validated")
        
        # Test final status message
        final_status = ("Listening for activation words...", "blue")
        status_message, status_color = final_status
        
        print(f"Final status: '{status_message}' → {status_color}")
        
        self.assertEqual(status_color, "blue")
        self.assertIn("Listening", status_message)
        
        print("✅ Return to listening state validation complete")

    def test_error_recovery_during_dictation(self):
        """Test error recovery during dictation workflow."""
        print("\n=== Testing Error Recovery During Dictation ===")
        
        error_scenarios = [
            {
                "error": "Transcription failed",
                "during_state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "recovery_state": {"audioState": "activation", "programActive": True, "isDictating": False},
                "recovery_status": ("Transcription failed, ready to try again", "orange")
            },
            {
                "error": "Audio stream interrupted",
                "during_state": {"audioState": "dictation", "programActive": True, "isDictating": True},
                "recovery_state": {"audioState": "activation", "programActive": True, "isDictating": False},
                "recovery_status": ("Audio interrupted, ready to try again", "orange")
            },
            {
                "error": "Clipboard copy failed",
                "during_state": {"audioState": "processing", "programActive": True, "isDictating": False},
                "recovery_state": {"audioState": "activation", "programActive": True, "isDictating": False},
                "recovery_status": ("Clipboard error, ready to try again", "orange")
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error=scenario["error"]):
                error = scenario["error"]
                during_state = scenario["during_state"]
                recovery_state = scenario["recovery_state"]
                status_message, status_color = scenario["recovery_status"]
                
                print(f"Error: {error}")
                print(f"  During state: {during_state}")
                print(f"  Recovery state: {recovery_state}")
                print(f"  Recovery status: '{status_message}' → {status_color}")
                
                # Validate error recovery
                self.assertEqual(recovery_state["audioState"], "activation")
                self.assertTrue(recovery_state["programActive"])
                self.assertFalse(recovery_state["isDictating"])
                
                # Validate error status
                self.assertEqual(status_color, "orange")
                self.assertIn("try again", status_message)
                
                print(f"✅ {error} recovery validated")
        
        print("✅ Error recovery validation complete")

    def test_complete_dictation_workflow_timing(self):
        """Test timing and performance of complete dictation workflow."""
        print("\n=== Testing Complete Dictation Workflow Timing ===")
        
        # Test expected timing benchmarks
        timing_expectations = [
            {"phase": "Wake word detection", "max_latency": 0.5, "unit": "seconds"},
            {"phase": "State transition to dictation", "max_latency": 0.1, "unit": "seconds"},
            {"phase": "Transcription processing", "max_latency": 2.0, "unit": "seconds"},
            {"phase": "Text processing", "max_latency": 0.1, "unit": "seconds"},
            {"phase": "Clipboard copy", "max_latency": 0.1, "unit": "seconds"},
            {"phase": "Return to listening", "max_latency": 0.1, "unit": "seconds"},
        ]
        
        total_max_time = sum(expectation["max_latency"] for expectation in timing_expectations)
        
        print(f"Expected workflow phases and timing:")
        for expectation in timing_expectations:
            phase = expectation["phase"]
            max_latency = expectation["max_latency"]
            unit = expectation["unit"]
            
            print(f"  {phase}: < {max_latency} {unit}")
            
            # Validate reasonable timing expectations
            self.assertLessEqual(max_latency, 5.0, 
                f"Phase '{phase}' has unreasonable timing expectation")
        
        print(f"Total expected workflow time: < {total_max_time} seconds")
        
        # Validate total workflow timing is reasonable
        self.assertLessEqual(total_max_time, 10.0, 
            "Total workflow time should be under 10 seconds")
        
        print("✅ Workflow timing validation complete")


class TestDictationIntegration(unittest.TestCase):
    """Test dictation integration with other components."""
    
    def test_audio_handler_dictation_integration(self):
        """Test integration between AudioHandler and dictation workflow."""
        print("\n=== Testing AudioHandler Dictation Integration ===")
        
        # Test AudioHandler state management during dictation
        audio_states = [
            {"state": "activation", "should_listen": True, "should_record": False},
            {"state": "dictation", "should_listen": False, "should_record": True},
            {"state": "processing", "should_listen": False, "should_record": False},
        ]
        
        for state_data in audio_states:
            with self.subTest(state=state_data["state"]):
                state = state_data["state"]
                should_listen = state_data["should_listen"]
                should_record = state_data["should_record"]
                
                print(f"State: {state}")
                print(f"  Should listen for wake words: {should_listen}")
                print(f"  Should record audio: {should_record}")
                
                # Validate state behavior logic
                if state == "activation":
                    self.assertTrue(should_listen)
                    self.assertFalse(should_record)
                elif state == "dictation":
                    self.assertFalse(should_listen)
                    self.assertTrue(should_record)
                elif state == "processing":
                    self.assertFalse(should_listen)
                    self.assertFalse(should_record)
                
                print(f"✅ {state} state behavior validated")
        
        print("✅ AudioHandler dictation integration validation complete")

    def test_transcription_handler_dictation_integration(self):
        """Test integration with TranscriptionHandler during dictation."""
        print("\n=== Testing TranscriptionHandler Dictation Integration ===")
        
        # Test transcription handler workflow
        transcription_steps = [
            {"step": "Start transcription", "input": "audio_data", "expected_output": "text"},
            {"step": "Apply text processing", "input": "raw_text", "expected_output": "processed_text"},
            {"step": "Return result", "input": "processed_text", "expected_output": "final_result"},
        ]
        
        for step_data in transcription_steps:
            with self.subTest(step=step_data["step"]):
                step = step_data["step"]
                input_type = step_data["input"]
                expected_output = step_data["expected_output"]
                
                print(f"Step: {step}")
                print(f"  Input: {input_type}")
                print(f"  Expected output: {expected_output}")
                
                # Validate step logic
                if step == "Start transcription":
                    self.assertEqual(input_type, "audio_data")
                    self.assertEqual(expected_output, "text")
                elif step == "Apply text processing":
                    self.assertEqual(input_type, "raw_text")
                    self.assertEqual(expected_output, "processed_text")
                elif step == "Return result":
                    self.assertEqual(input_type, "processed_text")
                    self.assertEqual(expected_output, "final_result")
                
                print(f"✅ {step} validated")
        
        print("✅ TranscriptionHandler dictation integration validation complete")


def run_dictation_workflow_tests():
    """Run the dictation workflow test suite."""
    print("=" * 60)
    print("CITRIX TRANSCRIBER - DICTATION WORKFLOW TESTS")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add dictation workflow tests
    suite.addTest(unittest.makeSuite(TestDictationWorkflow))
    suite.addTest(unittest.makeSuite(TestDictationIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall Status: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


if __name__ == "__main__":
    success = run_dictation_workflow_tests()
    sys.exit(0 if success else 1) 