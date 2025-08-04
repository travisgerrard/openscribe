# Removed Tkinter imports: tk, messagebox, ThemedTk
import sys
import os
import threading
import json  # For potential structured communication over stdin/stdout
import time
import subprocess

# Make Quartz imports conditional for CI compatibility
try:
    from Quartz.CoreGraphics import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        kCGHIDEventTap,
        CGEventSetFlags,
        kCGEventFlagMaskCommand,
    )
    QUARTZ_AVAILABLE = True
except ImportError:
    # Quartz not available (CI environment or non-macOS)
    QUARTZ_AVAILABLE = False
    print("[WARN] Quartz.CoreGraphics not available - clipboard functionality will be limited")

# Make pynput imports conditional for CI compatibility
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    # pynput not available (CI environment)
    PYNPUT_AVAILABLE = False
    print("[WARN] pynput not available - hotkey functionality will be limited")
    # Create a minimal mock keyboard module for imports
    class MockKeyboard:
        class Key:
            cmd = "cmd"
            cmd_l = "cmd_l" 
            cmd_r = "cmd_r"
            shift = "shift"
            shift_l = "shift_l"
            shift_r = "shift_r"
            ctrl = "ctrl"
            ctrl_l = "ctrl_l"
            ctrl_r = "ctrl_r"
            alt = "alt"
            alt_l = "alt_l"
            alt_gr = "alt_gr"
            space = "space"
            
            def __init__(self, name=None):
                self.name = name
        
        class KeyCode:
            def __init__(self, char=None):
                self.char = char
    
    keyboard = MockKeyboard()

# Import refactored modules and config
from src.config import config
from src.utils.utils import log_text
from src.audio.audio_handler import AudioHandler
from src.transcription_handler import TranscriptionHandler
from src.llm.llm_handler import LLMHandler
from src.hotkey_manager import HotkeyManager
from src.memory_monitor import (
    MemoryMonitor,
    start_memory_monitoring,
    stop_memory_monitoring,
)

import src.memory_monitor as mm_module  # Import with an alias

print(f"[DEBUG_PATH] memory_monitor module loaded from: {mm_module.__file__}")

# Removed GUI import

# Set environment variable
os.environ["TOKENIZERS_PARALLELISM"] = config.TOKENIZERS_PARALLELISM

# Import settings manager and text processor
from src.config.settings_manager import settings_manager
from src.text_processor import text_processor

def send_text_to_citrix(text):
    """Copies text to clipboard and simulates Cmd+V."""
    if not text:
        print("No text provided to send.")
        return
    try:
        # Use pbcopy for clipboard access on macOS
        process = subprocess.Popen(
            "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE
        )
        process.communicate(input=text.encode("utf-8"))
        print(f"Sent to clipboard: {text[:50]}...")  # Log snippet

        if QUARTZ_AVAILABLE:
            # Simulate Cmd+V using Quartz
            key_code_v = 9  # Keycode for 'v' on macOS
            event_down = CGEventCreateKeyboardEvent(None, key_code_v, True)
            CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
            event_up = CGEventCreateKeyboardEvent(None, key_code_v, False)
            CGEventSetFlags(event_up, kCGEventFlagMaskCommand)

            CGEventPost(kCGHIDEventTap, event_down)
            time.sleep(0.05)  # Small delay between down and up
            CGEventPost(kCGHIDEventTap, event_up)
            print("Simulated Cmd+V")
        else:
            # Fallback: Only copy to clipboard, user needs to paste manually
            print("Text copied to clipboard - Cmd+V simulation not available (Quartz not found)")

    except Exception as e:
        print(f"Error sending text to Citrix: {e}")
        log_text("ERROR", f"Failed to send text via Cmd+V: {e}")


import json  # For IPC payload serialization


class Application:
    """Main application class orchestrating all components."""

    def __init__(self):
        self._program_active = True  # Overall state
        self._current_processing_mode = (
            None  # 'dictate', 'proofread', 'letter' - set when dictation starts
        )
        self._last_raw_transcription = (
            ""  # Store last raw text for proof/letter actions
        )
        self._current_prompt = None  # Store prompt for proofread/letter commands
        self._is_proofing_active = (
            False  # Tracks if LLM proofing/letter generation is active
        )

        # --- Initialize Handlers ---
        self.llm_handler = LLMHandler(
            on_processing_complete_callback=self._handle_llm_complete,
            on_status_update_callback=self._handle_status_update,
            on_proofing_activity_callback=self._set_proofing_active_state,  # New callback
        )
        
        # Initialize LLM Handler with saved model settings
        saved_proofing_model = settings_manager.get_setting("selectedProofingModel", config.DEFAULT_LLM)
        saved_letter_model = settings_manager.get_setting("selectedLetterModel", config.DEFAULT_LLM)
        saved_proofing_prompt = settings_manager.get_setting("proofingPrompt", config.DEFAULT_PROOFREAD_PROMPT)
        saved_letter_prompt = settings_manager.get_setting("letterPrompt", config.DEFAULT_LETTER_PROMPT)
        
        # Configure LLM with saved settings
        self.llm_handler.update_selected_models(saved_proofing_model, saved_letter_model)
        self.llm_handler.update_prompts(saved_proofing_prompt, saved_letter_prompt)
        log_text("INIT", f"LLM configured with saved settings - Proofing: {saved_proofing_model}, Letter: {saved_letter_model}")
        
        # Initialize TranscriptionHandler with saved ASR model
        saved_asr_model = settings_manager.get_setting("selectedAsrModel", config.DEFAULT_ASR_MODEL)
        self.transcription_handler = TranscriptionHandler(
            on_transcription_complete_callback=self._handle_transcription_complete,
            on_status_update_callback=self._handle_status_update,
            selected_asr_model=saved_asr_model
        )
        self.audio_handler = AudioHandler(
            on_wake_word_callback=self._handle_wake_word,
            on_speech_end_callback=self._handle_speech_end,
            on_status_update_callback=self._handle_status_update,
        )
        self.hotkey_manager = HotkeyManager(
            on_hotkey_callback=self._handle_hotkey,
            on_status_update_callback=self._handle_status_update,
        )

        # --- Initial Setup ---
        self._handle_status_update("Application initializing...", "grey")
        # Load the default LLM model in a separate thread
        default_llm_key = next(
            (
                key
                for key, value in config.AVAILABLE_LLMS.items()
                if value == config.DEFAULT_LLM
            ),
            None,
        )
        if default_llm_key:
            log_text(
                "INIT", f"Starting background load for default LLM: {default_llm_key}"
            )

            # Define a callback for when loading finishes
            def on_default_load_complete(success):
                if success:
                    log_text(
                        "INIT",
                        f"Default LLM '{default_llm_key}' loaded successfully in background.",
                    )
                    # Optionally update status ONLY if successful, avoid overwriting other messages
                    # self._handle_status_update(f"Default LLM '{default_llm_key}' ready.", "grey")
                else:
                    log_text(
                        "INIT_ERROR",
                        f"Background load failed for default LLM: {default_llm_key}",
                    )
                    self._handle_status_update(
                        f"Error loading default LLM: {default_llm_key}", "red"
                    )

            threading.Thread(
                target=self.llm_handler.load_model,
                args=(default_llm_key, on_default_load_complete),
                daemon=True,
            ).start()
        else:
            log_text(
                "INIT_ERROR",
                f"Default LLM path '{config.DEFAULT_LLM}' not found in AVAILABLE_LLMS configuration.",
            )
            self._handle_status_update(f"Error: Default LLM config invalid.", "red")

    def start_backend(self):
        """Starts the application's background processes (Hotkeys only initially)."""
        self._handle_status_update(
            "Starting background services (Hotkeys only initially)...", "grey"
        )
        
        # Send initial inactive state with grey color to ensure tray starts grey
        initial_state_data = {
            "programActive": False,
            "audioState": "inactive", 
            "isDictating": False,
            "isProofingActive": False,
            "canDictate": False,
            "currentMode": None,
        }
        print(f"STATE:{json.dumps(initial_state_data)}", flush=True)
        
        self.hotkey_manager.start()
        self.start_backend_audio()
        # _update_app_state will be called once audio handler is ready

    def start_backend_audio(self):
        """Starts the audio handler. Call this after config is loaded."""
        # Use start_async to avoid blocking main thread during stream opening
        if (
            not self.audio_handler._audio_thread
            or not self.audio_handler._audio_thread.is_alive()
        ):
            self._handle_status_update("Starting Audio Handler (async)...", "grey")
            self.audio_handler.start_async()  # Call the async starter
            
            # Schedule a microphone status check after a brief delay
            threading.Timer(2.0, self._check_microphone_status_delayed).start()

    def _check_microphone_status_delayed(self):
        """
        Checks microphone status after audio handler startup and provides user feedback.
        Called with a delay to allow the audio handler to complete initialization.
        """
        try:
            # If audio handler failed to start properly, get detailed status
            if (not self.audio_handler._program_active and 
                hasattr(self.audio_handler, 'get_microphone_status_message')):
                
                status_message, status_color = self.audio_handler.get_microphone_status_message()
                
                # Only show detailed error suggestions for actual failures (red), not warnings (orange)
                if status_color == "red":
                    self._handle_status_update(status_message, status_color)
                    
                    # Also log the issue for debugging
                    log_text("MIC_STATUS_CHECK", f"Microphone failed: {status_message}")
                    
                    # Send status with action suggestions for serious errors
                    if "permission" in status_message.lower():
                        self._handle_status_update("💡 Check Privacy & Security settings in System Preferences", "blue")
                    elif "no default input" in status_message.lower() or "no input channels" in status_message.lower():
                        self._handle_status_update("💡 Check System Preferences > Sound > Input to select a microphone", "blue")
                    else:
                        self._handle_status_update("💡 Check System Preferences > Sound settings and restart the application", "blue")
                        
                elif status_color == "orange":
                    # For warnings, just log and show basic status
                    log_text("MIC_STATUS_CHECK", f"Microphone warning: {status_message}")
                    # Only show the basic warning message, not additional suggestions
                    self._handle_status_update(status_message, status_color)
                else:
                    # Green status - microphone is working
                    log_text("MIC_STATUS_CHECK", f"Microphone status: {status_message}")
                    
        except Exception as e:
            log_text("MIC_STATUS_CHECK_ERROR", f"Error checking microphone status: {e}")

    def shutdown(self):
        """Shuts down all components gracefully."""
        self._handle_status_update("Shutting down...", "orange")
        try:
            print("SHUTDOWN_SIGNAL", flush=True)  # Signal Electron we are shutting down
            self.hotkey_manager.set_dictating_state(
                False
            )  # Ensure state is false on shutdown
            self.hotkey_manager.stop()
            self.audio_handler.stop()
            # Ensure PyAudio is terminated if AudioHandler didn't do it
            if hasattr(self.audio_handler, "_p") and self.audio_handler._p:
                self.audio_handler.terminate_pyaudio()

            # Add any other cleanup needed for LLMHandler, TranscriptionHandler if necessary

        except Exception as e:
            log_text("SHUTDOWN_ERROR", f"Error during shutdown: {e}")
            print(f"ERROR: Error during shutdown: {e}", flush=True)
        finally:
            self._handle_status_update("Shutdown complete.", "grey")
            log_text("SHUTDOWN", "Backend shutdown complete.")

    # --- Callback Methods for Handlers ---

    def _handle_status_update(self, message: str, color: str):
        """Receives status updates from handlers and prints them for Electron."""
        # Check if it's an amplitude message and print it directly if so
        if message.startswith("AUDIO_AMP:"):
            print(message, flush=True)
        elif color == "STATE_MSG":
            # This is a detailed STATE JSON message, print it directly
            print(message, flush=True)
            
            # Extract microphone error information if present
            if message.startswith("STATE:"):
                try:
                    state_data = json.loads(message[6:])  # Remove "STATE:" prefix
                    if state_data.get("microphoneError"):
                        # Log the detailed error for debugging
                        log_text("MIC_ERROR_STATE", f"Microphone error: {state_data['microphoneError']}")
                        
                        # Send a user-friendly version to the status display
                        error_msg = state_data["microphoneError"]
                        if len(error_msg) > 80:  # Truncate very long messages
                            error_msg = error_msg[:77] + "..."
                        print(f"STATUS:orange:{error_msg}", flush=True)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    log_text("STATE_PARSE_ERROR", f"Error parsing state message: {e}")
        else:
            # Otherwise, print other status updates with the prefix
            print(f"STATUS:{color}:{message}", flush=True)

    # Removed _process_status_queue method

    def _handle_wake_word(self, command: str):
        """Called by AudioHandler when a wake word is detected."""
        log_text("WAKE_WORD", f"Command received: {command}")

        if not self._program_active:
            self._handle_status_update("Program inactive, wake word ignored.", "orange")
            # Ensure audio handler goes back to activation state if it changed
            self.audio_handler.set_listening_state("activation")
            self._update_app_state()
            return

        if command == config.COMMAND_START_DICTATE:
            self._current_processing_mode = "dictate"
            self._handle_status_update("Dictation started.", "green")
        elif command == config.COMMAND_START_PROOFREAD:  # Corrected indentation
            self._current_processing_mode = "proofread"
            self._handle_status_update("Dictation started (Proofread mode).", "green")
            self._current_prompt = ""  # Set prompt to empty string for proofread
        elif command == config.COMMAND_START_LETTER:
            self._current_processing_mode = "letter"
            self._handle_status_update("Dictation started (Letter mode).", "green")
        else:
            log_text("WAKE_WORD", f"Unknown command from wake word: {command}")
            self.audio_handler.set_listening_state(
                "activation"
            )  # Go back if command invalid
            self._update_app_state()
            return

        # Explicitly set AudioHandler to "dictation" state
        log_text(
            "WAKE_WORD",
            f"Setting AudioHandler state to 'dictation' for command: {command}",
        )
        self.audio_handler.set_listening_state("dictation")
        self.hotkey_manager.set_dictating_state(True)  # <<< SET STATE TO TRUE

        # Update app state (will be printed by _update_app_state)
        log_text(
            "WAKE_WORD", "Updating app state after setting AudioHandler to 'dictation'"
        )
        self._update_app_state()
        # Audio handler should already be in 'dictation' state from its own logic

    def _handle_speech_end(self, audio_data):
        """Called by AudioHandler when speech ends after dictation starts."""
        log_text("SPEECH_END", f"Received {len(audio_data)} audio samples.")
        self._handle_status_update("Speech ended. Transcribing...", "orange")
        self._update_app_state()  # Update state to processing

        # Pass audio data to transcription handler, always using the current selected ASR model
        # Ensure the transcription handler uses the up-to-date selected_asr_model
        self.transcription_handler.selected_asr_model = getattr(
            self, "selected_asr_model", self.transcription_handler.selected_asr_model
        )
        self.transcription_handler.transcribe_audio_data(
            audio_data, config.DEFAULT_WHISPER_PROMPT
        )

    def _handle_transcription_complete(self, raw_text: str, duration: float):
        """Called by TranscriptionHandler when transcription is complete."""
        log_text(
            "TRANSCRIPTION_COMPLETE",
            f"Duration: {duration:.2f}s, Raw text: {raw_text[:100]}....",
        )

        # Process text if available
        processed_text = raw_text.strip() if raw_text else ""
        
        # Apply text processing (filler word removal, etc.)
        if processed_text:
            processed_text = text_processor.clean_text(processed_text)
            
            # Log the processing if any changes were made
            if processed_text != raw_text.strip():
                log_text(
                    "TEXT_PROCESSED",
                    f"Filler words removed. Original: '{raw_text.strip()}' -> Processed: '{processed_text}'",
                )
        
        self._current_transcript = (
            processed_text  # Store for potential proofing
        )
        
        self._last_raw_transcription = processed_text  # Store processed text

        # Send transcription to Electron
        if processed_text:
            print(f"FINAL_TRANSCRIPT:{processed_text}", flush=True)
            
            # Handle different processing modes
            if self._current_processing_mode == "dictate":
                # For dictate mode, copy to clipboard and send to Citrix, then finish
                self._handle_status_update("Sending to Citrix...", "blue")
                send_text_to_citrix(processed_text + " ")  # Add space
                log_text("TRANSCRIPTION_COMPLETE", "Text sent to Citrix via clipboard.")
                
                # Reset state and return to listening for dictate mode
                self._handle_status_update("Transcription complete.", "green")
                self._current_processing_mode = None
                self.hotkey_manager.set_dictating_state(False)
                self.audio_handler.set_listening_state("activation")
                self._update_app_state()
                
            elif self._current_processing_mode == "proofread":
                # For proofread mode, start LLM processing (don't finish yet)
                self._handle_status_update("Starting proofreading with LLM...", "orange")
                if self.llm_handler._model is None:
                    self._handle_status_update("Proofread Error: LLM is not loaded.", "red")
                    # Reset state on error
                    self._current_processing_mode = None
                    self.hotkey_manager.set_dictating_state(False)
                    self.audio_handler.set_listening_state("activation")
                    self._update_app_state()
                else:
                    # Start LLM processing - state will be reset in _handle_llm_complete
                    prompt = self._current_prompt or settings_manager.get_setting('proofingPrompt', 'Proofread and improve this text:')
                    self.llm_handler.process_text(processed_text, "proofread", prompt)
                    
            elif self._current_processing_mode == "letter":
                # For letter mode, start LLM processing (don't finish yet)
                self._handle_status_update("Formatting as letter with LLM...", "orange")
                if self.llm_handler._model is None:
                    self._handle_status_update("Letter Error: LLM is not loaded.", "red")
                    # Reset state on error
                    self._current_processing_mode = None
                    self.hotkey_manager.set_dictating_state(False)
                    self.audio_handler.set_listening_state("activation")
                    self._update_app_state()
                else:
                    # Start LLM processing - state will be reset in _handle_llm_complete
                    prompt = self._current_prompt or settings_manager.get_setting('letterPrompt', 'Format this as a professional letter:')
                    self.llm_handler.process_text(processed_text, "letter", prompt)
            else:
                # Unknown mode or None - just finish
                self._handle_status_update("Transcription complete.", "green")
                self._current_processing_mode = None
                self.hotkey_manager.set_dictating_state(False)
                self.audio_handler.set_listening_state("activation")
                self._update_app_state()
        else:
            # Empty transcription - always finish
            self._handle_status_update("Transcription returned empty.", "orange")
            self._current_processing_mode = None
            self.hotkey_manager.set_dictating_state(False)
            self.audio_handler.set_listening_state("activation")
            self._update_app_state()

    def _handle_llm_complete(
        self, processed_text: str, original_text: str, mode: str, duration: float
    ):
        """Called by LLMHandler when proofreading/letter generation is done."""
        log_text(
            "LLM_COMPLETE",
            f"Mode: {mode}, Duration: {duration:.2f}s, Processed: {processed_text[:100]}...",
        )

        # Send processed text to Electron
        if processed_text.startswith("Error:"):
            # Handle error case - just log and update status, don't send to Citrix
            self._handle_status_update(f"LLM Error ({mode}): {processed_text}", "red")
            log_text("LLM_ERROR", f"LLM processing failed: {processed_text}")
            # Send the error back to Electron for display
            print(
                f"TRANSCRIPTION:ERROR:{processed_text}", flush=True
            )  # Use a distinct prefix for errors
        else:
            # Handle success case
            log_prefix = "PROOFED" if mode == "proofread" else "LETTER"
            print(f"TRANSCRIPTION:{log_prefix}:{processed_text}", flush=True)
            self._handle_status_update(
                f"LLM processing complete ({mode}). Sending to Citrix...", "blue"
            )
            send_text_to_citrix(processed_text + " ")  # Add space
            log_text(
                "LLM_COMPLETE", "Call to send_text_to_citrix completed."
            )  # Added log

        # Reset streaming callback after proofing
        if mode == "proofread" and hasattr(self.llm_handler, "on_processing_stream"):
            self.llm_handler.on_processing_stream = None
        # Reset state and go back to listening (always do this)
        self._current_processing_mode = None
        self.hotkey_manager.set_dictating_state(False)  # <<< SET STATE TO FALSE
        self.audio_handler.set_listening_state("activation")
        self._update_app_state()

    def _handle_hotkey(self, command: str):
        """Called by HotkeyManager when a hotkey is pressed."""
        log_text("HOTKEY", f"Command received: {command}")

        # --- Handle commands that work regardless of program_active state ---
        if command == config.COMMAND_TOGGLE_ACTIVE:
            self._toggle_program_active()
            return  # State change handled within the method

        if command == config.COMMAND_RESTART:
            self._trigger_restart()
            return

        if command == config.COMMAND_SHOW_HOTKEYS:
            self._send_hotkeys_info()
            return

        # Mini mode toggle is handled by Electron window management
        # Python backend doesn't need to do anything for this command via hotkey
        if command == config.COMMAND_TOGGLE_MINI_MODE:
            log_text("HOTKEY", "Toggle Mini Mode hotkey pressed (handled by frontend).")
            return

        # --- Handle commands that only work when program is active ---
        if not self._program_active:
            self._handle_status_update(
                f"Program inactive, hotkey '{command}' ignored.", "orange"
            )
            return

        # Check current audio state before starting new dictation
        current_audio_state = self.audio_handler.get_listening_state()
        if command in [
            config.COMMAND_START_DICTATE,
            config.COMMAND_START_PROOFREAD,
            config.COMMAND_START_LETTER,
        ]:
            log_text("HOTKEY", f"Checking audio state for command: {command}")
            if current_audio_state == "dictation":
                self._handle_status_update(
                    "Already dictating, ignoring start command.", "orange"
                )
                log_text("HOTKEY", "Already dictating, command ignored.")
                return
            if current_audio_state == "processing":
                self._handle_status_update(
                    "Currently processing, ignoring start command.", "orange"
                )
                log_text("HOTKEY", "Currently processing, command ignored.")
                return
            # If in activation, proceed to call _handle_wake_word equivalent
            log_text(
                "HOTKEY",
                f"Audio state is '{current_audio_state}', triggering action for command: {command}",
            )
            self._handle_wake_word(command)  # Simulate wake word detection
            log_text("HOTKEY", f"Called _handle_wake_word with command: {command}")

        elif command == config.COMMAND_STOP_DICTATE:
            if current_audio_state == "dictation":
                self._trigger_stop_dictation()
            else:
                self._handle_status_update(
                    "Not dictating, stop command ignored.", "orange"
                )

        # Add handling for ABORT hotkey if defined in config
        elif (
            command == config.COMMAND_ABORT_DICTATE
        ):  # Assuming you define this in config.py
            if current_audio_state in ["dictation", "processing"]:
                self._trigger_abort_dictation()
            else:
                self._handle_status_update(
                    "Not dictating/processing, abort command ignored.", "orange"
                )

        else:
            log_text("HOTKEY", f"Unhandled hotkey command: {command}")

    # --- Command Handling Methods (Triggered by stdin) ---

    def _trigger_model_change(self, model_key: str):
        """Handles model change command from Electron."""
        log_text("COMMAND", f"Model change requested: {model_key}")
        self._handle_status_update(f"Loading model: {model_key}...", "orange")
        # Load in background thread
        threading.Thread(
            target=self.llm_handler.load_model, args=(model_key,), daemon=True
        ).start()

    def _trigger_proofread(self, text: str, prompt: str):
        """Handles proofread command from Electron."""
        log_text("COMMAND", "Proofread command received.")
        if not text:
            self._handle_status_update("Proofread Error: No text provided.", "red")
            return
        if self.llm_handler._model is None:
            self._handle_status_update("Proofread Error: LLM is not loaded.", "red")
            return
        if self.audio_handler.get_listening_state() != "activation":
            self._handle_status_update(
                "Proofread Error: Cannot proofread while dictating or processing.",
                "orange",
            )
            return

        self._handle_status_update("Processing with LLM (proofread mode)...", "orange")
        self._current_processing_mode = "proofread"  # Set mode for LLM callback
        self._current_prompt = prompt  # Store prompt for LLM handler
        self.llm_handler.process_text(text, "proofread", prompt)

    def _trigger_letter(self, text: str, prompt: str):
        """Handles letter command from Electron."""
        log_text("COMMAND", "Letter command received.")
        if not text:
            self._handle_status_update("Letter Error: No text provided.", "red")
            return
        if self.llm_handler._model is None:
            self._handle_status_update("Letter Error: LLM is not loaded.", "red")
            return
        if self.audio_handler.get_listening_state() != "activation":
            self._handle_status_update(
                "Letter Error: Cannot format as letter while dictating or processing.",
                "orange",
            )
            return

        self._handle_status_update("Processing with LLM (letter mode)...", "orange")
        self._current_processing_mode = "letter"  # Set mode for LLM callback
        self._current_prompt = prompt  # Store prompt for LLM handler
        self.llm_handler.process_text(text, "letter", prompt)

    # Compare functionality remains unimplemented
    def _trigger_compare(self, text: str, prompt: str):
        log_text("COMMAND", "Compare command received (Not Implemented).")
        self._handle_status_update("Compare feature not implemented.", "orange")

    def _trigger_stop_dictation(self):
        """Handles stop dictation command (process audio) from Electron or hotkey."""
        log_text("COMMAND", "Stop Dictation (Process) requested.")
        current_audio_state = (
            self.audio_handler.get_listening_state()
        )  # Get state before
        log_text(
            "DEBUG",
            f"Before force_process_audio, AudioHandler state: {current_audio_state}",
        )

        if current_audio_state == "dictation":
            self._handle_status_update(
                "Stopping dictation manually & processing...", "orange"
            )
            self.audio_handler.force_process_audio()
            new_audio_state = (
                self.audio_handler.get_listening_state()
            )  # Get state after
            log_text(
                "DEBUG",
                f"After force_process_audio, AudioHandler state: {new_audio_state}",
            )
            # State update will happen implicitly via the callbacks triggered by force_process_audio
        else:
            self._handle_status_update(
                f"Not currently dictating (state: {current_audio_state}), stop command ignored.",
                "orange",
            )
            log_text(
                "DEBUG",
                f"Stop command ignored, AudioHandler state: {current_audio_state}",
            )

    def _trigger_abort_dictation(self):
        """Handles abort dictation command (discard audio) from Electron or hotkey."""
        log_text("COMMAND", "Abort Dictation (Discard) requested.")
        self.audio_handler.abort_dictation()  # Call the new method in AudioHandler
        self.hotkey_manager.set_dictating_state(False)  # <<< SET STATE TO FALSE
        self._update_app_state()  # Update state after aborting

    def _trigger_restart(self):
        """Handles restart command from Electron or hotkey."""
        # Confirmation should be handled in Electron frontend if desired
        log_text("COMMAND", "Restart requested.")
        self.shutdown()
        # Use os.execv to replace the current process with a new instance
        try:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            log_text("RESTART_ERROR", f"Failed to restart application: {e}")
            print(f"ERROR: Failed to restart application: {e}", flush=True)
            # Attempt to exit normally if exec fails
            sys.exit(1)

    def _set_proofing_active_state(self, is_active: bool):
        """Updates the proofing active state and notifies Electron."""
        log_text_detail = getattr(config, "log_text_detail_level", 0) >= 2
        if log_text_detail:
            log_text(
                "APP_STATE_DEBUG",
                f"Attempting to set proofing active state to: {is_active}. Current: {self._is_proofing_active}",
            )
        if self._is_proofing_active != is_active:
            self._is_proofing_active = is_active
            log_text(
                "APP_STATE_PROOFING", f"Proofing activity state changed to: {is_active}"
            )
            self._update_app_state()  # Send updated state to Electron
        elif log_text_detail:
            log_text(
                "APP_STATE_DEBUG",
                f"Proofing active state already {is_active}. No change needed.",
            )

    def _send_hotkeys_info(self):
        """Sends hotkey information to Electron."""
        log_text("COMMAND", "Get Hotkeys requested.")
        # Send hotkeys as a structured message (e.g., JSON)
        hotkey_data = {}
        for combo, command in config.HOTKEY_COMBINATIONS.items():
            keys_str_list = []
            for key in combo:
                if isinstance(key, keyboard.KeyCode):
                    char = getattr(key, "char", "?")
                    keys_str_list.append(char)
                elif isinstance(key, keyboard.Key):
                    key_map = {
                        keyboard.Key.cmd: "Cmd",
                        keyboard.Key.cmd_l: "Cmd",
                        keyboard.Key.cmd_r: "Cmd",
                        keyboard.Key.shift: "Shift",
                        keyboard.Key.shift_l: "Shift",
                        keyboard.Key.shift_r: "Shift",
                        keyboard.Key.ctrl: "Ctrl",
                        keyboard.Key.ctrl_l: "Ctrl",
                        keyboard.Key.ctrl_r: "Ctrl",
                        keyboard.Key.alt: "Alt",
                        keyboard.Key.alt_l: "Alt",
                        keyboard.Key.alt_gr: "AltGr",
                        keyboard.Key.space: "Space",
                    }
                    keys_str_list.append(key_map.get(key, key.name))
            keys_str_list.sort(
                key=lambda x: 0 if x in ["Cmd", "Shift", "Ctrl", "Alt"] else 1
            )
            combo_str = "+".join(keys_str_list)
            hotkey_data[combo_str] = command

        print(f"HOTKEYS:{json.dumps(hotkey_data)}", flush=True)

    # Mini mode toggle is handled entirely by Electron, no backend action needed

    # --- State Management ---

    def _toggle_program_active(self):
        """Toggles the overall program active state."""
        self._program_active = not self._program_active
        log_text("STATE_CHANGE", f"Program active set to: {self._program_active}")
        # Inform the audio handler
        self.audio_handler.set_program_active(self._program_active)
        if not self._program_active:
            self.hotkey_manager.set_dictating_state(
                False
            )  # <<< SET STATE TO FALSE if program deactivated
        # Send state update to Electron
        self._update_app_state()

    def _send_ipc_to_electron(self, channel: str, payload: dict = None):
        """Sends a structured IPC message to Electron via stdout."""
        try:
            message = f"IPC_MESSAGE:{channel}:{json.dumps(payload) if payload else ''}"
            print(message, flush=True)
            log_text(
                "IPC_SEND",
                f"Sent to Electron: {channel}, Payload: {str(payload)[:100]}...",
            )
        except Exception as e:
            log_text(
                "IPC_SEND_ERROR",
                f"Error sending IPC message {channel} to Electron: {e}",
            )

    def _update_app_state(self):
        """Determines current state and sends it to Electron."""
        audio_state = self.audio_handler.get_listening_state()
        is_dictating = audio_state == "dictation"
        # Use the AudioHandler's program active state since it knows if microphone is available
        audio_handler_active = self.audio_handler._program_active
        can_dictate = audio_handler_active and audio_state == "activation"

        state_data = {
            "programActive": audio_handler_active,  # Use AudioHandler's state instead of self._program_active
            "audioState": audio_state,  # "activation", "dictation", "processing"
            "isDictating": is_dictating,
            "isProofingActive": self._is_proofing_active,  # Added new state
            "canDictate": can_dictate,
            "currentMode": self._current_processing_mode,  # 'dictate', 'proofread', 'letter', or None
        }
        print(f"STATE:{json.dumps(state_data)}", flush=True)

        # Also send a user-friendly status message based on state
        if not audio_handler_active:
            status_text = "Microphone not available (Hotkeys still work)"
            status_color = "orange"
        elif audio_state == "activation":
            status_text = "Listening for activation words..."
            status_color = "blue"
        elif audio_state == "dictation":
            mode_info = (
                f" ({self._current_processing_mode} mode)"
                if self._current_processing_mode
                else ""
            )
            status_text = f"Listening for dictation...{mode_info}"
            status_color = "green"
        elif audio_state == "processing":
            status_text = "Processing audio..."
            status_color = "orange"
        else:
            status_text = "Unknown state"
            status_color = "red"

        self._handle_status_update(
            status_text, status_color
        )  # This now prints STATUS:color:message


# --- Main Execution ---
if __name__ == "__main__":
    app = None  # Initialize app to None
    try:
        log_text("STARTUP", "Backend application starting...")
        app = Application()
        app.start_backend()  # Start audio, hotkeys

        log_text("STARTUP", "Backend ready. Listening for commands on stdin...")
        print(
            "PYTHON_BACKEND_READY", flush=True
        )  # Signal Electron that backend is ready
        sys.stdout.flush()  # Explicit flush

        # Request configuration from Electron after signaling readiness
        log_text("STARTUP_TRACE", "About to send GET_CONFIG request.")  # ADDED TRACE
        log_text("CONFIG", "Sending GET_CONFIG request to Electron...")
        print("GET_CONFIG", flush=True)
        sys.stdout.flush()  # Explicit flush
        config_loaded = False
        received_config = None

        # Main loop to read commands from stdin
        for line in sys.stdin:
            command_line = line.strip()
            log_text("STDIN", f"Received command: {command_line}")
            # --- CONFIGURATION HANDLING ---
            if command_line.startswith("CONFIG:"):  # Changed command check
                log_text("STARTUP_TRACE", "Received CONFIG: command.")  # Updated TRACE
                config_str = command_line[
                    len("CONFIG:") :
                ]  # Extract JSON from the same line
                try:
                    received_config = json.loads(config_str)
                    # Removed call to non-existent config.load_settings_from_json
                    config_loaded = True
                    log_text("CONFIG", "Configuration received from Electron.")
                    log_text(
                        "STARTUP_TRACE",
                        f"Successfully parsed config JSON: {received_config}",
                    )  # ADDED TRACE

                    # --- Directly update handlers from received_config ---
                    if "wakeWords" in received_config:
                        app.audio_handler.update_wake_words(
                            received_config["wakeWords"]
                        )
                        # Save wake words to persistent settings
                        settings_manager.set_setting("wakeWords", received_config["wakeWords"], save=False)
                    else:
                        log_text(
                            "CONFIG_WARN", "Wake words not found in received config."
                        )

                    if (
                        "proofingPrompt" in received_config
                        and "letterPrompt" in received_config
                    ):
                        app.llm_handler.update_prompts(
                            received_config["proofingPrompt"],
                            received_config["letterPrompt"],
                        )
                        # Save prompts to persistent settings
                        settings_manager.set_setting("proofingPrompt", received_config["proofingPrompt"], save=False)
                        settings_manager.set_setting("letterPrompt", received_config["letterPrompt"], save=False)
                    else:
                        log_text("CONFIG_WARN", "Prompts not found in received config.")

                    if (
                        "selectedProofingModel" in received_config
                        and "selectedLetterModel" in received_config
                    ):
                        app.llm_handler.update_selected_models(
                            received_config["selectedProofingModel"],
                            received_config["selectedLetterModel"],
                        )
                        # Save model selections to persistent settings
                        settings_manager.set_setting("selectedProofingModel", received_config["selectedProofingModel"], save=False)
                        settings_manager.set_setting("selectedLetterModel", received_config["selectedLetterModel"], save=False)
                    else:
                        log_text(
                            "CONFIG_WARN",
                            "Selected models not found in received config.",
                        )

                    # Handle selected ASR model from config
                    if "selectedAsrModel" in received_config:
                        app.transcription_handler.selected_asr_model = received_config[
                            "selectedAsrModel"
                        ]
                        # Save ASR model selection to persistent settings
                        settings_manager.set_setting("selectedAsrModel", received_config["selectedAsrModel"], save=False)
                        log_text(
                            "CONFIG",
                            f"ASR model set to: {received_config['selectedAsrModel']}",
                        )
                    else:
                        log_text(
                            "CONFIG_WARN",
                            "selectedAsrModel not found in received config.",
                        )
                        
                    # Handle filler word filtering settings
                    if "filterFillerWords" in received_config:
                        text_processor.set_filter_enabled(received_config["filterFillerWords"])
                        log_text("CONFIG", f"Filler word filtering set to: {received_config['filterFillerWords']}")
                        
                    if "fillerWords" in received_config:
                        text_processor.set_filler_words(received_config["fillerWords"])
                        log_text("CONFIG", f"Filler words updated: {received_config['fillerWords']}")
                    
                    # Save all settings to file
                    settings_manager.save_settings()
                    # --- End direct updates ---

                    app._handle_status_update(
                        "Configuration applied.", "grey"
                    )  # Changed status message
                    app._update_app_state()  # Reflect state change to Electron

                except json.JSONDecodeError as e:
                    log_text("CONFIG_ERROR", f"JSON decode error on config: {e}")
                    app._handle_status_update(f"Config JSON error: {e}", "red")

            # --- MODEL LIST HANDLING ---
            elif command_line == "MODELS_REQUEST":  # Match command sent by Electron
                log_text(
                    "STARTUP_TRACE", "Received GET_MODELS command."
                )  # Updated TRACE
                log_text(
                    "STARTUP_TRACE",
                    "Calling app.llm_handler.get_available_models_for_electron()...",
                )  # ADDED TRACE
                models_list_data = app.llm_handler.get_available_models_for_electron()
                log_text(
                    "STARTUP_TRACE", f"Got models list data: {models_list_data}"
                )  # ADDED TRACE
                log_text("STARTUP_TRACE", "Calling json.dumps()...")  # ADDED TRACE
                models_json = json.dumps(models_list_data)
                log_text(
                    "STARTUP_TRACE", f"JSON created: {models_json[:100]}..."
                )  # ADDED TRACE
                log_text(
                    "STARTUP_TRACE", "Printing MODELS_LIST to stdout..."
                )  # Corrected TRACE message
                print(f"MODELS_LIST:{models_json}", flush=True)  # Corrected prefix
                sys.stdout.flush()  # Explicit flush
                log_text(
                    "STARTUP_TRACE", f"Sent MODELS_LIST list."
                )  # Corrected TRACE message

            elif command_line == "STOP_DICTATION":
                app._trigger_stop_dictation()

            elif command_line == "ABORT_DICTATION":
                app._trigger_abort_dictation()

            elif command_line == "GET_HOTKEYS":
                app._send_hotkeys_info()

            elif command_line == "TOGGLE_ACTIVE":
                app._toggle_program_active()

            elif command_line == "RESTART_APP":
                app._trigger_restart()

            elif command_line.startswith("SET_APP_STATE:"):
                try:
                    active_status = command_line[len("SET_APP_STATE:") :]
                    active = active_status.lower() == "true"
                    app.audio_handler.set_program_active(active)
                    app._program_active = active  # Update internal state too
                    log_text(
                        "COMMAND", f"Set program active state via command: {active}"
                    )
                    app._update_app_state()  # Reflect state change to Electron
                except ValueError:
                    log_text(
                        "COMMAND_ERROR",
                        f"Invalid active state command format: {command_line}",
                    )
                    app._handle_status_update("Invalid state command.", "red")

            elif command_line.startswith("VOCABULARY_API:"):
                # Handle vocabulary API commands
                try:
                    # Parse the vocabulary command: VOCABULARY_API:messageId:{"command": "...", "data": {...}}
                    parts = command_line.split(":", 2)
                    if len(parts) >= 3:
                        message_id = parts[1]
                        command_data = json.loads(parts[2])
                        
                        # Import and call vocabulary API
                        from src.vocabulary.vocabulary_api import handle_vocabulary_command
                        result = handle_vocabulary_command(
                            command_data.get("command", ""),
                            **command_data.get("data", {})
                        )
                        
                        # Send response back to Electron
                        response_message = f"VOCAB_RESPONSE:{message_id}:{json.dumps(result)}"
                        print(response_message, flush=True)
                        sys.stdout.flush()
                        
                        log_text("VOCAB_API", f"Handled vocabulary command: {command_data.get('command')} - Success: {result.get('success')}")
                    else:
                        log_text("VOCAB_ERROR", f"Invalid vocabulary API command format: {command_line}")
                        
                except json.JSONDecodeError as e:
                    log_text("VOCAB_ERROR", f"JSON decode error in vocabulary API: {e}")
                except Exception as e:
                    log_text("VOCAB_ERROR", f"Error handling vocabulary API: {e}")
                    # Send error response
                    if 'message_id' in locals():
                        error_response = f"VOCAB_RESPONSE:{message_id}:{json.dumps({'success': False, 'error': str(e)})}"
                        print(error_response, flush=True)
                        sys.stdout.flush()

            elif command_line == "start_dictate":
                app._handle_hotkey(config.COMMAND_START_DICTATE)
            elif command_line == "start_proofread":
                app._handle_hotkey(config.COMMAND_START_PROOFREAD)
            elif command_line == "start_letter":
                app._handle_hotkey(config.COMMAND_START_LETTER)

            elif command_line == "SHUTDOWN":
                log_text("COMMAND", "Shutdown command received from Electron.")
                # app.shutdown() # Shutdown is handled in finally block
                break  # Exit the loop and end the backend process

            else:
                log_text("COMMAND_UNKNOWN", f"Unknown command received: {command_line}")
                print(
                    f"UNKNOWN_COMMAND:{command_line}", flush=True
                )  # For debugging in Electron
                sys.stdout.flush()  # Explicit flush

    except BrokenPipeError:
        log_text("PIPE_ERROR", "Broken pipe error (Electron likely closed). Exiting.")
    except Exception as e:
        # Log the exception that occurred during startup or main loop
        log_text(
            "CRITICAL_ERROR", f"Unhandled exception: {e}"
        )  # Add exc_info for traceback
        print(
            f"ERROR: CRITICAL - {e}", flush=True
        )  # Also print basic error for Electron
        sys.stdout.flush()  # Explicit flush
    finally:
        log_text("SHUTDOWN", "Main loop finished or error occurred.")
        if app:  # Check if app was successfully initialized before trying to shut down
            try:
                app.shutdown()
            except Exception as shutdown_e:
                log_text(
                    "SHUTDOWN_ERROR",
                    f"Error during final shutdown: {shutdown_e}",
                    exc_info=True,
                )
                print(f"ERROR: Shutdown error - {shutdown_e}", flush=True)
                sys.stdout.flush()  # Explicit flush
        else:
            log_text(
                "SHUTDOWN", "App object was not initialized, skipping shutdown call."
            )
        print(
            "BACKEND_SHUTDOWN_FINALIZED", flush=True
        )  # Last signal to Electron on hard exit
        sys.stdout.flush()  # Explicit flush
