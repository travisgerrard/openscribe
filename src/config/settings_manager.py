#!/usr/bin/env python3
"""
Settings Manager for CitrixTranscriber
Handles saving and loading user preferences between sessions.
"""

import json
import os
from typing import Dict, Any, Optional
from src.config import config

class SettingsManager:
    """Manages user settings persistence."""
    
    def __init__(self, settings_file: str = "user_settings.json"):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Path to the settings file
        """
        self.settings_file = settings_file
        self.settings = self._load_default_settings()
        self.load_settings()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default settings from config."""
        return {
            "selectedAsrModel": config.DEFAULT_ASR_MODEL,
            "selectedProofingModel": config.DEFAULT_LLM,
            "selectedLetterModel": config.DEFAULT_LLM,
            "programActive": True,
            "wakeWords": config.WAKE_WORDS,
            "proofingPrompt": config.DEFAULT_PROOFREAD_PROMPT,
            "letterPrompt": config.DEFAULT_LETTER_PROMPT,
            "filterFillerWords": True,  # New setting for filler word filtering
            "fillerWords": ["um", "uh", "ah", "er", "hmm", "mm", "mhm"]  # Default filler words
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file.
        
        Returns:
            Dictionary of loaded settings
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.settings.update(saved_settings)
                    print(f"[Settings] Loaded from {self.settings_file}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Settings] Error loading {self.settings_file}: {e}")
                print(f"[Settings] Using default settings")
        else:
            print(f"[Settings] No settings file found, using defaults")
        
        return self.settings
    
    def save_settings(self) -> bool:
        """
        Save current settings to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.settings_file)), exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            print(f"[Settings] Saved to {self.settings_file}")
            return True
        except IOError as e:
            print(f"[Settings] Error saving {self.settings_file}: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
            save: Whether to save to file immediately
        """
        self.settings[key] = value
        if save:
            self.save_settings()
    
    def update_settings(self, new_settings: Dict[str, Any], save: bool = True) -> None:
        """
        Update multiple settings.
        
        Args:
            new_settings: Dictionary of settings to update
            save: Whether to save to file immediately
        """
        self.settings.update(new_settings)
        if save:
            self.save_settings()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self.settings.copy()


# Global settings manager instance
settings_manager = SettingsManager() 