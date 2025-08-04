# Make imports conditional for CI compatibility
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARN] numpy not available in transcription_handler.py - using mock")
    # Create minimal mock numpy for CI
    class MockArray:
        def __init__(self, data):
            self.data = data
            self.size = len(data) if hasattr(data, '__len__') else 0
        
        def tobytes(self):
            return b"mock_audio_data"
        
        def astype(self, dtype):
            return self
    
    class MockNumpy:
        @staticmethod
        def frombuffer(data, dtype=None):
            return MockArray([])
        
        @staticmethod
        def array(data):
            return MockArray(data)
        
        int16 = "int16"
        ndarray = MockArray  # Add ndarray as a type alias for type annotations
    
    np = MockNumpy()

import time
import os
import wave

try:
    import mlx_whisper
    MLX_WHISPER_AVAILABLE = True
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    print("[WARN] mlx_whisper not available - Whisper transcription will be mocked")

try:
    import parakeet_mlx
    PARAKEET_MLX_AVAILABLE = True
except ImportError:
    PARAKEET_MLX_AVAILABLE = False
    print("[WARN] parakeet_mlx not available - Parakeet transcription will be mocked")

# Create mock transcription functions if neither library is available
if not MLX_WHISPER_AVAILABLE and not PARAKEET_MLX_AVAILABLE:
    print("[WARN] No ASR libraries available - all transcription will be mocked")
    class MockMLXWhisper:
        @staticmethod
        def transcribe(audio_path, path_or_hf_repo, language=None, temperature=None, **kwargs):
            return {
                "text": f"[MOCK TRANSCRIPTION] Audio from {audio_path}",
                "language": "en",
                "segments": []
            }
    
    mlx_whisper = MockMLXWhisper()
    
    class MockParakeetMLX:
        @staticmethod
        def transcribe_from_file(audio_path, model_id, **kwargs):
            return f"[MOCK PARAKEET TRANSCRIPTION] Audio from {audio_path}"
    
    parakeet_mlx = MockParakeetMLX()

import threading

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("[WARN] pyaudio not available in transcription_handler.py - using mock")
    # Create mock pyaudio
    class MockPyAudio:
        paInt16 = "paInt16"
        
        @staticmethod
        def get_sample_size(format):
            return 2  # Default to 16-bit
    
    pyaudio = MockPyAudio()

import json

try:
    from huggingface_hub import snapshot_download
    HUGGINGFACE_HUB_AVAILABLE = True
except ImportError:
    HUGGINGFACE_HUB_AVAILABLE = False
    print("[WARN] huggingface_hub not available - using mock download")
    def snapshot_download(repo_id, local_dir=None, **kwargs):
        # Create a mock local directory structure
        mock_dir = local_dir or f"./mock_models/{repo_id.replace('/', '_')}"
        os.makedirs(mock_dir, exist_ok=True)
        
        # Create a mock config.json
        config_path = os.path.join(mock_dir, "config.json")
        if not os.path.exists(config_path):
            with open(config_path, "w") as f:
                json.dump({"sample_rate": 16000, "mock": True}, f)
        
        return mock_dir

# Import configuration constants
from src.config import config
from src.utils.utils import log_text  # Assuming a utils.py for logging
from src.vocabulary.vocabulary_manager import get_vocabulary_manager


class TranscriptionHandler:
    """Handles the transcription of audio data using multiple ASR libraries."""

    def __init__(
        self,
        on_transcription_complete_callback=None,
        on_status_update_callback=None,
        selected_asr_model=None,
    ):
        """
        Initializes the TranscriptionHandler.

        Args:
            on_transcription_complete_callback: Function to call when transcription finishes.
                                                Receives the transcribed text (str) and transcription time (float).
            on_status_update_callback: Function to call to update the application status display.
                                       Receives status text (str) and color (str).
            selected_asr_model: The Hugging Face ID of the ASR model to use (optional).
                               If not provided, will use saved settings or default.
        """
        self.on_transcription_complete = on_transcription_complete_callback
        self.on_status_update = on_status_update_callback
        self._temp_folder = config.TEMP_AUDIO_FOLDER
        self._sample_rate = config.SAMPLE_RATE
        
        # Use provided model, or saved settings, or config default (in that order)
        if selected_asr_model:
            self.selected_asr_model = selected_asr_model
        else:
            # Try to get from saved settings, fall back to config default
            try:
                from settings_manager import settings_manager
                self.selected_asr_model = settings_manager.get_setting("selectedAsrModel", config.DEFAULT_ASR_MODEL)
            except ImportError:
                # In case settings_manager is not available (testing, etc.)
                self.selected_asr_model = config.DEFAULT_ASR_MODEL

        # Determine the model type and library to use
        self.model_type = self._detect_model_type(self.selected_asr_model)
        self._log_status(f"Detected model type: {self.model_type} for {self.selected_asr_model}", "grey")
        
        # Load Parakeet model if needed
        if self.model_type == "parakeet" and PARAKEET_MLX_AVAILABLE:
            try:
                self._log_status(f"Loading Parakeet model: {self.selected_asr_model}", "grey")
                self.parakeet_model = parakeet_mlx.from_pretrained(self.selected_asr_model)
                self._log_status("Parakeet model loaded successfully", "grey")
            except Exception as e:
                self._log_status(f"Failed to load Parakeet model: {e}", "red")
                raise RuntimeError(f"Failed to load Parakeet model: {e}") from e
        else:
            self.parakeet_model = None

        # Check if we're in a CI environment (missing key dependencies)
        if not MLX_WHISPER_AVAILABLE and not PARAKEET_MLX_AVAILABLE:
            self._log_status("Transcription handler initialized in CI mode - dependencies mocked", "orange")
            self.local_model_path_prepared = "./mock_model_path"
            return

        # Ensure temp audio folder exists
        if not os.path.exists(self._temp_folder):
            try:
                os.makedirs(self._temp_folder)
                self._log_status(
                    f"Created temporary audio folder: {self._temp_folder}", "green"
                )
            except OSError as e:
                self._log_status(
                    f"Error creating temp audio folder {self._temp_folder}: {e}", "red"
                )
                # Decide if this is fatal or if we can proceed without saving temp files
                raise RuntimeError(f"Failed to create temp audio folder: {e}") from e

        # Only prepare local model copy for Whisper models (Parakeet models don't need it)
        if self.model_type == "whisper":
            self._log_status(
                f"Preparing local copy of Whisper model: {self.selected_asr_model}", "grey"
            )
            try:
                self.local_model_path_prepared = self._prepare_local_model_copy(
                    self.selected_asr_model
                )
                self._log_status(
                    f"Local Whisper model prepared at: {self.local_model_path_prepared}",
                    "grey",
                )
            except Exception as e:
                self._log_status(f"Failed to prepare local Whisper model: {e}", "red")
                log_text(
                    "TRANSCRIPTION_HANDLER_ERROR",
                    f"Failed to prepare local Whisper model: {e}",
                )
                raise
        else:
            # For Parakeet models, we use the model ID directly
            self.local_model_path_prepared = self.selected_asr_model
            self._log_status(f"Parakeet model will be used directly: {self.selected_asr_model}", "grey")

    def _detect_model_type(self, model_id: str) -> str:
        """
        Detect whether the model is a Whisper or Parakeet model.
        
        Args:
            model_id: The Hugging Face model ID
            
        Returns:
            "whisper" or "parakeet"
        """
        model_id_lower = model_id.lower()
        if "parakeet" in model_id_lower:
            return "parakeet"
        elif "whisper" in model_id_lower:
            return "whisper"
        else:
            # Default to whisper for unknown models
            self._log_status(f"Unknown model type for {model_id}, defaulting to whisper", "orange")
            return "whisper"

    def _log_status(self, message, color="black"):
        """Helper to call the status update callback if available."""
        print(f"TranscriptionHandler Status: {message}")  # Also print to console
        if self.on_status_update:
            self.on_status_update(message, color)

    def _prepare_local_model_copy(self, hf_repo_id: str) -> str:
        """Prepare local copy for Whisper models only."""
        self._log_status(f"Downloading/locating model: {hf_repo_id}", "blue")
        try:
            # Download the model snapshot, this will return the path to the local cache
            # or use existing cache if already downloaded.
            # We use a specific local_dir to ensure we know where to find and modify it.
            # Using a subdirectory within TEMP_AUDIO_FOLDER or a dedicated 'models_cache' folder.
            # For simplicity, let's use a 'models_cache' in the app's root for now.
            # Ensure this path is robust or configurable if needed.
            app_root = os.path.dirname(
                os.path.abspath(__file__)
            )  # Gets directory of transcription_handler.py
            # To place it in the main project root, assuming standard structure:
            # project_root = os.path.dirname(app_root)
            # For now, let's put it inside TEMP_AUDIO_FOLDER to keep related temp files together
            # but this might be re-downloaded if TEMP_AUDIO_FOLDER is cleared often.
            # A better place might be a dedicated 'model_cache' directory.
            # Let's create a 'model_cache' directory next to TEMP_AUDIO_FOLDER if it doesn't exist.
            model_cache_dir = os.path.join(
                os.path.dirname(config.TEMP_AUDIO_FOLDER), "model_cache_whisper"
            )
            if not os.path.exists(model_cache_dir):
                os.makedirs(model_cache_dir)
                self._log_status(
                    f"Created model cache directory: {model_cache_dir}", "grey"
                )

            local_model_path = snapshot_download(
                repo_id=hf_repo_id,
                local_dir=os.path.join(model_cache_dir, hf_repo_id.replace("/", "_")),
                local_dir_use_symlinks=False,
            )
            self._log_status(f"Model files located at: {local_model_path}", "grey")
        except Exception as e:
            self._log_status(
                f"Error downloading model snapshot for {hf_repo_id}: {e}", "red"
            )
            raise

        config_path = os.path.join(local_model_path, "config.json")
        self._log_status(f"Modifying config.json at: {config_path}", "blue")
        try:
            with open(config_path, "r") as f:
                model_config_json = json.load(f)
            self._log_status(
                "Successfully loaded model config.json for modification", "grey"
            )

            config_modified = False
            
            if "sample_rate" in model_config_json:
                del model_config_json["sample_rate"]
                self._log_status(
                    "'sample_rate' key removed from local config.json", "yellow"
                )
                config_modified = True
            else:
                self._log_status(
                    "'sample_rate' key not found in config.json, no modification needed.",
                    "grey",
                )

            # Remove incompatible parameters that cause issues with mlx-whisper
            incompatible_keys = [
                "compute_eval_loss",  
                "log_prediction",     
                "rnnt_reduction",     
                "eval_output_dir",
                "eval_strategy", 
                "prediction_loss_only",
                "remove_unused_columns"
            ]
            
            for key in incompatible_keys:
                if key in model_config_json:
                    del model_config_json[key]
                    self._log_status(
                        f"'{key}' key removed from local config.json (incompatible with mlx-whisper)", "yellow"
                    )
                    config_modified = True

            if config_modified:
                with open(config_path, "w") as f:
                    json.dump(model_config_json, f, indent=4)
                self._log_status("Modified config.json saved.", "green")
            else:
                self._log_status("No config.json modifications needed.", "grey")

            return local_model_path  # Return path to the directory containing the modified model
        except Exception as e:
            self._log_status(
                f"Error modifying config.json from {config_path}: {e}", "red"
            )
            raise

    def _save_temp_audio(self, audio_data: np.ndarray) -> str:
        """Saves audio data to a temporary WAV file."""
        timestamp = int(time.time() * 1000)
        filename = os.path.join(self._temp_folder, f"temp_{timestamp}.wav")
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(config.CHANNELS)
                # Use pyaudio to get sample width based on the format defined in config
                wf.setsampwidth(pyaudio.get_sample_size(config.AUDIO_FORMAT))
                wf.setframerate(self._sample_rate)
                wf.writeframes(audio_data.tobytes())
            # self._log_status(f"Temporary audio saved: {filename}", "grey") # Optional: Log file saving
            return filename
        except Exception as e:
            self._log_status(
                f"Error saving temporary audio file {filename}: {e}", "red"
            )
            return None  # Indicate failure

    def _load_audio_from_file(self, filename: str) -> np.ndarray:
        """Loads audio data from a WAV file."""
        try:
            with wave.open(filename, "rb") as wf:
                n_frames = wf.getnframes()
                # Assuming audio format is paInt16 as defined in config
                audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)
            return audio
        except Exception as e:
            self._log_status(f"Error loading audio file {filename}: {e}", "red")
            return None  # Indicate failure

    def _cleanup_temp_file(self, filename: str):
        """Deletes the temporary audio file."""
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
                # self._log_status(f"Temporary audio deleted: {filename}", "grey") # Optional: Log file deletion
            except OSError as e:
                self._log_status(
                    f"Error deleting temporary audio file {filename}: {e}", "orange"
                )

    def transcribe_audio_data(
        self, audio_data: np.ndarray, prompt: str = config.DEFAULT_WHISPER_PROMPT
    ):
        """
        Transcribes the given audio data in a separate thread.

        Args:
            audio_data: Numpy array containing the audio samples.
            prompt: The prompt to guide the transcription (used for Whisper models).
        """
        # Handle mock numpy arrays in CI environment
        if not NUMPY_AVAILABLE and hasattr(audio_data, 'data'):
            # This is a mock array, proceed with mock data
            pass
        elif audio_data is None or (hasattr(audio_data, 'size') and audio_data.size == 0):
            self._log_status("No audio data provided for transcription.", "orange")
            if self.on_transcription_complete:
                self.on_transcription_complete("", 0.0)  # Return empty result
            return

        # Run the transcription process in a background thread
        thread = threading.Thread(
            target=self._transcribe_thread_worker,
            args=(audio_data, prompt),
            daemon=True,
        )
        thread.start()

    def _transcribe_thread_worker(self, audio_data: np.ndarray, prompt: str):
        """Worker function for the transcription thread."""
        self._log_status("Starting transcription process...", "blue")
        filename = None
        raw_text = ""
        transcription_time = 0.0

        try:
            # Check if we're in CI mode (missing dependencies)
            if not MLX_WHISPER_AVAILABLE and not PARAKEET_MLX_AVAILABLE:
                self._log_status("Transcription mocked - no ASR libraries available (CI environment)", "orange")
                raw_text = "[MOCK TRANSCRIPTION] Test transcription result"
                transcription_time = 0.1  # Mock fast transcription
                log_text("TRANSCRIBED", f"[Time: {transcription_time:.2f} seconds] {raw_text}")
                if self.on_transcription_complete:
                    self.on_transcription_complete(raw_text, transcription_time)
                return

            # 1. Save audio to a temporary file
            filename = self._save_temp_audio(audio_data)
            if filename is None:
                self._log_status("Failed to save temporary audio file.", "red")
                return

            # 2. Load audio from file (not strictly necessary, but keeps logic consistent)
            loaded_audio = self._load_audio_from_file(filename)
            if loaded_audio is None:
                self._log_status("Failed to load audio for transcription.", "red")
                return

            # 3. Perform transcription based on model type
            start_time = time.time()
            
            if self.model_type == "parakeet":
                self._log_status(f"Using Parakeet-MLX for transcription with model: {self.selected_asr_model}", "blue")
                
                if not PARAKEET_MLX_AVAILABLE or self.parakeet_model is None:
                    raw_text = "[MOCK PARAKEET TRANSCRIPTION] Test transcription result"
                    self._log_status("Parakeet transcription mocked - parakeet_mlx not available or model not loaded", "orange")
                else:
                    # Use parakeet_mlx for transcription
                    result = self.parakeet_model.transcribe(filename)
                    # Extract text from AlignedResult - use the direct text property
                    if hasattr(result, 'text'):
                        raw_text = result.text.strip()
                    elif hasattr(result, 'tokens') and result.tokens:
                        # Fallback: concatenate tokens without spaces (character-level tokens)
                        raw_text = ''.join([token.text for token in result.tokens if hasattr(token, 'text')]).strip()
                    else:
                        raw_text = str(result).strip()
                    
            else:  # whisper model
                self._log_status(f"Using MLX-Whisper for transcription with model: {self.selected_asr_model}", "blue")
                
                if not MLX_WHISPER_AVAILABLE:
                    raw_text = "[MOCK WHISPER TRANSCRIPTION] Test transcription result"
                    self._log_status("Whisper transcription mocked - mlx_whisper not available", "orange")
                else:
                    # Use mlx_whisper for transcription
                    result = mlx_whisper.transcribe(
                        filename,  # Pass file path
                        language="en",
                        fp16=False,
                        prompt=prompt,
                        path_or_hf_repo=self.local_model_path_prepared,
                    )
                    raw_text = result.get("text", "").strip()

            end_time = time.time()
            transcription_time = end_time - start_time

            # Apply vocabulary corrections
            try:
                vocab_manager = get_vocabulary_manager()
                corrected_text, corrections = vocab_manager.apply_corrections(raw_text)
                
                if corrections:
                    self._log_status(f"Applied {len(corrections)} vocabulary corrections", "blue")
                    log_text("VOCAB_CORRECTIONS", f"Applied corrections: {corrections}")
                    raw_text = corrected_text
                    
            except Exception as e:
                self._log_status(f"Error applying vocabulary corrections: {e}", "orange")
                # Continue with original text if vocabulary fails
                log_text("VOCAB_ERROR", f"Vocabulary correction failed: {e}")

            log_text(
                "TRANSCRIBED", f"[Time: {transcription_time:.2f} seconds] {raw_text}"
            )
            self._log_status(
                f"Transcription successful ({transcription_time:.2f}s).", "green"
            )

        except Exception as e:
            self._log_status(f"Error during transcription: {e}", "red")
            log_text("TRANSCRIBED", f"(Exception) {str(e)}")
            raw_text = ""  # Ensure empty text on error
            transcription_time = 0.0
        finally:
            # 4. Clean up temporary file
            if filename:
                self._cleanup_temp_file(filename)

            # 5. Call the completion callback (ensure it's thread-safe if it modifies GUI)
            if self.on_transcription_complete:
                # The callback is handled by main.py which uses a queue, so it's safe.
                self.on_transcription_complete(raw_text, transcription_time)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Assuming utils.py exists with a basic log_text function
    # Create a dummy utils.py if needed:
    # with open("utils.py", "w") as f:
    #     f.write("import time\n")
    #     f.write("def log_text(label, content):\n")
    #     f.write("    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')\n")
    #     f.write("    print(f'{timestamp} [{label}] {content}')\n")
    #     f.write("    # Optionally write to file\n")
    #     f.write("    # with open(config.LOG_FILE, 'a', encoding='utf-8') as log_file:\n")
    #     f.write("    #     log_file.write(f'{timestamp} [{label}] {content}\\n')\n")

    import pyaudio  # Needed for get_sample_size in _save_temp_audio

    def transcription_done(text, duration):
        print(f"\n--- TRANSCRIPTION COMPLETE ---")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Text: {text}")
        print(f"----------------------------\n")

    def status_update(message, color):
        print(f"--- STATUS [{color}]: {message} ---")

    print("Initializing TranscriptionHandler...")
    handler = TranscriptionHandler(
        on_transcription_complete_callback=transcription_done,
        on_status_update_callback=status_update,
    )

    # Create a dummy audio signal (e.g., 2 seconds of sine wave)
    sample_rate = config.SAMPLE_RATE
    duration = 2
    frequency = 440  # A4 note
    t = np.linspace(0.0, duration, int(sample_rate * duration))
    amplitude = np.iinfo(np.int16).max * 0.5
    dummy_audio = (amplitude * np.sin(2.0 * np.pi * frequency * t)).astype(np.int16)

    print(f"Created dummy audio: {len(dummy_audio)} samples, dtype={dummy_audio.dtype}")

    print("\nStarting transcription...")
    handler.transcribe_audio_data(dummy_audio)

    print("\nTranscription started in background thread. Waiting...")
    # Keep the main thread alive for a while to let transcription finish
    time.sleep(30)  # Adjust sleep time as needed for the model to run
    print("Test finished.")
