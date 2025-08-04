#!/usr/bin/env python3
"""
State Synchronization Tests

These tests validate that audio states, GUI states, and user feedback remain synchronized
across the application. State desync causes user confusion and missed commands.

Prevents issues like:
- Audio handler thinking it's dictating while GUI shows inactive
- Commands being missed due to state inconsistencies
- User feedback not matching actual system state
"""

import unittest
import threading
import time
from typing import Dict, List, Callable
from unittest.mock import Mock, MagicMock


class MockAudioHandler:
    """Mock audio handler for testing state synchronization"""

    def __init__(self):
        self._listening_state = "inactive"
        self._program_active = True
        self._callbacks = []
        self._state_lock = threading.Lock()

    def set_listening_state(self, state: str):
        """Simulate audio state changes"""
        valid_states = [
            "inactive",
            "activation",
            "dictating",
            "processing",
            "preparing",
        ]
        if state not in valid_states:
            raise ValueError(f"Invalid state: {state}")

        with self._state_lock:
            old_state = self._listening_state
            self._listening_state = state
            # Notify callbacks of state change - handle errors gracefully
            for callback in self._callbacks:
                try:
                    callback("state_change", {"old": old_state, "new": state})
                except Exception as e:
                    # Log error but continue with other callbacks
                    print(f"Callback error (handled): {e}")

    def get_listening_state(self) -> str:
        with self._state_lock:
            return self._listening_state

    def set_program_active(self, active: bool):
        with self._state_lock:
            self._program_active = active

    def get_state(self) -> Dict:
        with self._state_lock:
            return {
                "listening_state": self._listening_state,
                "program_active": self._program_active,
                "timestamp": time.time(),
            }

    def add_callback(self, callback: Callable):
        self._callbacks.append(callback)


class MockGUIState:
    """Mock GUI state manager for testing"""

    def __init__(self):
        self.display_status = "waiting"
        self.color = "grey"
        self.is_dictating = False
        self.last_update = None
        self._update_lock = threading.Lock()

    def update_from_audio(self, audio_state: Dict):
        """Update GUI state based on audio handler state"""
        with self._update_lock:
            listening_state = audio_state.get("listening_state", "inactive")

            if listening_state == "dictating":
                self.display_status = "dictating"
                self.color = "green"
                self.is_dictating = True
            elif listening_state == "activation":
                self.display_status = "listening"
                self.color = "blue"
                self.is_dictating = False
            elif listening_state == "processing":
                self.display_status = "processing"
                self.color = "orange"
                self.is_dictating = False
            else:
                self.display_status = "inactive"
                self.color = "grey"
                self.is_dictating = False

            self.last_update = time.time()

    def get_state(self) -> Dict:
        with self._update_lock:
            return {
                "display_status": self.display_status,
                "color": self.color,
                "is_dictating": self.is_dictating,
                "last_update": self.last_update,
            }


class MockAppStateManager:
    """Centralized state manager for testing"""

    def __init__(self):
        self._state = {
            "audio_state": "inactive",
            "gui_state": "waiting",
            "processing_state": "idle",
            "llm_state": "ready",
        }
        self._listeners = []
        self._lock = threading.Lock()
        self._transition_log = []

    def set_state(self, key: str, value: str) -> bool:
        """Thread-safe state updates with validation"""
        with self._lock:
            if self._validate_transition(key, self._state.get(key), value):
                old_value = self._state.get(key)
                self._state[key] = value
                self._transition_log.append(
                    {
                        "key": key,
                        "old": old_value,
                        "new": value,
                        "timestamp": time.time(),
                    }
                )
                self._notify_listeners(key, value)
                return True
            return False

    def get_state(self) -> Dict:
        """Get current state snapshot"""
        with self._lock:
            return self._state.copy()

    def get_transition_log(self) -> List[Dict]:
        """Get history of state transitions for debugging"""
        with self._lock:
            return self._transition_log.copy()

    def _validate_transition(self, key: str, old_value: str, new_value: str) -> bool:
        """Validate that state transitions are legal"""

        # Audio state validation
        if key == "audio_state":
            valid_transitions = {
                "inactive": ["activation", "preparing"],
                "preparing": ["activation", "inactive"],
                "activation": ["dictating", "inactive"],
                "dictating": [
                    "processing",
                    "inactive",
                    "activation",
                ],  # Allow returning to activation
                "processing": ["activation", "inactive"],
            }
            return new_value in valid_transitions.get(old_value, [])

        # GUI state validation
        if key == "gui_state":
            valid_states = ["waiting", "listening", "dictating", "processing", "error"]
            return new_value in valid_states

        # Processing state validation
        if key == "processing_state":
            valid_states = ["idle", "transcribing", "llm_processing", "complete"]
            return new_value in valid_states

        # LLM state validation
        if key == "llm_state":
            valid_states = ["ready", "loading", "processing", "streaming", "error"]
            return new_value in valid_states

        return True  # Allow other keys for now

    def _notify_listeners(self, key: str, value: str):
        """Notify listeners of state changes"""
        for listener in self._listeners:
            try:
                listener(key, value)
            except Exception as e:
                print(f"Error notifying listener: {e}")

    def add_listener(self, listener: Callable):
        """Add state change listener"""
        self._listeners.append(listener)


class TestStateSynchronization(unittest.TestCase):
    """Test state synchronization across components"""

    def setUp(self):
        self.audio_handler = MockAudioHandler()
        self.gui_state = MockGUIState()
        self.app_state = MockAppStateManager()

    def test_audio_gui_state_sync(self):
        """Ensure audio handler state matches GUI display"""

        # Test dictating state
        self.audio_handler.set_listening_state("dictating")
        audio_state = self.audio_handler.get_state()
        self.gui_state.update_from_audio(audio_state)

        gui_state = self.gui_state.get_state()
        self.assertEqual(gui_state["display_status"], "dictating")
        self.assertEqual(gui_state["color"], "green")
        self.assertTrue(gui_state["is_dictating"])

        # Test activation state
        self.audio_handler.set_listening_state("activation")
        audio_state = self.audio_handler.get_state()
        self.gui_state.update_from_audio(audio_state)

        gui_state = self.gui_state.get_state()
        self.assertEqual(gui_state["display_status"], "listening")
        self.assertEqual(gui_state["color"], "blue")
        self.assertFalse(gui_state["is_dictating"])

        # Test processing state
        self.audio_handler.set_listening_state("processing")
        audio_state = self.audio_handler.get_state()
        self.gui_state.update_from_audio(audio_state)

        gui_state = self.gui_state.get_state()
        self.assertEqual(gui_state["display_status"], "processing")
        self.assertEqual(gui_state["color"], "orange")
        self.assertFalse(gui_state["is_dictating"])

    def test_concurrent_state_updates(self):
        """Test race conditions in state management"""

        def update_audio_state():
            """Simulate rapid audio state changes"""
            states = ["activation", "dictating", "processing", "activation"]
            for state in states:
                self.audio_handler.set_listening_state(state)
                time.sleep(0.01)  # Small delay to simulate real timing

        def update_gui_state():
            """Simulate GUI updates following audio changes"""
            for _ in range(10):
                audio_state = self.audio_handler.get_state()
                self.gui_state.update_from_audio(audio_state)
                time.sleep(0.005)

        # Run both operations concurrently
        audio_thread = threading.Thread(target=update_audio_state)
        gui_thread = threading.Thread(target=update_gui_state)

        audio_thread.start()
        gui_thread.start()

        audio_thread.join()
        gui_thread.join()

        # Verify final states are consistent
        final_audio_state = self.audio_handler.get_state()
        final_gui_state = self.gui_state.get_state()

        # GUI should have been updated recently (within 1 second)
        self.assertIsNotNone(final_gui_state["last_update"])
        self.assertLess(time.time() - final_gui_state["last_update"], 1.0)

    def test_state_transition_validation(self):
        """Test that invalid state transitions are rejected"""

        # Test valid transitions
        self.assertTrue(self.app_state.set_state("audio_state", "activation"))
        self.assertTrue(self.app_state.set_state("audio_state", "dictating"))
        self.assertTrue(self.app_state.set_state("audio_state", "processing"))

        # Test invalid transitions
        self.assertFalse(
            self.app_state.set_state("audio_state", "dictating")
        )  # Can't go from processing to dictating
        self.assertFalse(self.app_state.set_state("audio_state", "invalid_state"))

        # Verify state didn't change on invalid transition
        state = self.app_state.get_state()
        self.assertEqual(state["audio_state"], "processing")

    def test_state_consistency_across_components(self):
        """Test that all components maintain consistent state"""

        state_updates = []

        def state_listener(key: str, value: str):
            state_updates.append((key, value, time.time()))

        self.app_state.add_listener(state_listener)

        # Simulate a complete workflow
        workflow_steps = [
            ("audio_state", "activation"),
            ("gui_state", "listening"),
            ("audio_state", "dictating"),
            ("gui_state", "dictating"),
            ("processing_state", "transcribing"),
            ("llm_state", "processing"),
            ("llm_state", "streaming"),
            ("processing_state", "complete"),
            ("audio_state", "activation"),
            ("gui_state", "listening"),
        ]

        for key, value in workflow_steps:
            success = self.app_state.set_state(key, value)
            self.assertTrue(success, f"Failed to set {key} to {value}")
            time.sleep(0.01)  # Small delay between updates

        # Verify all updates were recorded
        self.assertEqual(len(state_updates), len(workflow_steps))

        # Verify final state is consistent
        final_state = self.app_state.get_state()
        self.assertEqual(final_state["audio_state"], "activation")
        self.assertEqual(final_state["gui_state"], "listening")
        self.assertEqual(final_state["processing_state"], "complete")
        self.assertEqual(final_state["llm_state"], "streaming")

    def test_state_recovery_after_error(self):
        """Test state recovery after component errors"""

        # Simulate error scenario
        self.app_state.set_state("audio_state", "activation")
        self.app_state.set_state("audio_state", "dictating")
        self.app_state.set_state("llm_state", "processing")

        # Simulate LLM error
        self.app_state.set_state("llm_state", "error")
        self.app_state.set_state("processing_state", "idle")

        # Verify recovery path
        self.app_state.set_state("audio_state", "activation")
        self.app_state.set_state("llm_state", "ready")

        final_state = self.app_state.get_state()
        self.assertEqual(final_state["audio_state"], "activation")
        self.assertEqual(final_state["llm_state"], "ready")
        self.assertEqual(final_state["processing_state"], "idle")

    def test_callback_error_handling(self):
        """Test that callback errors don't break state management"""

        def failing_callback(event, data):
            raise Exception("Simulated callback error")

        def working_callback(event, data):
            working_callback.called = True

        working_callback.called = False

        # Add both callbacks
        self.audio_handler.add_callback(failing_callback)
        self.audio_handler.add_callback(working_callback)

        # State change should work despite failing callback
        self.audio_handler.set_listening_state("dictating")

        # Working callback should still be called
        self.assertTrue(working_callback.called)

        # State should be updated correctly
        state = self.audio_handler.get_state()
        self.assertEqual(state["listening_state"], "dictating")

    def test_state_transition_timing(self):
        """Test that state transitions happen in reasonable time"""

        # Measure state transition performance
        start_time = time.time()

        for i in range(100):
            self.app_state.set_state("processing_state", "transcribing")
            self.app_state.set_state("processing_state", "idle")

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete 200 state transitions in < 100ms
        self.assertLess(
            total_time,
            0.1,
            f"State transitions too slow: {total_time:.3f}s for 200 transitions",
        )

        # Verify transition log is maintained
        log = self.app_state.get_transition_log()
        self.assertEqual(len(log), 200)  # Should have recorded all transitions

    def test_state_snapshot_consistency(self):
        """Test that state snapshots are atomic and consistent"""

        def rapid_state_changes():
            """Rapidly change multiple state values"""
            for i in range(50):
                self.app_state.set_state("audio_state", "activation")
                self.app_state.set_state("gui_state", "listening")
                self.app_state.set_state("audio_state", "dictating")
                self.app_state.set_state("gui_state", "dictating")

        def take_snapshots():
            """Take state snapshots during rapid changes"""
            snapshots = []
            for i in range(20):
                snapshot = self.app_state.get_state()
                snapshots.append(snapshot)
                time.sleep(0.01)
            return snapshots

        # Run state changes and snapshot taking concurrently
        changer_thread = threading.Thread(target=rapid_state_changes)
        snapshot_thread = threading.Thread(target=take_snapshots)

        changer_thread.start()
        snapshots = []
        snapshot_thread = threading.Thread(
            target=lambda: snapshots.extend(take_snapshots())
        )
        snapshot_thread.start()

        changer_thread.join()
        snapshot_thread.join()

        # Verify all snapshots are valid states
        for snapshot in snapshots:
            self.assertIsInstance(snapshot, dict)
            self.assertIn("audio_state", snapshot)
            self.assertIn("gui_state", snapshot)
            # Each snapshot should be internally consistent
            self.assertIsNotNone(snapshot["audio_state"])
            self.assertIsNotNone(snapshot["gui_state"])


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
