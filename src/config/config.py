import pyaudio
import os
import sys

# Make pynput imports conditional for CI compatibility
try:
    from pynput.keyboard import Key, KeyCode  # Import necessary keys
    PYNPUT_AVAILABLE = True
except ImportError:
    # pynput not available (CI environment)
    PYNPUT_AVAILABLE = False
    print("[WARN] pynput not available in config.py - using mock classes")
    # Create minimal mock classes for configuration
    class MockKey:
        cmd = "cmd"
        shift = "shift"
        alt = "alt"
        ctrl = "ctrl"
    
    class MockKeyCode:
        @staticmethod
        def from_char(char):
            class CharKey:
                def __init__(self, char):
                    self.char = char
                def __hash__(self):
                    return hash(self.char)
                def __eq__(self, other):
                    return hasattr(other, 'char') and self.char == other.char
            return CharKey(char)
    
    Key = MockKey()
    KeyCode = MockKeyCode()

# --- Path Resolution ---
def get_bundle_resource_path():
    """
    Get the path to the app bundle's Resources directory.
    Returns None if not running as a bundled app.
    """
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        # sys.executable points to the bundled executable
        # Navigate up to Resources directory
        executable_path = sys.executable
        # From: .../CitrixTranscriberBackend.app/Contents/MacOS/citrix-transcriber-backend
        # To: .../Resources/
        macos_dir = os.path.dirname(executable_path)
        backend_contents_dir = os.path.dirname(macos_dir)
        backend_app_dir = os.path.dirname(backend_contents_dir)
        resources_dir = os.path.dirname(backend_app_dir)
        return resources_dir
    return None

def resolve_resource_path(relative_path):
    """
    Resolve a resource path, handling both development and bundled modes.
    """
    bundle_resources = get_bundle_resource_path()
    if bundle_resources:
        # Running as bundled app - use absolute path from Resources
        return os.path.join(bundle_resources, relative_path)
    else:
        # Running in development - use relative path
        return relative_path

# --- Audio Parameters ---
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
VAD_AGGRESSIVENESS = 1  # 0 (least aggressive) to 3 (most aggressive) - Reduced to fix silence detection
SILENCE_THRESHOLD_SECONDS = 1.5  # How long silence triggers processing
RING_BUFFER_DURATION_MS = 600  # How much audio to keep before trigger

# --- Paths ---
VOSK_MODEL_PATH = resolve_resource_path("vosk")
LOG_FILE = resolve_resource_path("transcript_log.txt")
TEMP_AUDIO_FOLDER = resolve_resource_path("temp_audio")
CHIME_SOUND_FILE = resolve_resource_path("chime.wav")  # Currently unused, but kept for potential future use

# --- Model Configurations ---
LLM_TEMPERATURE = 0.1  # Controls randomness, lower is more deterministic
LLM_SAMPLERS = []  # e.g., ["top_k", "top_p"] if supported and desired
LLM_REPETITION_PENALTY = (
    1.1  # Penalizes repetition, typical values are 1.0 (no penalty) to 1.2
)
LLM_TOP_P = 0.95  # Nucleus sampling: considers the smallest set of tokens whose cumulative probability exceeds top_p
LLM_MAX_TOKENS_TO_GENERATE = 4096  # Maximum number of tokens the LLM should generate (increased for DeepSeek R1 reasoning models)
AVAILABLE_ASR_MODELS = {
    "Whisper (large-v3-turbo)": "mlx-community/whisper-large-v3-turbo",
    "Parakeet-TDT-0.6B-v2": "mlx-community/parakeet-tdt-0.6b-v2",
}
DEFAULT_ASR_MODEL = "mlx-community/parakeet-tdt-0.6b-v2"

# WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo" # Or choose another compatible model
# WHISPER_MODEL = "mlx-community/parakeet-tdt-0.6b-v2" # Or choose another compatible model
DEFAULT_LLM = "mlx-community/Qwen3-8B-4bit"
AVAILABLE_LLMS = {
    "Qwen3-8B-4bit": "mlx-community/Qwen3-8B-4bit",
    "Qwen3-14B-4bit-AWQ": "mlx-community/Qwen3-14B-4bit-AWQ",
    "DeepSeek-R1-DWQ-8B-4bit": "mlx-community/DeepSeek-R1-0528-Qwen3-8B-4bit-DWQ",
    # Add other models as needed
}

# --- Prompts ---
DEFAULT_WHISPER_PROMPT = (
    "You are transcribing a professional encounter for documentation. "
    "Ensure the transcription is accurate, concise, and formatted appropriately. "
    "Use appropriate terminology when needed."
)

DEFAULT_PROOFREAD_PROMPT = (
    "You are proofreading text that will be entered into a professional document.\n"
    "Correct any grammatical errors, spelling mistakes, or awkward phrasing.\n"
    "Ensure the text is clear, concise, and maintains accuracy.\n"
    # "Return only the corrected version without adding any extra comments, context, or introductory phrases."
)

DEFAULT_LETTER_PROMPT = (
    "You are finalizing text that will be sent as a professional message.\n"
    "Ensure the text is grammatically correct, clear, concise, and maintains accuracy.\n"
    "Format it appropriately for professional communication.\n"
    "Return only the finalized message without adding any extra comments, context, or introductory phrases."
)

# --- Hotkeys ---
# Define commands associated with hotkeys
COMMAND_TOGGLE_ACTIVE = "toggle_active"
COMMAND_START_DICTATE = "start_dictate"
COMMAND_START_PROOFREAD = "start_proofread"
COMMAND_START_LETTER = "start_letter"
COMMAND_STOP_DICTATE = "stop_dictate"  # Added for explicit stop hotkey
COMMAND_ABORT_DICTATE = "abort_dictate"  # Added for abort/cancel hotkey
COMMAND_RESTART = "restart"
COMMAND_SHOW_HOTKEYS = "show_hotkeys"
COMMAND_TOGGLE_MINI_MODE = "toggle_mini_mode"  # Added for mini mode toggle

# --- Wake Words ---
# Define words for different activation commands
# Structure: { category: [list_of_words] }
# Categories should match keys in command_map in audio_handler.py
WAKE_WORDS = {
    "dictate": ["note", "dictation", "dictate"],
    "proofread": ["proof", "proofread"],
    "letter": ["letter"],
}

# Define key combinations (using pynput format)
# Use Key.cmd for Command, Key.alt for Option, Key.ctrl for Control, Key.shift for Shift
# Example: {Key.cmd, Key.shift, 'a'}
HOTKEY_COMBINATIONS = {
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("a")}): COMMAND_TOGGLE_ACTIVE,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("d")}): COMMAND_START_DICTATE,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("p")}): COMMAND_START_PROOFREAD,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("l")}): COMMAND_START_LETTER,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("s")}): COMMAND_STOP_DICTATE,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("r")}): COMMAND_RESTART,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("h")}): COMMAND_SHOW_HOTKEYS,
    frozenset({Key.cmd, Key.shift, KeyCode.from_char("m")}): COMMAND_TOGGLE_MINI_MODE,
}

# --- GUI ---
APP_TITLE = "Professional Dictation Transcriber"
DEFAULT_THEME = "arc"  # Example theme, requires ttkthemes

# --- Other ---
TOKENIZERS_PARALLELISM = "false"  # Environment variable setting
LOG_TEXT_DETAIL_LEVEL = 1  # 0 = basic, 1 = detailed, etc. (currently informational)
SEND_TO_CITRIX_ENABLED = True  # Set to False to only copy to clipboard without pasting
