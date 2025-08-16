"""
Legacy compatibility shim for tests or modules importing `settings_manager` from project root.
Re-exports the actual implementation from `src.config.settings_manager`.
"""

from src.config.settings_manager import SettingsManager, settings_manager  # noqa: F401



