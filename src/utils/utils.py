import time
from src.config import config
import os


def log_text(label: str, content: str):
    """Logs a message with a timestamp and label to the configured log file with rotation."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} [{label}] {content}\n"
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
