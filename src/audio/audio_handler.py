# Make imports conditional for CI compatibility
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("[WARN] pyaudio not available in audio_handler.py - using mock")
    class MockPyAudio:
        paInt16 = "paInt16"
        paInputOverflowed = -9981
        paDeviceUnavailable = -9985
        paStreamIsStopped = -9983
        
        class PyAudio:
            def open(self, **kwargs):
                return MockStream()
            
            def terminate(self):
                pass
                
            def get_device_count(self):
                return 1
                
            def get_device_info_by_index(self, index):
                return {
                    'name': 'Mock Audio Device',
                    'maxInputChannels': 2,
                    'defaultSampleRate': 44100.0
                }
                
            def get_default_input_device_info(self):
                return {
                    'name': 'Mock Default Input',
                    'maxInputChannels': 2,
                    'defaultSampleRate': 44100.0,
                    'index': 0
                }
        
        def __init__(self):
            pass
    
    class MockStream:
        def is_active(self):
            return False
        
        def stop_stream(self):
            pass
        
        def close(self):
            pass
            
        def read(self, frames, exception_on_overflow=True):
            return b'\x00' * (frames * 2)  # Mock audio data
            
        def start_stream(self):
            pass
    
    pyaudio = MockPyAudio()

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("[WARN] webrtcvad not available in audio_handler.py - using mock")
    class MockWebRTCVAD:
        class Vad:
            def __init__(self, aggressiveness):
                self.aggressiveness = aggressiveness
            
            def is_speech(self, frame, sample_rate):
                return False  # Mock always returns no speech
    
    webrtcvad = MockWebRTCVAD()

import collections

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARN] numpy not available in audio_handler.py - using mock")
    class MockNumpy:
        @staticmethod
        def frombuffer(data, dtype=None):
            return MockArray([])
        
        @staticmethod
        def array(data):
            return MockArray(data)
        
        @staticmethod
        def concatenate(arrays):
            return MockArray([])
        
        int16 = "int16"
    
    class MockArray:
        def __init__(self, data):
            self.data = data
            self.size = len(data) if hasattr(data, '__len__') else 0
        
        def tobytes(self):
            return b"mock_audio_data"
        
        def astype(self, dtype):
            return self
    
    np = MockNumpy()

import threading
import time
import json
import phonetics
import sys
import subprocess
import os

try:
    from vosk import Model as VoskModel, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("[WARN] vosk not available in audio_handler.py - using mock")
    class MockVoskModel:
        def __init__(self, path):
            self.path = path
    
    class MockKaldiRecognizer:
        def __init__(self, model, sample_rate):
            pass
        
        def SetWords(self, value):
            pass
        
        def AcceptWaveform(self, data):
            return False
        
        def Result(self):
            return '{"text": "[MOCK VOSK]"}'
        
        def FinalResult(self):
            return '{"text": "[MOCK VOSK FINAL]"}'
    
    VoskModel = MockVoskModel
    KaldiRecognizer = MockKaldiRecognizer

from src.utils.utils import log_text
from src.memory_monitor import (
    memory_monitor,
    start_memory_monitoring,
    stop_memory_monitoring,
)
from src.performance_optimizer import start_perf_timer, end_perf_timer

# Import configuration constants
from src.config import config


class AudioHandler:
    """Handles audio input, VAD, wake word detection, and buffering."""

    def __init__(
        self,
        on_wake_word_callback=None,
        on_speech_end_callback=None,
        on_status_update_callback=None,
    ):
        """
        Initializes the AudioHandler.

        Args:
            on_wake_word_callback: Function to call when a wake word is detected.
                                   Receives the detected command (e.g., config.COMMAND_START_DICTATE).
            on_speech_end_callback: Function to call when speech ends after dictation starts.
                                     Receives the recorded audio data (numpy array).
            on_status_update_callback: Function to call to update the application status display.
                                        Receives status text (str) and color (str).
        """
        self.on_wake_word = on_wake_word_callback
        self.on_speech_end = on_speech_end_callback
        self.on_status_update = on_status_update_callback

        self._listening_state = "inactive"  # Initial state
        self._program_active = False  # Start as FALSE until microphone is available
        self._audio_thread = None
        self._stop_event = threading.Event()
        self._vad_lock = threading.Lock()
        
        # Microphone availability state
        self._mic_availability_checked = False
        self._mic_error_details = None
        self._last_mic_check_time = 0
        self._mic_check_interval = 30  # seconds between availability checks

        # Audio parameters from config
        self._sample_rate = config.SAMPLE_RATE
        self._frame_duration_ms = config.FRAME_DURATION_MS
        self._frame_size = config.FRAME_SIZE
        self._audio_format = pyaudio.paInt16
        self._channels = config.CHANNELS

        # Check if we're in CI environment (missing key dependencies)
        if not PYAUDIO_AVAILABLE or not WEBRTCVAD_AVAILABLE or not VOSK_AVAILABLE:
            self._log_status("Audio handler initialized in CI mode - dependencies mocked", "orange")
            # Set up mock components
            self._vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
            self._vosk_model = None
            self._recognizer = None
            self._vosk_ready_event = threading.Event()
            self._model_lock = threading.Lock()
            self._p = pyaudio.PyAudio() if PYAUDIO_AVAILABLE else pyaudio
            self._stream = None
        else:
            # VAD setup
            self._vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)

            # Vosk setup with thread safety
            self._vosk_model = None
            self._recognizer = None
            self._vosk_ready_event = threading.Event()
            self._model_lock = threading.Lock()

            # PyAudio setup
            self._p = pyaudio.PyAudio()
            self._stream = None

        # Buffering
        self._ring_buffer_size = int(
            config.RING_BUFFER_DURATION_MS / self._frame_duration_ms
        )
        self._ring_buffer = collections.deque(maxlen=self._ring_buffer_size)
        self._voiced_frames = []
        self._triggered = False
        self._silence_start_time = None
        self._wake_words_config = (
            {}
        )  # Store {metaphone: command} mapping - Will be populated by update_wake_words
        self._vosk_ready_event = threading.Event()  # Event to signal Vosk readiness

        # Memory monitoring
        self._last_memory_log = 0
        self._memory_log_interval = 5  # seconds between memory logs

        # Start memory monitoring
        # start_memory_monitoring()

    def load_vosk_model_async(self):
        """Loads the Vosk model in the background with thread safety."""
        # Check if we're in CI mode (missing Vosk)
        if not VOSK_AVAILABLE:
            self._log_status("Vosk model loading skipped - not available in CI environment", "orange")
            self._vosk_ready_event.set()  # Signal ready even though mocked
            return

        import gc

        with self._model_lock:
            if self._vosk_model is not None:  # Skip if already loaded
                return
            # Log before loading
            memory_monitor.log_operation(
                "vosk_load_start", {"threads": threading.active_count()}
            )
            try:
                # Check if Vosk model directory exists and contains files
                import os
                if not os.path.exists(config.VOSK_MODEL_PATH):
                    raise Exception(f"Vosk model directory does not exist: {config.VOSK_MODEL_PATH}")
                
                # Check if directory contains model files (look for common Vosk model files)
                model_files = os.listdir(config.VOSK_MODEL_PATH)
                required_files = ['am', 'conf', 'graph']
                missing_files = [f for f in required_files if f not in model_files]
                
                if missing_files:
                    raise Exception(f"Vosk model directory is missing required files: {missing_files}")
                
                log_text(
                    "VOSK_LOAD",
                    f"Starting Vosk model load from path: {config.VOSK_MODEL_PATH}",
                )
                self._vosk_model = VoskModel(config.VOSK_MODEL_PATH)
                self._recognizer = KaldiRecognizer(self._vosk_model, self._sample_rate)
                self._recognizer.SetWords(
                    False
                )  # We only care about the final result for wake words
                self._vosk_ready_event.set()  # Signal that Vosk is ready
                self._log_status("Vosk model loaded successfully.", "grey")
                log_text("VOSK_LOAD", "Vosk model loaded successfully.")
                # Log after loading
                memory_monitor.log_operation(
                    "vosk_load_end", {"threads": threading.active_count()}
                )
                
                # If audio stream is open and we are in 'preparing', switch to 'activation'
                if (
                    self._stream
                    and self._stream.is_active()
                    and self._listening_state == "preparing"
                ):
                    print(
                        "[DEBUG] Setting listening state to 'activation' in load_vosk_model_async (Vosk just loaded)"
                    )
                    self.set_listening_state("activation")
                    # Status message is already sent by set_listening_state(), no need to duplicate
            except Exception as e:
                error_msg = str(e)
                # Check for various Vosk model file missing errors
                if any(phrase in error_msg.lower() for phrase in [
                    "does not contain model files",
                    "folder",
                    "failed to create a model",
                    "model files",
                    "missing required files",
                    "does not exist"
                ]):
                    self._log_status("Vosk model files not found. Please download the Vosk model.", "red")
                    self._log_status("Visit: https://alphacephei.com/vosk/models", "orange")
                    self._log_status("Download a model (e.g., vosk-model-small-en-us-0.15) and extract to 'vosk/' directory", "orange")
                else:
                    self._log_status(f"Error loading Vosk model: {e}", "red")
                
                log_text(
                    "VOSK_LOAD_ERROR", f"Error loading Vosk model: {e}"
                )
                # Set the event even on failure to prevent deadlocks
                self._vosk_ready_event.set()
                memory_monitor.log_operation(
                    "vosk_load_error",
                    {"threads": threading.active_count(), "error": str(e)},
                )

    def _log_status(self, message, color="black"):
        """Helper to call the status update callback if available."""
        print(f"AudioHandler Status: {message}")  # Also print to console
        if self.on_status_update:
            self.on_status_update(message, color)

    def _log_memory_usage(self):
        """Log memory usage if enough time has passed since the last log."""
        current_time = time.time()
        if current_time - self._last_memory_log >= self._memory_log_interval:
            try:
                stats = memory_monitor.get_memory_stats(self)
                if stats:
                    # Add audio-specific stats
                    stats.audio_frames = len(self._voiced_frames)
                    stats.ring_buffer_size = (
                        len(self._ring_buffer) if hasattr(self, "_ring_buffer") else 0
                    )
                    stats.voiced_frames_size = (
                        sum(sys.getsizeof(frame) for frame in self._voiced_frames)
                        / (1024 * 1024)  # MB
                        if self._voiced_frames
                        else 0
                    )
                    memory_monitor._log_stats(stats)
                self._last_memory_log = current_time
            except Exception as e:
                print(f"Error in _log_memory_usage: {e}")

    def start(self):
        """DEPRECATED: Use start_async. Starts the audio processing thread."""
        # This method is kept for potential direct use but start_async is preferred
        # to avoid blocking the main thread during stream opening.
        if self._audio_thread is not None and self._audio_thread.is_alive():
            self._log_status("Audio thread already running (start_async).", "orange")
            return

        self.set_listening_state("activation")  # Start in activation mode

    def start_async(self):
        """Starts the audio stream opening and processing thread asynchronously."""
        if self._audio_thread is not None and self._audio_thread.is_alive():
            self._log_status("Audio thread already running (start_async).", "orange")
            return

        # Run the blocking parts (stream opening) and thread start in a separate thread
        thread = threading.Thread(target=self._start_worker, daemon=True)
        thread.start()

    def _start_worker(self):
        """Worker function to open stream and start the main loop thread."""
        try:
            # Check microphone availability for informational purposes
            # but don't block on advisory warnings  
            # Skip test stream during startup to prevent macOS microphone indicator flashing
            is_available, availability_message, status_color = self.check_microphone_availability(skip_test_stream=True)
            
            if not is_available and status_color == "red":
                # Only block on serious errors (red status), not warnings (orange)
                self._log_status(availability_message, status_color)
                log_text("AUDIO_START_ERROR", f"Microphone check failed: {availability_message}")
                
                # Send a state update indicating microphone is not available
                if self.on_status_update:
                    state_payload = {
                        "audioState": "inactive",
                        "isDictating": False,
                        "programActive": False,
                        "microphoneError": availability_message
                    }
                    json_state_payload = json.dumps(state_payload)
                    self.on_status_update(f"STATE:{json_state_payload}", "STATE_MSG")
                
                return
            elif not is_available:
                # Orange status (advisory warning) - log but continue trying
                self._log_status(f"Advisory: {availability_message}", status_color)
                log_text("AUDIO_START_WARNING", f"Microphone warning (continuing): {availability_message}")
            else:
                # Green status - all good
                self._log_status(availability_message, status_color)
                log_text("AUDIO_START_INFO", f"Microphone check passed: {availability_message}")
            
            log_text("AUDIO_START", "Opening audio stream...")
            self._stream = self._p.open(
                format=self._audio_format,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._frame_size,
            )
            self._stream.start_stream()
            
            # Keep programActive as False until fully ready
            # Only set to True when transitioning to activation state
            self._log_status("Audio stream opened.", "grey")
            log_text("AUDIO_START", "Audio stream opened successfully.")

            # Now start the main audio processing thread
            self._audio_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._audio_thread.start()
            self._log_status("Audio processing thread started.", "grey")

            print(
                "[DEBUG] Setting listening state to 'preparing' in _start_worker (waiting for Vosk)"
            )
            self.set_listening_state("preparing")
            
            # Load Vosk model asynchronously
            print("[DEBUG] Starting Vosk model loading in _start_worker")
            vosk_thread = threading.Thread(target=self.load_vosk_model_async, daemon=True)
            vosk_thread.start()

        except Exception as e:
            # Enhanced error handling with specific PyAudio error detection
            error_message = str(e)
            detailed_message = f"Error opening audio stream: {error_message}"
            
            # Classify the error for better user feedback
            if hasattr(e, 'errno'):
                if e.errno == getattr(pyaudio, 'paDeviceUnavailable', -9985):
                    detailed_message = "Microphone device is currently unavailable (may be in use by another application)"
                elif e.errno == getattr(pyaudio, 'paInputOverflowed', -9981):
                    detailed_message = "Audio input buffer overflow (system too busy)"
                elif e.errno == getattr(pyaudio, 'paStreamIsStopped', -9983):
                    detailed_message = "Audio stream failed to start properly"
            
            # Check for common error patterns
            if "Device unavailable" in error_message:
                # Now check for conflicts to provide specific guidance
                conflict_info = self._check_for_audio_conflicts()
                if conflict_info:
                    detailed_message = f"Microphone device unavailable - {conflict_info}"
                else:
                    detailed_message = "Microphone device unavailable - likely in use by another application"
            elif "Permission denied" in error_message or "access" in error_message.lower():
                detailed_message = "Microphone access denied - check System Preferences > Security & Privacy > Microphone"
            elif "No such device" in error_message or "device not found" in error_message.lower():
                detailed_message = "No microphone device found - check System Preferences > Sound > Input"
            
            self._log_status(detailed_message, "red")
            log_text("AUDIO_START_ERROR", detailed_message)
            
            # Keep program_active as False since microphone is not available
            if self._stream:
                try:
                    self._stream.close()
                except:
                    pass
                self._stream = None
            
            # Send detailed error state to UI
            if self.on_status_update:
                state_payload = {
                    "audioState": "inactive",
                    "isDictating": False,
                    "programActive": False,
                    "microphoneError": detailed_message
                }
                json_state_payload = json.dumps(state_payload)
                self.on_status_update(f"STATE:{json_state_payload}", "STATE_MSG")

    def stop(self):
        """Stops audio processing and cleans up resources."""
        import gc

        memory_monitor.log_operation(
            "audio_stop_start", {"threads": threading.active_count()}
        )
        self._stop_event.set()
        self._program_active = False

        # Stop the audio stream if it exists
        if hasattr(self, "_stream") and self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                log_text(
                    "AUDIO_STOP_ERROR",
                    f"Error stopping audio stream: {e}",
                )

        # Terminate PyAudio
        if hasattr(self, "_p") and self._p:
            try:
                self._p.terminate()
            except Exception as e:
                log_text(
                    "AUDIO_TERMINATE_ERROR",
                    f"Error terminating PyAudio: {e}",
                )

        # Clean up Vosk model and recognizer with thread safety
        with self._model_lock:
            if hasattr(self, "_recognizer") and self._recognizer is not None:
                try:
                    del self._recognizer
                    self._recognizer = None
                    memory_monitor.log_operation(
                        "vosk_recognizer_deleted", {"threads": threading.active_count()}
                    )
                except Exception as e:
                    log_text(
                        "VOSK_CLEANUP_ERROR",
                        f"Error cleaning up recognizer: {e}",
                    )

            if hasattr(self, "_vosk_model") and self._vosk_model is not None:
                try:
                    del self._vosk_model
                    self._vosk_model = None
                    memory_monitor.log_operation(
                        "vosk_model_deleted", {"threads": threading.active_count()}
                    )
                except Exception as e:
                    log_text(
                        "VOSK_CLEANUP_ERROR",
                        f"Error cleaning up Vosk model: {e}",
                    )

            # Clear the ready event for next start
            self._vosk_ready_event.clear()

        # Force garbage collection, log result
        collected = gc.collect()
        memory_monitor.log_operation(
            "gc_collect", {"collected": collected, "threads": threading.active_count()}
        )

        # Stop memory monitoring
        stop_memory_monitoring()

        # Clear buffers
        self._ring_buffer.clear()
        self._voiced_frames.clear()
        memory_monitor.log_operation(
            "audio_stop_end", {"threads": threading.active_count()}
        )

        log_text("AUDIO_HANDLER", "Audio handler stopped and cleaned up")
        self._audio_thread = None
        self.set_listening_state("inactive")  # Ensure state is inactive

    def terminate_pyaudio(self):
        """Explicitly terminate PyAudio. Call this on application exit."""
        if self._p:
            self._p.terminate()
            self._log_status("PyAudio terminated.", "green")
            self._p = None

    def set_program_active(self, active: bool):
        """Sets the overall program active state, affecting audio processing."""
        self._program_active = active
        if not active:
            # If becoming inactive, force the state and status update
            self.set_listening_state("inactive")
        elif self._listening_state == "inactive":
            # If becoming active and was previously inactive, go back to preparing mode
            self.set_listening_state("preparing")

    def set_listening_state(self, state: str):
        """
        Sets the current listening state (activation, dictation, processing, inactive, preparing)
        and sends both a simple status update for the status bar and a comprehensive STATE JSON
        message to the frontend for more detailed UI logic.
        """
        if state not in [
            "activation",
            "dictation",
            "processing",
            "inactive",
            "preparing",
        ]:
            self._log_status(f"Invalid listening state requested: {state}", "red")
            return

        # Handle the case where the program is globally inactive
        # Allow transition TO "preparing", "inactive", and "activation" even when program_active is False
        # Only "dictation" and "processing" require program_active to be True
        if not self._program_active and state not in ["inactive", "preparing", "activation"]:
            self._listening_state = "inactive"
            self._log_status("Program is inactive. Cannot change state.", "orange")
            # Optionally call status update callback here if needed for UI consistency
            if self.on_status_update:
                self.on_status_update("Program is inactive", "orange")
            return

        self._listening_state = state
        # Reset buffering state when changing state, except when moving to 'processing'
        if state != "processing":
            self._reset_buffering()

        # Update status based on the new state
        if state == "activation":
            self._program_active = True  # Only set active when ready for activation
            self._log_status("Listening for activation words...", "blue")
        elif state == "dictation":
            self._log_status("Listening for dictation...", "green")
        elif state == "processing":
            self._log_status("Processing audio...", "orange")
        elif state == "inactive":
            self._program_active = False  # Set inactive when truly inactive
            self._log_status("Microphone is not listening.", "grey")
        elif state == "preparing":
            # Keep _program_active as False during preparing - microphone not ready for use yet
            self._log_status("Preparing to listen (initializing audio/Vosk)...", "grey")

        # Send detailed STATE update to Electron for UI logic (e.g., hiding proofing UI)
        if self.on_status_update:
            is_dictating_bool = self._listening_state == "dictation"
            state_payload = {
                "audioState": self._listening_state,
                "isDictating": is_dictating_bool,
                "programActive": self._program_active,
                # currentMode is not managed by AudioHandler, frontend can manage/infer if needed
            }
            try:
                json_state_payload = json.dumps(state_payload)
                # Use a special "color" to indicate this is a raw STATE message
                self.on_status_update(f"STATE:{json_state_payload}", "STATE_MSG")
            except Exception as e:
                log_text(
                    "AUDIO_HANDLER_STATE_SEND_ERROR",
                    f"Error sending detailed STATE update: {e}",
                )

    def get_listening_state(self) -> str:
        """Returns the current listening state."""
        return self._listening_state

    def abort_dictation(self):
        """Stops listening and discards any buffered audio, returning to activation state."""
        if (
            self._listening_state == "dictation"
            or self._listening_state == "processing"
        ):
            self._log_status("Aborting current dictation/processing.", "orange")
            self.set_listening_state("activation")  # This also calls _reset_buffering
        else:
            self._log_status("No active dictation/processing to abort.", "blue")

    def update_wake_words(self, wake_words_list: list):
        """Updates the wake words used for detection based on loaded settings."""
        # Use log_text for consistency with main.py logging
        from src.utils.utils import log_text  # Import locally if not already imported globally

        log_text(
            "CONFIG",
            f"AudioHandler received wake words update request: {wake_words_list}",
        )
        self._log_status(
            f"Updating wake words to: {wake_words_list}", "grey"
        )  # Keep status update for UI
        self._update_wake_words_internal(wake_words_list)

    def _update_wake_words_internal(self, wake_words_obj: dict):
        """Internal helper to process and store wake words from the structured object."""
        from src.utils.utils import log_text  # Ensure log_text is available

        new_wake_words_config = {}
        log_text("CONFIG", f"Processing wake words object: {wake_words_obj}")

        # Define mapping from object keys to command constants
        command_map = {
            "dictate": config.COMMAND_START_DICTATE,
            "proofread": config.COMMAND_START_PROOFREAD,
            "letter": config.COMMAND_START_LETTER,
        }

        if not isinstance(wake_words_obj, dict):
            log_text(
                "CONFIG_ERROR",
                f"Received wake words data is not a dictionary: {type(wake_words_obj)}",
            )
            self._wake_words_config = {}  # Reset config on error
            return

        # Iterate through the categories (dictate, proofread, letter)
        for category, words in wake_words_obj.items():
            command = command_map.get(category)
            if not command:
                log_text(
                    "CONFIG_WARN",
                    f"Unknown wake word category '{category}' found in settings.",
                )
                continue

            if not isinstance(words, list):
                log_text(
                    "CONFIG_WARN",
                    f"Wake words for category '{category}' is not a list: {type(words)}",
                )
                continue

            # Process each word in the category's list
            for word in words:
                word_lower = str(word).lower().strip()  # Ensure string conversion
                if not word_lower:
                    continue
                try:
                    metaphone_key = phonetics.metaphone(word_lower)
                    # Store metaphone -> (original_word, command)
                    # Check for conflicts (same metaphone mapped to different commands) - last one wins here
                    if (
                        metaphone_key in new_wake_words_config
                        and new_wake_words_config[metaphone_key][1] != command
                    ):
                        log_text(
                            "CONFIG_WARN",
                            f"Metaphone key '{metaphone_key}' for word '{word_lower}' conflicts with previous command mapping. Overwriting.",
                        )
                    new_wake_words_config[metaphone_key] = (word_lower, command)
                except Exception as e:
                    log_text(
                        "CONFIG_ERROR",
                        f"Error processing metaphone for word '{word_lower}': {e}",
                    )

        self._wake_words_config = new_wake_words_config
        log_text(
            "CONFIG",
            f"AudioHandler processed wake words config: {self._wake_words_config}",
        )
        self._log_status(
            f"Processed wake words config: {len(self._wake_words_config)} entries",
            "grey",
        )

    def _reset_buffering(self):
        """Resets the VAD buffering state and conflict detection counters."""
        self._ring_buffer.clear()
        self._voiced_frames = []
        self._triggered = False
        self._silence_start_time = None
        
        # Reset conflict detection state
        self._silent_frame_count = 0  # Updated from _zero_frame_count
        if hasattr(self, '_conflict_warning_sent'):
            del self._conflict_warning_sent
        if hasattr(self, '_low_amp_warning_sent'):
            del self._low_amp_warning_sent
        self._low_amp_count = 0
        self._main_loop_silent_count = 0  # Updated from _main_loop_zero_count
        if hasattr(self, '_main_loop_conflict_logged'):
            del self._main_loop_conflict_logged
        # print("Buffering state and conflict detection reset.") # Debug log

    def _optimize_buffer_memory(self):
        """Optimizes buffer memory usage to prevent unbounded growth during long dictation."""
        # IMPORTANT: Don't truncate audio during active dictation as it will cause 
        # transcription of only the last portion of long dictations
        
        # For now, just log buffer stats without truncating to preserve full dictation audio
        # Maximum voiced frames for monitoring (roughly 60 seconds at 50ms frames = 1200 frames)
        MONITORING_THRESHOLD = 1200
        
        if len(self._voiced_frames) > MONITORING_THRESHOLD:
            # Log current buffer size for monitoring without truncating
            total_size_mb = sum(sys.getsizeof(frame) for frame in self._voiced_frames) / (1024 * 1024)
            buffer_duration_sec = len(self._voiced_frames) * 0.05  # 50ms per frame
            
            log_text("AUDIO_BUFFER_MONITOR", 
                    f"Long dictation detected: {len(self._voiced_frames)} frames "
                    f"({buffer_duration_sec:.1f}s), using {total_size_mb:.1f}MB memory")
            
            # Only warn if we're getting extremely long (5+ minutes)
            if len(self._voiced_frames) > 6000:  # 5 minutes
                log_text("AUDIO_BUFFER_WARNING", 
                        f"Very long dictation: {buffer_duration_sec:.1f}s - "
                        f"consider breaking into smaller segments for better performance")
        
        # Optional: Force garbage collection for other objects but preserve audio frames
        if len(self._voiced_frames) % 200 == 0:  # Every ~10 seconds
            import gc
            collected = gc.collect()
            if collected > 0:
                log_text("AUDIO_BUFFER_GC", f"Garbage collected {collected} objects during long dictation")

    def _calculate_buffer_stats(self):
        """Calculate and return current buffer statistics for monitoring."""
        ring_buffer_size = len(self._ring_buffer) if hasattr(self, "_ring_buffer") else 0
        voiced_frames_count = len(self._voiced_frames)
        voiced_frames_size_mb = (
            sum(sys.getsizeof(frame) for frame in self._voiced_frames) / (1024 * 1024)
            if self._voiced_frames else 0
        )
        
        return {
            'ring_buffer_frames': ring_buffer_size,
            'voiced_frames_count': voiced_frames_count,
            'voiced_frames_size_mb': voiced_frames_size_mb,
            'max_ring_buffer': self._ring_buffer_size,
            'is_triggered': self._triggered
        }

    def force_process_audio(self):
        """Forces processing of currently buffered audio frames."""
        if self._listening_state not in ["dictation", "processing"]:
            self._log_status("No voiced frames to force process.", "blue")
            # Ensure we return to activation state if called inappropriately
            if self._listening_state != "activation":
                self.set_listening_state("activation")
            return

        self._log_status("Force processing buffered audio...", "orange")
        self.set_listening_state("processing")  # Set state to processing

        # Important: Create a copy of the frames before resetting
        frames_to_process = list(self._voiced_frames)
        audio_data = (
            np.concatenate(frames_to_process)
            if frames_to_process
            else np.array([], dtype=np.int16)
        )

        # Reset buffering state *after* copying data
        self._reset_buffering()

        if self.on_speech_end and audio_data.size > 0:
            # Call the callback with the captured audio
            self._log_status(
                f"Calling on_speech_end with {audio_data.size} samples.", "blue"
            )
            self.on_speech_end(audio_data)
        else:
            # If no data or no callback, just return to activation
            if not self.on_speech_end:
                self._log_status("on_speech_end callback is None.", "red")
            if audio_data.size == 0:
                self._log_status("audio_data is empty.", "orange")
            self._log_status(
                "No audio data after force process or no callback, returning to activation.",
                "orange",
            )
            self.set_listening_state("activation")

    def _handle_wake_word(self, recognized_text):
        """Processes recognized text to check for configured wake words."""
        from src.utils.utils import log_text  # Ensure log_text is available

        recognized_text_raw = (
            recognized_text  # Keep original case for logging if needed
        )
        recognized_text = recognized_text.lower().strip()
        if not recognized_text:
            return

        # --- Wake Word Debug Logging ---
        try:
            recognized_sound = phonetics.metaphone(recognized_text)
            log_text(
                "WAKE_WORD_DEBUG",
                f"Vosk recognized: '{recognized_text_raw}' -> Lower: '{recognized_text}' -> Metaphone: '{recognized_sound}'",
            )
            log_text(
                "WAKE_WORD_DEBUG",
                f"Comparing against config: {self._wake_words_config}",
            )
        except Exception as e:
            log_text("WAKE_WORD_DEBUG", f"Error during wake word debug logging: {e}")
        # --- End Debug Logging ---

        # Use simple substring matching for now, consider metaphone if needed
        # recognized_sound = phonetics.metaphone(recognized_text) # Keep if using metaphone matching

        command = None
        detected_word = None

        # Iterate through configured wake words (using simple substring matching)
        log_text(
            "WAKE_WORD_DEBUG",
            f"Checking wake word. Current config dict: {self._wake_words_config}",
        )  # ADDED LOG
        for meta_key, (original_word, cmd) in self._wake_words_config.items():
            # Simple substring check - might need refinement for robustness
            # Example: if original_word in recognized_text:
            # Using metaphone matching:
            # Calculate metaphone for recognized text *once* before the loop if using metaphone matching
            recognized_sound = phonetics.metaphone(recognized_text)
            if meta_key == recognized_sound:  # Use exact metaphone match
                command = cmd
                detected_word = original_word
                log_text(
                    "WAKE_WORD_DEBUG",
                    f"MATCH FOUND: Recognized sound '{recognized_sound}' == Config key '{meta_key}' (Word: '{original_word}', Command: {cmd})",
                )
                self._log_status(f"Wake word '{detected_word}' detected.", "green")
                break  # Stop after first match
            # else: # Optional: Log non-matches for debugging
            #    log_text("WAKE_WORD_DEBUG", f"NO MATCH: Recognized sound '{recognized_sound}' != Config key '{meta_key}' (Word: '{original_word}')")

        if command and self.on_wake_word:
            log_text("WAKE_WORD_DEBUG", f"WAKE WORD DETECTED! Command: {command}, detected word: {detected_word}")
            log_text("WAKE_WORD_DEBUG", f"Current state before transition: {self._listening_state}")
            self.set_listening_state("dictation")  # Switch state immediately
            log_text("WAKE_WORD_DEBUG", f"State after set_listening_state('dictation'): {self._listening_state}")
            log_text(
                "WAKE_WORD_ACTION",
                f"Invoking on_wake_word callback with command: {command}",
            )  # Added log
            self.on_wake_word(command)  # Notify the main application
            log_text("WAKE_WORD_DEBUG", f"on_wake_word callback completed")

    def _process_dictation_frame(self, frame_bytes):
        """Processes a single audio frame during the 'dictation' state using VAD."""
        # Check if frame data is valid first
        if not frame_bytes or len(frame_bytes) == 0:
            log_text("AUDIO_DEBUG", "Empty frame received during dictation")
            # Send zero amplitude for empty frames
            if self.on_status_update:
                self.on_status_update("AUDIO_AMP:0", "blue")
            return
        
        # Check if frame is the expected size
        expected_frame_size = self._frame_size * 2  # 2 bytes per sample for int16
        if len(frame_bytes) != expected_frame_size:
            log_text("AUDIO_DEBUG", f"Unexpected frame size: {len(frame_bytes)}, expected: {expected_frame_size}")
            # Send zero amplitude for malformed frames
            if self.on_status_update:
                self.on_status_update("AUDIO_AMP:0", "blue")
            return
            
        # Convert frame data first
        frame_data = np.frombuffer(frame_bytes, dtype=np.int16)
        
        # Check for Safari-style conflict: only truly zero/empty frames (much more permissive)
        max_amplitude = np.abs(np.max(frame_data)) if frame_data.size > 0 else 0
        is_essentially_silent = np.all(frame_data == 0)  # Only skip completely zero frames, let VAD handle the rest
        
        if is_essentially_silent:
            # Track silent frames but reduce logging verbosity
            if hasattr(self, '_silent_frame_count'):
                self._silent_frame_count += 1
            else:
                self._silent_frame_count = 1
                
            # If we get too many silent frames in a row, warn about possible issues (but be less aggressive)
            if self._silent_frame_count > 100:  # About 2 seconds of silent frames - higher threshold
                if not hasattr(self, '_conflict_warning_sent'):
                    self._conflict_warning_sent = True
                    # Only log once per dictation session, not per frame
                    log_text("AUDIO_CONFLICT", f"Sustained silent audio during dictation ({self._silent_frame_count} frames)")
                    
                    # Check for active conflicts but don't immediately show notification
                    conflict_info = self._check_for_audio_conflicts()
                    if conflict_info:
                        log_text("AUDIO_CONFLICT", f"Possible conflict: {conflict_info}")
                        
            # Send zero amplitude for silent frames
            if self.on_status_update:
                self.on_status_update("AUDIO_AMP:0", "blue")
            return
        else:
            # Reset silent frame counter and conflict warning when we get valid data
            self._silent_frame_count = 0
            if hasattr(self, '_conflict_warning_sent'):
                del self._conflict_warning_sent
        
        try:
            with self._vad_lock:
                # Performance optimization: Skip VAD for very low amplitude frames
                # This reduces CPU usage during obvious silence periods
                skip_vad = False
                if max_amplitude < 5:  # Very quiet audio, likely silence
                    # Check recent amplitude history to confirm consistent low volume
                    if hasattr(self, '_recent_low_amp_count'):
                        self._recent_low_amp_count += 1
                        if self._recent_low_amp_count > 10:  # 10 consecutive low-amp frames
                            skip_vad = True
                            is_speech = False  # Assume silence
                    else:
                        self._recent_low_amp_count = 1
                else:
                    # Reset low amplitude counter when we get louder audio
                    self._recent_low_amp_count = 0
                
                if not skip_vad:
                    is_speech = self._vad.is_speech(frame_bytes, self._sample_rate)
                    # Log VAD performance occasionally for monitoring
                    if len(self._voiced_frames) % 100 == 0:
                        log_text("VAD_PERF", f"VAD processed frame, amplitude: {max_amplitude:.1f}, speech: {is_speech}")
                # Remove frequent VAD debug logging during normal operation
        except Exception as vad_error:
            self._log_status(f"VAD Error: {vad_error}", "red")
            is_speech = False  # Assume not speech on error

        # Calculate amplitude with better error handling
        try:
            amplitude = np.clip(max_amplitude / 100.0, 0, 100)
            
            # Track low amplitude but reduce logging verbosity  
            if hasattr(self, '_low_amp_count'):
                if amplitude < 1.0:  # Very low amplitude
                    self._low_amp_count += 1
                else:
                    self._low_amp_count = 0
            else:
                self._low_amp_count = 1 if amplitude < 1.0 else 0
                
            # Only warn about consistently low amplitude after longer period
            if self._low_amp_count > 100 and not hasattr(self, '_low_amp_warning_sent'):  # About 2 seconds
                self._low_amp_warning_sent = True
                log_text("AUDIO_DEBUG", f"Consistently low amplitude: {amplitude:.1f}")
                
        except Exception as amp_error:
            log_text("AUDIO_DEBUG", f"Error calculating amplitude: {amp_error}")
            amplitude = 0
            
        if self.on_status_update:
            self.on_status_update(f"AUDIO_AMP:{int(amplitude)}", "blue")

        if not self._triggered:
            self._ring_buffer.append((frame_data, is_speech))
            num_voiced = sum(1 for _, speech in self._ring_buffer if speech)
            # Start recording if VAD detects speech for a portion of the ring buffer
            if (
                num_voiced > 0.5 * self._ring_buffer.maxlen
            ):  # Adjust threshold as needed
                self._triggered = True
                self._silence_start_time = None
                # Prepend audio from ring buffer
                for f, s in self._ring_buffer:
                    self._voiced_frames.append(f)
                self._ring_buffer.clear()
        else:
            # Already triggered; collect voiced frames
            self._voiced_frames.append(frame_data)
            
            # Optimize buffer memory usage periodically
            if len(self._voiced_frames) % 50 == 0:  # Check every 50 frames (~2.5 seconds)
                self._optimize_buffer_memory()

            if not is_speech:
                if self._silence_start_time is None:
                    self._silence_start_time = time.time()
                    # Only log significant silence events, not every timer start
                else:
                    silence_duration = time.time() - self._silence_start_time

                    if silence_duration >= config.SILENCE_THRESHOLD_SECONDS:
                        # Sufficient silence detected; process audio
                        log_text("AUDIO_AUTO_STOP", f"Auto-stopping after {silence_duration:.1f}s silence")
                        self._triggered = False
                        self._silence_start_time = None
                        self._request_audio_processing()
                    # Remove verbose intermediate silence logging
            else:
                # Speech is still being detected; reset silence timer
                self._silence_start_time = None

    def _request_audio_processing(self):
        """Requests processing of buffered audio frames."""
        if not self._voiced_frames:
            self._log_status("No voiced frames to process.", "blue")
            self.set_listening_state("activation")
            return

        self._log_status("Requesting audio processing...", "orange")
        self.set_listening_state("processing")

        # Copy the frames before resetting
        frames_to_process = list(self._voiced_frames)
        audio_data = (
            np.concatenate(frames_to_process)
            if frames_to_process
            else np.array([], dtype=np.int16)
        )

        # Reset buffering state after copying
        self._reset_buffering()

        if self.on_speech_end and audio_data.size > 0:
            self.on_speech_end(audio_data)
        else:
            # Return to activation if no callback or no data
            self.set_listening_state("activation")

    def _run_loop(self):
        """The main audio processing loop running in a separate thread."""

        while not self._stop_event.is_set():
            # Log memory usage periodically
            try:
                self._log_memory_usage()
            except Exception as e:
                print(f"Error in memory logging: {e}")
            if not self._program_active or self._listening_state == "inactive":
                time.sleep(0.1)  # Sleep briefly if inactive
                continue

            if not self._stream or not self._stream.is_active():
                self._log_status("Audio stream is not active. Stopping loop.", "red")
                break  # Exit loop if stream is bad

            try:
                data = self._stream.read(self._frame_size, exception_on_overflow=False)
                
                # Check for empty or problematic data reads
                if not data:
                    log_text("AUDIO_DEBUG", "No data returned from audio stream read")
                    time.sleep(0.01)  # Brief pause before next read
                    continue
                    
                # Check if we're getting silence consistently (possible microphone conflict)
                if len(data) > 0:
                    # Quick check for all-zero data or very low amplitude (Safari pattern)
                    sample_data = np.frombuffer(data, dtype=np.int16)
                    max_amplitude = np.abs(np.max(sample_data)) if sample_data.size > 0 else 0
                    is_essentially_silent = (np.all(sample_data == 0))
                    
                    if is_essentially_silent:
                        if not hasattr(self, '_main_loop_silent_count'):
                            self._main_loop_silent_count = 0
                        self._main_loop_silent_count += 1
                        
                        # If we get sustained silent data in the main loop, log it once for debugging
                        if self._main_loop_silent_count > 1000 and not hasattr(self, '_main_loop_conflict_logged'):  # About 20 seconds - much longer threshold
                            self._main_loop_conflict_logged = True
                            log_text("AUDIO_DEBUG", f"Main loop sustained silence: {self._main_loop_silent_count} frames")
                            
                            # Check for conflicts but don't spam logs
                            conflict_info = self._check_for_audio_conflicts()
                            if conflict_info:
                                log_text("AUDIO_DEBUG", f"Possible conflict: {conflict_info}")
                    else:
                        # Reset counters when we get valid data
                        self._main_loop_silent_count = 0
                        if hasattr(self, '_main_loop_conflict_logged'):
                            del self._main_loop_conflict_logged

                if self._listening_state == "activation":
                    # Wait briefly for Vosk model to be ready if it isn't yet
                    if not self._vosk_ready_event.is_set():
                        # Optional: Add a timeout?
                        # self._vosk_ready_event.wait(timeout=10) # Wait up to 10 seconds
                        # if not self._vosk_ready_event.is_set():
                        #     log_text("VOSK_WAIT_TIMEOUT", "Timed out waiting for Vosk model.")
                        #     continue # Skip this frame if Vosk isn't ready
                        pass  # If not waiting, just skip frame if Vosk not ready

                    if (
                        self._recognizer and self._vosk_ready_event.is_set()
                    ):  # Check if recognizer exists and is ready
                        if self._recognizer.AcceptWaveform(data):
                            result = self._recognizer.Result()
                            # --- Corrected Indentation Start ---
                            try:
                                result_dict = json.loads(result)
                                text = result_dict.get("text", "")
                                if text:
                                    # print(f"Vosk heard: {text}") # Debug log
                                    self._handle_wake_word(text)
                            except json.JSONDecodeError:
                                # Handle cases where Vosk might return partial/invalid JSON
                                # print(f"Vosk partial result: {self._recognizer.PartialResult()}") # Debug log
                                pass  # Ignore partial results for wake word
                            # --- Corrected Indentation End ---

                elif self._listening_state == "dictation":
                    # Process frame for VAD and buffering
                    self._process_dictation_frame(data)

                elif self._listening_state == "processing":
                    # While processing, we might want to discard audio or handle it differently
                    # For now, just sleep briefly to yield CPU
                    time.sleep(self._frame_duration_ms / 1000.0)

            except IOError as e:
                # This can happen if the input device changes or has issues
                if e.errno == pyaudio.paInputOverflowed:
                    # print("Input overflowed. Skipping frame.") # Debug log
                    pass  # Ignore overflow, continue reading
                else:
                    self._log_status(f"Audio read error: {e}", "red")
                    log_text("AUDIO_READ_ERROR", f"IOError during audio read: {e}")
                    
                    # Check if this might be due to microphone conflicts
                    if "Device unavailable" in str(e) or "busy" in str(e).lower():
                        conflict_info = self._check_for_audio_conflicts()
                        if conflict_info:
                            log_text("AUDIO_CONFLICT", f"Audio read error likely due to conflict: {conflict_info}")
                            self._log_status(f"Microphone conflict: {conflict_info}", "orange")
                    
                    # Consider stopping or attempting to restart the stream
                    time.sleep(0.5)  # Avoid busy-looping on persistent errors
            except Exception as e:
                self._log_status(f"Error in audio loop: {e}", "red")
                log_text("AUDIO_LOOP_ERROR", f"Unexpected error in audio loop: {e}")
                # Decide if the error is fatal or recoverable
                time.sleep(0.5)  # Pause before continuing

    def check_microphone_availability(self, skip_test_stream=False):
        """
        Checks if the microphone is available and not being used by another application.
        Args:
            skip_test_stream: If True, skips opening a test audio stream to prevent macOS indicator flashing
        Returns a tuple of (is_available: bool, detailed_message: str, status_color: str)
        """
        if not PYAUDIO_AVAILABLE:
            return False, "PyAudio not available (CI environment)", "orange"
            
        try:
            # Check if default input device exists
            try:
                default_device = self._p.get_default_input_device_info()
            except OSError as e:
                return False, f"No default input device found: {str(e)}", "red"
            
            # Get device info for detailed error reporting
            device_name = default_device.get('name', 'Unknown Device')
            max_channels = default_device.get('maxInputChannels', 0)
            
            if max_channels == 0:
                return False, f"Device '{device_name}' has no input channels", "red"
            
            # Skip test stream during startup to prevent macOS microphone indicator flashing
            if skip_test_stream:
                return True, f"Microphone '{device_name}' is available", "green"
            
            # Try to open a test stream to check for actual conflicts
            test_stream = None
            try:
                test_stream = self._p.open(
                    format=self._audio_format,
                    channels=min(self._channels, max_channels),
                    rate=self._sample_rate,
                    input=True,
                    frames_per_buffer=self._frame_size,
                    start=False  # Don't start immediately
                )
                
                # Try to start the stream
                test_stream.start_stream()
                
                # Test reading a small amount of data
                test_data = test_stream.read(self._frame_size, exception_on_overflow=False)
                
                # Stop and close the test stream
                test_stream.stop_stream()
                test_stream.close()
                
                # Check if we got valid data
                if len(test_data) == 0:
                    return False, f"Device '{device_name}' returned no audio data", "orange"
                    
                # Only check for conflicts if we get no audio data at all
                # Don't flag conflicts for normal background noise
                return True, f"Microphone '{device_name}' is available", "green"
                
            except OSError as e:
                error_msg = str(e).lower()
                
                # Detect specific error types
                if "device unavailable" in error_msg or "usbmuxd" in error_msg:
                    # Check for conflicts to provide better error message
                    conflict_info = self._check_for_audio_conflicts()
                    if conflict_info:
                        return False, f"Device '{device_name}' is unavailable - {conflict_info}", "orange"
                    else:
                        return False, f"Device '{device_name}' is unavailable (may be in use by another app)", "orange"
                elif "permission" in error_msg or "access" in error_msg:
                    return False, f"Permission denied for microphone access", "red"
                elif "sample rate" in error_msg or "format" in error_msg:
                    return False, f"Audio format not supported by '{device_name}'", "orange"
                else:
                    return False, f"Audio device error: {str(e)}", "red"
                    
            except Exception as e:
                return False, f"Unexpected microphone error: {str(e)}", "red"
                
            finally:
                # Ensure test stream is properly closed
                if test_stream:
                    try:
                        if hasattr(test_stream, 'is_active') and test_stream.is_active():
                            test_stream.stop_stream()
                        test_stream.close()
                    except:
                        pass
                        
        except Exception as e:
            return False, f"Failed to check microphone: {str(e)}", "red"
    
    def _check_for_audio_conflicts(self):
        """
        Checks for common applications that might be using the microphone.
        Returns a string describing potential conflicts, or None if no conflicts detected.
        """
        if not PYAUDIO_AVAILABLE:
            return None
            
        try:
            # Check for common audio-using applications on macOS
            if sys.platform == "darwin":
                # Use lsof to check for audio device usage
                try:
                    result = subprocess.run(
                        ["lsof", "/dev/tty"], 
                        capture_output=True, 
                        text=True, 
                        timeout=2
                    )
                    # This is a basic check - more sophisticated detection would require more system calls
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                
                # Check for Safari/Chrome processes (common dictation users)
                try:
                    result = subprocess.run(
                        ["pgrep", "-l", "Safari|Chrome|Microsoft|Zoom|Teams"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        processes = result.stdout.strip().split('\n')
                        browser_processes = [p for p in processes if any(browser in p for browser in ['Safari', 'Chrome'])]
                        if browser_processes:
                            return "Web browser (Safari/Chrome) may be using microphone for dictation"
                        
                        meeting_processes = [p for p in processes if any(app in p for app in ['Zoom', 'Teams', 'Microsoft'])]
                        if meeting_processes:
                            return "Video conferencing app may be using microphone"
                            
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                    
            return None
            
        except Exception as e:
            log_text("MIC_CONFLICT_CHECK_ERROR", f"Error checking for audio conflicts: {e}")
            return None
    
    def get_microphone_status_message(self):
        """
        Returns a user-friendly status message about microphone availability.
        Includes suggestions for resolving common issues.
        """
        current_time = time.time()
        
        # Re-check availability periodically or if not checked yet
        if (not self._mic_availability_checked or 
            current_time - self._last_mic_check_time > self._mic_check_interval):
            
            is_available, message, color = self.check_microphone_availability()
            self._mic_availability_checked = True
            self._mic_error_details = (is_available, message, color)
            self._last_mic_check_time = current_time
        
        is_available, message, color = self._mic_error_details
        
        if is_available:
            return message, color
        else:
            # Provide helpful suggestions based on the error
            base_message = message
            
            if "Safari" in message or "Chrome" in message or "dictation" in message:
                suggestion = " Try closing browser tabs with dictation or disabling browser microphone access."
            elif "Zoom" in message or "Teams" in message or "conferencing" in message:
                suggestion = " Please close video conferencing applications and try again."
            elif "permission" in message.lower():
                suggestion = " Go to System Preferences > Security & Privacy > Microphone to grant access."
            elif "unavailable" in message.lower() or "in use" in message.lower():
                suggestion = " Close other applications using the microphone and restart the app."
            elif "no input channels" in message.lower() or "no default input" in message.lower():
                suggestion = " Check System Preferences > Sound > Input to select a microphone."
            else:
                suggestion = " Check System Preferences > Sound settings and restart the application."
                
            return f"{base_message}{suggestion}", color


# Example Usage (for testing purposes)
if __name__ == "__main__":

    def handle_wake_word_test(command):
        print(f"*** Wake Word Detected: Command = {command} ***")
        # Example: Immediately stop after wake word for testing
        # audio_handler.stop()

    def handle_speech_end_test(audio_data):
        print(f"*** Speech Ended: Received {len(audio_data)} samples ***")
        print(f"Audio data shape: {audio_data.shape}, dtype: {audio_data.dtype}")
        # Here you would typically save or transcribe the audio_data
        # For testing, just go back to activation state
        audio_handler.set_listening_state("activation")

    def handle_status_update_test(message, color):
        print(f"--- STATUS [{color}]: {message} ---")

    print("Initializing AudioHandler...")
    audio_handler = AudioHandler(
        on_wake_word_callback=handle_wake_word_test,
        on_speech_end_callback=handle_speech_end_test,
        on_status_update_callback=handle_status_update_test,
    )

    print("Starting AudioHandler...")
    audio_handler.start()

    try:
        print("AudioHandler running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Keep main thread alive
    except KeyboardInterrupt:
        print("\nStopping AudioHandler...")
        audio_handler.stop()
        audio_handler.terminate_pyaudio()  # Clean up PyAudio
        print("AudioHandler stopped.")
