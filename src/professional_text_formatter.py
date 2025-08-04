"""
Professional Text Formatter

Handles specialized formatting for professional text, including bullet point extraction,
text normalization, and mode-specific formatting for proofread and letter modes.
"""

import re
from src.utils.utils import log_text


class ProfessionalTextFormatter:
    """Handles formatting and post-processing of professional text from LLM responses."""
    
    def __init__(self):
        """Initialize the professional text formatter."""
        pass
    
    def post_process_response(self, response_text: str, mode: str) -> str:
        """
        Post-processes the LLM's response based on the mode.
        
        Args:
            response_text: Raw text from LLM
            mode: Processing mode ('proofread', 'letter', etc.)
            
        Returns:
            Formatted text appropriate for the specified mode
        """
        log_text(
            "POST_PROCESS_RESPONSE",
            f"Mode: {mode}, Pre-processed text: '{response_text[:100]}...'",
        )
        
        if mode == "proofread":
            return self._process_proofread_mode(response_text)
        else:  # For 'letter' mode or any other mode
            return self._process_letter_mode(response_text)
    
    def _process_proofread_mode(self, response_text: str) -> str:
        """Process text for proofread mode with bullet point extraction."""
        lines = response_text.splitlines()
        bullet_pattern = re.compile(r"^\s*[-*•]\s+")
        first_block_bullets = []
        in_bullet_block = False

        # First try to extract existing bullet points
        for line in lines:
            is_bullet = bullet_pattern.match(line)
            if is_bullet:
                # Remove the bullet and leading/trailing whitespace from the line itself
                cleaned_line = re.sub(r"^\s*[-*•]\s+", "", line).strip()
                if cleaned_line:  # Only add non-empty lines
                    # Split long bullets into multiple logical bullets
                    if len(cleaned_line) > 200:  # If it's a very long bullet
                        split_bullets = self._split_long_bullet(cleaned_line)
                        first_block_bullets.extend(split_bullets)
                    else:
                        first_block_bullets.append(cleaned_line)
                    in_bullet_block = True
            elif in_bullet_block and line.strip():
                # This is a continuation of the previous bullet, append it
                if first_block_bullets:
                    first_block_bullets[-1] += " " + line.strip()
            # If we hit a blank line or non-bullet after bullets, we're done with this block
            elif in_bullet_block and not line.strip():
                break

        if not first_block_bullets:
            log_text(
                "POST_PROCESS_RESPONSE_WARN",
                "Proofread output did not contain any valid bullet points. Returning original text.",
            )
            return response_text.strip()

        # Join the cleaned bullet points with a standard bullet format
        final_output = "\n".join([f"- {line}" for line in first_block_bullets])
        log_text(
            "POST_PROCESS_RESPONSE",
            f"Post-processed proofread output: '{final_output[:100]}...'",
        )
        return final_output
    
    def _split_long_bullet(self, cleaned_line: str) -> list:
        """Split long bullet points into multiple logical bullets."""
        # Look for logical break points: "The second issue", "He also", etc.
        split_patterns = [
            r"\. The second (?:issue|concern|problem)",
            r"\. The person also",
            r"\. He also",
            r"\. She also",
            r"\. Additionally",
            r"\. Furthermore",
            r"\. He seeks?",
            r"\. Person seeks?",
        ]

        # Try to split on these patterns
        parts = [cleaned_line]
        for pattern in split_patterns:
            new_parts = []
            for part in parts:
                split_parts = re.split(f"({pattern})", part)
                if len(split_parts) > 1:
                    # Reconstruct properly
                    for i in range(0, len(split_parts), 2):
                        if i < len(split_parts):
                            combined = split_parts[i]
                            if i + 1 < len(split_parts):
                                combined += split_parts[i + 1]
                            if combined.strip():
                                new_parts.append(combined.strip())
                else:
                    new_parts.append(part)
            parts = new_parts

        # Return all parts as separate bullets
        return [part.strip() for part in parts if part.strip()]
    
    def _process_letter_mode(self, response_text: str) -> str:
        """Process text for letter mode or any other mode."""
        # Basic strip for now, can be expanded if letter mode needs specific formatting
        final_output = response_text.strip()
        log_text(
            "POST_PROCESS_RESPONSE",
            f"Post-processed letter/other output: '{final_output[:100]}...'",
        )
        return final_output 