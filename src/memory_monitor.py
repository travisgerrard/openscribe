import os
import sys
import psutil
import time
import threading
import traceback
from typing import Dict, Optional, Callable
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class MemoryStats:
    """Container for memory statistics."""

    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory usage percentage
    process_name: str
    thread_count: int
    audio_frames: Optional[int] = None
    ring_buffer_size: Optional[int] = None
    voiced_frames_size: Optional[int] = None


class MemoryMonitor:
    """Monitors memory usage of the application."""

    def __init__(self, log_interval: int = 10, log_to_file: bool = True):
        try:
            from src.config import config as _cfg
            if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
                print("!!!!!!!!!! EXECUTING MODIFIED MemoryMonitor.__init__ !!!!!!!!!!!!")
        except Exception:
            pass
        """
        Initialize the memory monitor.
        
        Args:
            log_interval: How often to log memory stats (in seconds)
            log_to_file: Whether to log to a file
        """
        self.log_interval = log_interval
        self.log_to_file = log_to_file
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._process = psutil.Process(os.getpid())
        self._log_file = os.path.join(os.path.dirname(__file__), "memory_logs.jsonl")
        self._transcript_log = os.path.join(
            os.path.dirname(__file__), "transcript_log.txt"
        )
        self._callbacks = []

        # Ensure log directory exists and clean up old logs
        os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
        self._cleanup_logs()

    def start(self) -> None:
        try:
            from src.config import config as _cfg
            if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
                print(
                    "[DEBUG] MemoryMonitor.start() CALLED - THIS IS THE NEW SIMPLIFIED VERSION - SHOULD BE DISABLED!"
                )
        except Exception:
            pass
        return

    def stop(self) -> None:
        """Stop the memory monitoring thread."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def register_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """Register a callback to receive memory stats."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def log_operation(self, operation: str, additional_data: dict = None):
        """Log a memory-related operation with current stats"""
        try:
            mem_info = self._process.memory_info()
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
                "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
                "percent": round(self._process.memory_percent(), 2),
                "process": self._process.name(),
                "threads": self._process.num_threads(),
            }

            if additional_data:
                log_entry.update(additional_data)

            # Log to file only
            if self.log_to_file:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            print(f"Error in log_operation: {e}")

    def log_proofing_operation(
        self,
        operation: str,
        model_name: str = None,
        input_length: int = None,
        output_length: int = None,
        duration: float = None,
        **extra,
    ):
        """
        Log memory usage for proofing operations.

        Args:
            operation: Type of proofing operation (e.g., 'proof_start', 'proof_complete')
            model_name: Name of the model being used
            input_length: Length of input text in characters
            output_length: Length of output text in characters
            duration: Time taken for the operation in seconds
            **extra: Additional key-value pairs to include in the log
        """
        mem_info = self._process.memory_info()
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
            "percent": round(self._process.memory_percent(), 2),
            "process": self._process.name(),
            "threads": self._process.num_threads(),
        }

        # Add optional fields if provided
        if model_name is not None:
            log_entry["model"] = model_name
        if input_length is not None:
            log_entry["input_length"] = input_length
        if output_length is not None:
            log_entry["output_length"] = output_length
        if duration is not None:
            log_entry["duration_sec"] = round(duration, 2)

        # Add any extra fields
        if extra:
            log_entry.update(extra)

        # Removed excessive console spam: print(f"[PROOFING_MEM] {json.dumps(log_entry, indent=2)}")
        if self.log_to_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                print(f"Error writing proofing log: {e}")

    def get_memory_stats(self, audio_handler=None) -> MemoryStats:
        """Get current memory statistics."""
        try:
            mem_info = self._process.memory_info()
            thread_count = self._process.num_threads()

            stats = MemoryStats(
                timestamp=time.time(),
                rss_mb=mem_info.rss / (1024 * 1024),  # Convert to MB
                vms_mb=mem_info.vms / (1024 * 1024),  # Convert to MB
                percent=self._process.memory_percent(),
                process_name=self._process.name(),
                thread_count=thread_count,
            )

            # Add audio handler specific stats if available
            if audio_handler and hasattr(audio_handler, "_voiced_frames"):
                stats.audio_frames = len(audio_handler._voiced_frames)
                stats.ring_buffer_size = (
                    len(audio_handler._ring_buffer)
                    if hasattr(audio_handler, "_ring_buffer")
                    else 0
                )
                stats.voiced_frames_size = sum(
                    sys.getsizeof(frame) for frame in audio_handler._voiced_frames
                ) / (
                    1024 * 1024
                )  # Convert to MB

            return stats

        except Exception as e:
            print(f"Error getting memory stats: {e}")
            traceback.print_exc()
            return None

    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        try:
            from src.config import config as _cfg
            if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
                print(
                    "[DEBUG] MemoryMonitor._monitor_loop() CALLED - THIS IS THE NEW SIMPLIFIED VERSION - SHOULD BE DISABLED!"
                )
        except Exception:
            pass
        return

    def _log_stats(
        self, stats: MemoryStats, marker: str = None, extra: dict = None
    ) -> None:
        """Log memory statistics."""
        try:
            # Format the log entry
            log_entry = {
                "timestamp": datetime.fromtimestamp(stats.timestamp).isoformat(),
                "rss_mb": round(stats.rss_mb, 2),
                "vms_mb": round(stats.vms_mb, 2),
                "percent": round(stats.percent, 2),
                "process": stats.process_name,
                "threads": stats.thread_count,
            }
            if marker:
                log_entry["marker"] = marker
            if extra:
                log_entry.update(extra)
            # Add audio-specific stats if available
            if stats.audio_frames is not None:
                log_entry.update(
                    {
                        "audio_frames": stats.audio_frames,
                        "ring_buffer_size": stats.ring_buffer_size,
                        "voiced_frames_mb": (
                            round(stats.voiced_frames_size, 2)
                            if stats.voiced_frames_size
                            else 0
                        ),
                    }
                )
            # Write only to file
            if self.log_to_file:
                try:
                    with open(self._log_file, "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                except Exception as e:
                    print(f"Error writing to memory log file: {e}")
        except Exception as e:
            print(f"Error logging memory stats: {e}")
            traceback.print_exc()

    def _cleanup_logs(self) -> None:
        """Clean up log files at startup."""
        log_files = [self._log_file, self._transcript_log]

        for log_file in log_files:
            try:
                if os.path.exists(log_file):
                    # Open in write mode to clear the file
                    with open(log_file, "w") as f:
                        f.write("")
                    try:
                        from src.config import config as _cfg
                        if not getattr(_cfg, "MINIMAL_TERMINAL_OUTPUT", False):
                            print(f"Cleared log file: {log_file}")
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error cleaning up log file {log_file}: {e}")
                traceback.print_exc()


# Global instance for easy access
memory_monitor = MemoryMonitor(log_interval=5)  # Log every 5 seconds by default


def start_memory_monitoring():
    """Start the global memory monitor."""
    memory_monitor.start()


def stop_memory_monitoring():
    """Stop the global memory monitor."""
    memory_monitor.stop()


def get_memory_usage() -> Dict:
    """Get current memory usage statistics."""
    stats = memory_monitor.get_memory_stats()
    if stats:
        return {
            "rss_mb": round(stats.rss_mb, 2),
            "vms_mb": round(stats.vms_mb, 2),
            "percent": round(stats.percent, 2),
            "process": stats.process_name,
            "threads": stats.thread_count,
            "timestamp": datetime.fromtimestamp(stats.timestamp).isoformat(),
        }
    return {"error": "Failed to get memory stats"}
