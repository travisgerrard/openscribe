# Make imports conditional for CI compatibility
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Keep warning in stdout only if minimal mode is disabled
    try:
        from src.config import config as _cfg
        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
            print("[WARN] numpy not available in transcription_handler.py - using mock")
    except Exception:
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
import shutil

try:
    import mlx_whisper
    MLX_WHISPER_AVAILABLE = True
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    try:
        from src.config import config as _cfg
        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
            print("[WARN] mlx_whisper not available - Whisper transcription will be mocked")
    except Exception:
        print("[WARN] mlx_whisper not available - Whisper transcription will be mocked")

try:
    import parakeet_mlx
    PARAKEET_MLX_AVAILABLE = True
except ImportError:
    PARAKEET_MLX_AVAILABLE = False
    try:
        from src.config import config as _cfg
        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
            print("[WARN] parakeet_mlx not available - Parakeet transcription will be mocked")
    except Exception:
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

# Optional Transformers fallback for non-MLX Whisper repos
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore

try:
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    AutoModelForSpeechSeq2Seq = None  # type: ignore
    AutoProcessor = None  # type: ignore
    hf_pipeline = None  # type: ignore

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    try:
        from src.config import config as _cfg
        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
            print("[WARN] pyaudio not available in transcription_handler.py - using mock")
    except Exception:
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
    try:
        from src.config import config as _cfg
        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
            print("[WARN] huggingface_hub not available - using mock download")
    except Exception:
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

        # Ensure selected_asr_model is valid string; fallback to default
        if not self.selected_asr_model:
            self.selected_asr_model = config.DEFAULT_ASR_MODEL
        # Determine the model type and library to use
        self.model_type = self._detect_model_type(self.selected_asr_model)
        self._log_status(f"Detected model type: {self.model_type} for {self.selected_asr_model}", "grey")
        # Decide whisper backend explicitly: MLX vs Transformers
        self._whisper_backend = None
        if self.model_type == "whisper":
            self._whisper_backend = self._detect_whisper_backend(self.selected_asr_model)
            self._log_status(f"Selected whisper backend: {self._whisper_backend}", "grey")
        
        # Light mode to avoid heavy model loads (set CT_LIGHT_MODE=1 to enable)
        self._light_mode = os.getenv("CT_LIGHT_MODE", "0") == "1"
        if self._light_mode:
            self._log_status("CT_LIGHT_MODE enabled - skipping heavy ASR model loads", "orange")
            self.parakeet_model = None
            self.local_model_path_prepared = "./mock_model_path"
        
        
        # Load Parakeet model if needed (skip in light mode)
        if not self._light_mode:
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

        # Only prepare local model copy for Whisper models using MLX backend
        if self.model_type == "whisper" and self._whisper_backend == "mlx" and not self._light_mode:
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
        elif not self._light_mode and self.model_type == "parakeet":
            # For Parakeet models, we use the model ID directly
            self.local_model_path_prepared = self.selected_asr_model
            self._log_status(f"Parakeet model will be used directly: {self.selected_asr_model}", "grey")

    def update_selected_asr_model(self, new_model_id: str):
        """Update ASR model at runtime and prepare required resources."""
        if not new_model_id or new_model_id == self.selected_asr_model:
            # No change
            return
        self._log_status(f"Updating ASR model to: {new_model_id}", "orange")
        self.selected_asr_model = new_model_id
        # Recompute model type
        self.model_type = self._detect_model_type(self.selected_asr_model)
        self._log_status(f"Detected model type: {self.model_type} for {self.selected_asr_model}", "grey")
        
        # Reset model-specific resources
        self.parakeet_model = None
        self.local_model_path_prepared = None
        
        # Respect light mode - avoid heavy loads and downloads
        if getattr(self, "_light_mode", False):
            self._log_status("CT_LIGHT_MODE enabled - deferring heavy ASR model setup", "orange")
            self.local_model_path_prepared = "./mock_model_path"
            return

        # Handle CI/mock mode quickly
        if not MLX_WHISPER_AVAILABLE and not PARAKEET_MLX_AVAILABLE:
            self._log_status("ASR update in CI mode - dependencies mocked", "orange")
            self.local_model_path_prepared = "./mock_model_path"
            return
        
        try:
            if self.model_type == "parakeet":
                if PARAKEET_MLX_AVAILABLE:
                    self._log_status(f"Loading Parakeet model: {self.selected_asr_model}", "grey")
                    self.parakeet_model = parakeet_mlx.from_pretrained(self.selected_asr_model)
                    self._log_status("Parakeet model loaded successfully", "grey")
                    # For Parakeet models, path is just the model id
                    self.local_model_path_prepared = self.selected_asr_model
                else:
                    self._log_status("Parakeet library not available; cannot load model.", "red")
                    raise RuntimeError("Parakeet library not available")
            else:
                # Whisper path handling
                self._log_status(
                    f"Preparing local copy of Whisper model: {self.selected_asr_model}",
                    "grey",
                )
                self.local_model_path_prepared = self._prepare_local_model_copy(
                    self.selected_asr_model
                )
                self._log_status(
                    f"Local Whisper model prepared at: {self.local_model_path_prepared}",
                    "grey",
                )
        except Exception as e:
            self._log_status(f"Failed to update ASR model '{self.selected_asr_model}': {e}", "red")
            raise

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
            # Check if parakeet_mlx is available, if not, fall back to whisper
            if not PARAKEET_MLX_AVAILABLE:
                self._log_status(f"Parakeet model {model_id} selected but parakeet_mlx not available. Falling back to Whisper.", "orange")
                return "whisper"
            return "parakeet"
        elif "whisper" in model_id_lower:
            return "whisper"
        else:
            # Default to whisper for unknown models
            self._log_status(f"Unknown model type for {model_id}, defaulting to whisper", "orange")
            return "whisper"

    def _detect_whisper_backend(self, model_id: str) -> str:
        """Return 'mlx' for MLX-native repos, otherwise 'transformers'."""
        if not model_id:
            return "mlx"
        mid = model_id.lower()
        if mid.startswith("mlx-community/"):
            return "mlx"
        # Known non-MLX repos commonly using HF Transformers
        if any(mid.startswith(p) for p in [
            "openai/", "na0s/", "crystalcareai/", "distil-whisper/"
        ]):
            return "transformers"
        # Default to MLX if unknown
        return "mlx"

    def _log_status(self, message, color="black"):
        """Helper to call the status update callback if available."""
        # Only mirror to console if minimal terminal mode is disabled
        try:
            from src.config import config as _cfg
            if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
                print(f"TranscriptionHandler Status: {message}")
        except Exception:
            print(f"TranscriptionHandler Status: {message}")
        if self.on_status_update:
            self.on_status_update(message, color)

    def _prepare_local_model_copy(self, hf_repo_id: str) -> str:
        """Ensure a local model copy exists under models/, migrating cache if needed."""
        self._log_status(f"Preparing model locally: {hf_repo_id}", "blue")
        # Target nested directory inside models/, e.g., models/mlx-community/whisper-large-v3-turbo
        target_dir = os.path.join(config.MODELS_ROOT, hf_repo_id.replace("/", os.sep))
        target_parent = os.path.dirname(target_dir)
        try:
            # Ensure models root and nested parent exist
            if not os.path.exists(target_parent):
                os.makedirs(target_parent, exist_ok=True)
                self._log_status(f"Created models directory: {target_parent}", "grey")

            # 1) If already present under models/, use it
            if os.path.isdir(target_dir) and os.path.isfile(os.path.join(target_dir, "config.json")):
                self._log_status(f"Found existing model in models/: {target_dir}", "grey")
                local_model_path = target_dir
            else:
                # 2) Try to migrate from old cache location model_cache_whisper/<repo_underscored>
                legacy_cache_dir = os.path.join(
                    os.path.dirname(config.TEMP_AUDIO_FOLDER),
                    "model_cache_whisper",
                    hf_repo_id.replace("/", "_")
                )
                if os.path.isdir(legacy_cache_dir):
                    # Move legacy cache into models/<org>/<repo>
                    self._log_status(f"Migrating model from cache: {legacy_cache_dir} → {target_dir}", "orange")
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.move(legacy_cache_dir, target_dir)
                    local_model_path = target_dir
                else:
                    # 3) Download directly into models/
                    self._log_status(f"Downloading model into: {target_dir}", "blue")
                    local_model_path = snapshot_download(
                        repo_id=hf_repo_id,
                        local_dir=target_dir,
                        local_dir_use_symlinks=False,
                    )
                    # snapshot_download may return the same local_dir; ensure directory exists
                    if not os.path.isdir(local_model_path):
                        os.makedirs(local_model_path, exist_ok=True)

            self._log_status(f"Model files located at: {local_model_path}", "grey")
        except Exception as e:
            self._log_status(
                f"Error preparing local model for {hf_repo_id}: {e}", "red"
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
            # Also remove certain HF metadata keys not supported by mlx_whisper ModelDimensions
            incompatible_keys.extend([
                "_name_or_path",
            ])
            
            for key in incompatible_keys:
                if key in model_config_json:
                    del model_config_json[key]
                    self._log_status(
                        f"'{key}' key removed from local config.json (incompatible with mlx-whisper)", "yellow"
                    )
                    config_modified = True

            # For Whisper via mlx_whisper, keep only essential architectural keys
            # to avoid unexpected kwargs in ModelDimensions
            try:
                allowed_keys = {
                    "d_model",
                    "decoder_attention_heads",
                    "decoder_layers",
                    "encoder_attention_heads",
                    "encoder_layers",
                    "num_mel_bins",
                    "vocab_size",
                    "num_hidden_layers",
                }
                filtered = {k: v for k, v in model_config_json.items() if k in allowed_keys}
                # Only replace if it reduces keys (avoid accidental expansion)
                if len(filtered) < len(model_config_json):
                    model_config_json = filtered
                    config_modified = True
                    self._log_status(
                        "Pruned config.json to essential keys for mlx-whisper", "yellow"
                    )
            except Exception:
                pass

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

    def _save_temp_audio(self, audio_data) -> str:
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

    def _load_audio_from_file(self, filename: str):
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
        self, audio_data, prompt: str = config.DEFAULT_WHISPER_PROMPT
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

    def _transcribe_thread_worker(self, audio_data, prompt: str):
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
                    # Provide helpful error message instead of mock transcription
                    error_msg = "Parakeet transcription failed"
                    if not PARAKEET_MLX_AVAILABLE:
                        error_msg += " - parakeet_mlx library not installed. Please run: pip install parakeet-mlx"
                    else:
                        error_msg += " - model failed to load"
                    
                    self._log_status(error_msg, "red")
                    raise RuntimeError(error_msg)
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
                if self._whisper_backend == "transformers":
                    # Use Transformers path directly for non-MLX repos
                    self._log_status(f"Using Transformers-Whisper for transcription with model: {self.selected_asr_model}", "blue")
                    if TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE:
                        raw_text = self._transcribe_with_transformers_whisper(filename, self.selected_asr_model, prompt)
                    else:
                        raise RuntimeError("Transformers/Torch not available for selected Whisper model")
                else:
                    self._log_status(f"Using MLX-Whisper for transcription with model: {self.selected_asr_model}", "blue")
                    if not MLX_WHISPER_AVAILABLE:
                        raw_text = "[MOCK WHISPER TRANSCRIPTION] Test transcription result"
                        self._log_status("Whisper transcription mocked - mlx_whisper not available", "orange")
                    else:
                        # Ensure a valid model path or repo id is available
                        model_path_or_repo = self.local_model_path_prepared or self.selected_asr_model
                        fallback_attempted = False
                        while True:
                            try:
                                if not model_path_or_repo:
                                    # Last-resort: attempt to prepare local copy now
                                    self.local_model_path_prepared = self._prepare_local_model_copy(self.selected_asr_model)
                                    model_path_or_repo = self.local_model_path_prepared
                                    self._log_status(
                                        f"Prepared Whisper model on-demand at: {model_path_or_repo}",
                                        "grey",
                                    )
                                # Use mlx_whisper for transcription
                                result = mlx_whisper.transcribe(
                                    filename,
                                    language="en",
                                    fp16=False,
                                    prompt=prompt,
                                    path_or_hf_repo=model_path_or_repo,
                                )
                                raw_text = result.get("text", "").strip()
                                break
                            except Exception as whisper_error:
                                # Fallback once to a known-good ASR if third-party whisper repo is incompatible
                                if fallback_attempted:
                                    raise
                                fallback_attempted = True
                                # Prefer fallback to a known-good MLX Whisper base; if still not possible, try Transformers
                                self._log_status(
                                    f"Whisper model '{self.selected_asr_model}' incompatible ({whisper_error}). Applying fallback...",
                                    "orange",
                                )
                                # Attempt MLX base large-v3
                                model_path_or_repo = "mlx-community/whisper-large-v3-turbo"
                                try:
                                    result = mlx_whisper.transcribe(
                                        filename,
                                        language="en",
                                        fp16=False,
                                        prompt=prompt,
                                        path_or_hf_repo=model_path_or_repo,
                                    )
                                    raw_text = result.get("text", "").strip()
                                    break
                                except Exception:
                                    # As last resort, try Transformers pipeline for the originally selected HF model
                                    if TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE:
                                        self._log_status("Trying Transformers Whisper fallback pipeline...", "orange")
                                        try:
                                            raw_text = self._transcribe_with_transformers_whisper(filename, self.selected_asr_model, prompt)
                                            break
                                        except Exception as tf_err:
                                            self._log_status(f"Transformers fallback failed: {tf_err}", "red")
                                            raise
                                    else:
                                        raise

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

    def _transcribe_with_transformers_whisper(self, audio_path: str, model_id: str, prompt: str) -> str:
        if not (TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE):
            raise RuntimeError("Transformers/Torch not available for Whisper fallback")
        device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
        torch_dtype = torch.float16 if device == "mps" else torch.float32
        # Cache pipelines per model
        if not hasattr(self, "_hf_pipes"):
            self._hf_pipes = {}
        if model_id not in self._hf_pipes:
            processor = AutoProcessor.from_pretrained(model_id)
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True
            )
            if device != "cpu":
                model.to(device)
            pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                torch_dtype=torch_dtype,
                device=0 if device != "cpu" else -1,
            )
            self._hf_pipes[model_id] = pipe
        else:
            pipe = self._hf_pipes[model_id]
        # Whisper models typically cap target length at 448 tokens (max_target_positions)
        # Keep a safety margin to account for special/prompt tokens
        safe_max_new_tokens = 440
        gen_kwargs = {
            "max_new_tokens": safe_max_new_tokens,
            "num_beams": 1,
            "condition_on_prev_tokens": False,
        }
        result = pipe(audio_path, generate_kwargs=gen_kwargs)
        return (result.get("text") or "").strip()


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
        print("\n--- TRANSCRIPTION COMPLETE ---")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Text: {text}")
        print("----------------------------\n")

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
