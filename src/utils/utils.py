import time
from src.config import config
import os


def log_text(label: str, content: str):
    """Logs a message with a timestamp and label to the configured log file with rotation."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} [{label}] {content}\n"
    # Controlled terminal printing: keep stdout quiet unless label is whitelisted or minimal mode is off
    try:
        if not getattr(config, "MINIMAL_TERMINAL_OUTPUT", False) or (
            hasattr(config, "TERMINAL_LOG_WHITELIST") and label in config.TERMINAL_LOG_WHITELIST
        ):
            print(log_entry.strip())
    except Exception:
        # Fall back to printing on any config access error
        print(log_entry.strip())

    try:
        # Check if log file exists and rotate if it's too large
        if (
            os.path.exists(config.LOG_FILE)
            and os.path.getsize(config.LOG_FILE) > 1024 * 1024
        ):  # 1MB
            # Simple rotation: rename existing file with a number suffix
            os.replace(config.LOG_FILE, config.LOG_FILE + ".old")

        with open(config.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"Error writing to log file {config.LOG_FILE}: {e}")
