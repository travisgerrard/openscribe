# Make pynput imports conditional for CI compatibility
try:
        from pynput import keyboard
        PYNPUT_AVAILABLE = True
except ImportError:
    # pynput not available (CI environment)
    PYNPUT_AVAILABLE = False
    print("[WARN] pynput not available in hotkey_manager.py - using mock classes")
    # Create a minimal mock keyboard module
    class MockKeyboard:
        class Key:
            cmd = "cmd"
            shift = "shift"
            ctrl = "ctrl"
            alt = "alt"
            space = "space"
            
        class KeyCode:
            def __init__(self, char=None):
                self.char = char
            
            @staticmethod
            def from_char(char):
                return MockKeyboard.KeyCode(char)
        
        class Listener:
            def __init__(self, on_press=None, on_release=None):
                self.on_press = on_press
                self.on_release = on_release
            
            def start(self):
                pass
            
            def stop(self):
                pass
            
            def join(self):
                pass
    
    keyboard = MockKeyboard()

import threading
import time

# Import configuration constants
from src.config import config
from src.utils.utils import log_text


class HotkeyManager:
    """Manages global hotkey listeners using pynput."""

    def __init__(self, on_hotkey_callback=None, on_status_update_callback=None):
        """
        Initializes the HotkeyManager.

        Args:
            on_hotkey_callback: Function to call when a registered hotkey combination is pressed.
                                Receives the command string associated with the hotkey.
            on_status_update_callback: Function to call to update the application status display.
                                       Receives status text (str) and color (str).
        """
        self.on_hotkey = on_hotkey_callback
        self.on_status_update = on_status_update_callback
        self._listener_thread = None
        self._listener = None
        self._stop_event = threading.Event()
        self._current_keys = set()  # Keep track of currently pressed keys
        self._is_dictating = False  # Track if dictation mode is active

    def set_dictating_state(self, is_dictating: bool):
        """Update the dictation state."""
        self._is_dictating = is_dictating
        # log_text("HOTKEY_DEBUG", f"Dictation state set to: {self._is_dictating}")

    def _log_status(self, message, color="black"):
        """Helper to call the status update callback if available."""
        print(f"HotkeyManager Status: {message}")  # Also print to console
        if self.on_status_update:
            self.on_status_update(message, color)

    def _normalize_key(self, key):
        """Normalize key representation for consistent comparison."""
        # For special keys, return the key object itself.
        # For character keys, return the KeyCode object.
        if hasattr(key, "char") and key.char:
            # It's a character key, potentially wrapped in KeyCode already or just a char
            # We want the KeyCode object for consistency in the set
            return keyboard.KeyCode.from_char(key.char)
        # It's a special key (like Key.cmd, Key.shift, etc.)
        return key

    def _on_press(self, key):
        """Callback function for key press events."""
        try:
            normalized_key = self._normalize_key(key)
            # log_text("HOTKEY_DEBUG", f"Key pressed: {key} (Normalized: {normalized_key})")
            self._current_keys.add(normalized_key)

            # --- Check for space bar during dictation ---
            if self._is_dictating and key == keyboard.Key.space:
                # log_text("HOTKEY_DEBUG", "Space bar pressed during dictation. Stopping.")
                self._log_status("Space bar pressed, stopping dictation...", "blue")
                if self.on_hotkey:
                    try:
                        # Trigger the stop command immediately on press
                        self.on_hotkey(config.COMMAND_STOP_DICTATE)
                    except Exception as e:
                        self._log_status(
                            f"Error executing hotkey callback for '{config.COMMAND_STOP_DICTATE}': {e}",
                            "red",
                        )
                # Prevent space from being added to the set if it stops dictation
                self._current_keys.remove(normalized_key)
                return  # Stop further processing for this key press

        except Exception as e:
            print(f"ERROR: Error in _on_press: {e}")
            # log_text("HOTKEY_ERROR", f"Error in _on_press: {e}")

    def _on_release(self, key):
        """Callback function for key release events."""
        try:
            normalized_key = self._normalize_key(key)
            # log_text("HOTKEY_DEBUG", f"Key released: {key} (Normalized: {normalized_key})")

            # Check for combination *before* removing the key
            current_combination = frozenset(self._current_keys)
            # log_text("HOTKEY_DEBUG", f"Current combination: {current_combination}")
            if current_combination in config.HOTKEY_COMBINATIONS:
                command = config.HOTKEY_COMBINATIONS[current_combination]
                # log_text("HOTKEY_DEBUG", f"Hotkey detected: {current_combination} -> {command}")
                self._log_status(
                    f"Hotkey detected on release: {current_combination} -> {command}",
                    "blue",
                )
                if self.on_hotkey:
                    try:
                        self.on_hotkey(command)
                    except Exception as e:
                        self._log_status(
                            f"Error executing hotkey callback for '{command}': {e}",
                            "red",
                        )
                # Optional: Clear keys after successful trigger? Depends on desired behavior.
                # self._current_keys.clear()

            # Now remove the key
            self._current_keys.remove(normalized_key)
        except KeyError:
            # Key might have been released that wasn't tracked (e.g., if listener started while key was held)
            # log_text("HOTKEY_DEBUG", f"Key {normalized_key} released but not found in current keys.")
            pass
        except Exception as e:
            print(f"ERROR: Error in _on_release: {e}")
            # log_text("HOTKEY_ERROR", f"Error in _on_release: {e}")

    def _run_listener(self):
        """Runs the pynput listener loop."""
        self._log_status("Hotkey listener thread started.", "grey")
        try:
            # Setup the listener (non-blocking version might be complex with start/stop)
            self._listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
            )
            self._listener.start()
            # Keep the thread alive until stop_event is set
            self._stop_event.wait()
            self._log_status("Stop event received, stopping listener...", "blue")
            self._listener.stop()
            # Join might be needed here if stop() is not synchronous enough
            self._listener.join()

        except Exception as e:
            self._log_status(f"Error in hotkey listener thread: {e}", "red")
        finally:
            self._listener = None  # Clear listener instance
            self._log_status("Hotkey listener thread finished.", "blue")

    def start(self):
        """Starts the hotkey listener in a separate thread."""
        if not PYNPUT_AVAILABLE:
            self._log_status("Hotkey listener disabled - pynput not available (CI environment)", "orange")
            return
            
        if self._listener_thread is not None and self._listener_thread.is_alive():
            self._log_status("Hotkey listener already running.", "orange")
            return

        self._stop_event.clear()
        self._current_keys.clear()  # Reset keys on start
        self._listener_thread = threading.Thread(
            target=self._run_listener, daemon=False
        )  # Make thread non-daemon
        self._listener_thread.start()

    def stop(self):
        """Stops the hotkey listener thread."""
        if not PYNPUT_AVAILABLE:
            self._log_status("Hotkey listener was disabled - pynput not available", "orange")
            return
            
        if self._listener_thread is None or not self._listener_thread.is_alive():
            self._log_status("Hotkey listener not running.", "orange")
            return

        self._log_status("Attempting to stop hotkey listener...", "blue")
        self._stop_event.set()  # Signal the listener thread to stop

        # Wait for the listener thread to finish
        self._listener_thread.join(timeout=2)  # Add a timeout

        if self._listener_thread.is_alive():
            self._log_status(
                "Hotkey listener thread did not stop gracefully.", "orange"
            )
            # If the listener is stuck, there isn't much more we can do from here
            # without more drastic measures which might be unsafe.
        else:
            self._log_status("Hotkey listener stopped.", "green")

        self._listener_thread = None
        self._current_keys.clear()  # Clear keys on stop


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Make sure config.py is present

    def handle_hotkey_test(command):
        print(f"\n*** Hotkey Executed: Command = {command} ***\n")
        # Example: Stop listener on restart command for testing
        if command == config.COMMAND_RESTART:
            print("Restart command received, stopping listener for test.")
            hotkey_manager.stop()

    def handle_status_update_test(message, color):
        print(f"--- STATUS [{color}]: {message} ---")

    print("Initializing HotkeyManager...")
    hotkey_manager = HotkeyManager(
        on_hotkey_callback=handle_hotkey_test,
        on_status_update_callback=handle_status_update_test,
    )

    print("Starting HotkeyManager...")
    hotkey_manager.start()

    print("\nHotkey listener running. Try pressing hotkeys defined in config.py.")
    print(f"Example: Cmd+Shift+D ({config.COMMAND_START_DICTATE})")
    print(f"Example: Cmd+Shift+R ({config.COMMAND_RESTART}) to stop this test.")
    print("Press Ctrl+C in the console if needed (listener runs as daemon).")

    # Keep the main thread alive while the listener runs
    try:
        while (
            hotkey_manager._listener_thread
            and hotkey_manager._listener_thread.is_alive()
        ):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Stopping HotkeyManager...")
        hotkey_manager.stop()

    print("\nHotkeyManager test finished.")
