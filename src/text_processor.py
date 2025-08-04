#!/usr/bin/env python3
"""
Text Processor for CitrixTranscriber
Handles post-processing of transcribed text including filler word removal.
"""

import re
from typing import List, Set
from src.config.settings_manager import settings_manager

class TextProcessor:
    """Handles text post-processing operations."""
    
    def __init__(self):
        """Initialize the text processor."""
        self._filler_words_cache = None
        self._filler_words_regex = None
        self._update_filler_words()
    
    def _update_filler_words(self):
        """Update the filler words list and regex from settings."""
        filler_words = settings_manager.get_setting("fillerWords", [])
        self._filler_words_cache = set(word.lower() for word in filler_words)
        
        # Create regex pattern for efficient removal
        if filler_words:
            # Create pattern that matches filler words as standalone words
            # \b ensures word boundaries, re.IGNORECASE makes it case-insensitive
            escaped_words = [re.escape(word) for word in filler_words]
            pattern = r'\b(?:' + '|'.join(escaped_words) + r')\b'
            self._filler_words_regex = re.compile(pattern, re.IGNORECASE)
        else:
            self._filler_words_regex = None
    
    def remove_filler_words(self, text: str) -> str:
        """
        Remove filler words from text.
        
        Args:
            text: Input text
            
        Returns:
            Text with filler words removed
        """
        if not text or not settings_manager.get_setting("filterFillerWords", False):
            return text
        
        # Update filler words if settings changed
        current_filler_words = set(word.lower() for word in settings_manager.get_setting("fillerWords", []))
        if current_filler_words != self._filler_words_cache:
            self._update_filler_words()
        
        if not self._filler_words_regex:
            return text
        
        # Remove filler words
        result = self._filler_words_regex.sub('', text)
        
        # Clean up punctuation and spacing issues
        # Remove orphaned commas that appear after removing filler words
        result = re.sub(r',\s*,', ',', result)  # Multiple commas -> single comma
        result = re.sub(r'^\s*,\s*', '', result)  # Comma at start
        result = re.sub(r',\s*([.!?])', r'\1', result)  # Comma before punctuation
        result = re.sub(r'\s*,\s*$', '', result)  # Comma at end
        
        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def clean_text(self, text: str) -> str:
        """
        Apply all text cleaning operations.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text:
            return text
        
        # Apply filler word removal
        cleaned = self.remove_filler_words(text)
        
        # Additional cleaning operations can be added here
        # e.g., punctuation correction, capitalization, etc.
        
        return cleaned
    
    def set_filler_words(self, filler_words: List[str]) -> None:
        """
        Update the list of filler words.
        
        Args:
            filler_words: List of filler words to remove
        """
        settings_manager.set_setting("fillerWords", filler_words)
        self._update_filler_words()
    
    def get_filler_words(self) -> List[str]:
        """Get the current list of filler words."""
        return settings_manager.get_setting("fillerWords", [])
    
    def set_filter_enabled(self, enabled: bool) -> None:
        """
        Enable or disable filler word filtering.
        
        Args:
            enabled: Whether to filter filler words
        """
        settings_manager.set_setting("filterFillerWords", enabled)
    
    def is_filter_enabled(self) -> bool:
        """Check if filler word filtering is enabled."""
        return settings_manager.get_setting("filterFillerWords", False)


# Global text processor instance
text_processor = TextProcessor() 