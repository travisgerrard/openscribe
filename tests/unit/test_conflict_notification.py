#!/usr/bin/env python3
"""
Unit tests for the microphone conflict notification system.
Tests the prominent conflict banner and user feedback functionality.
"""

import unittest
import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestConflictNotificationSystem(unittest.TestCase):
    """Test the conflict notification system components."""

    def test_html_conflict_banner_structure(self):
        """Test that the HTML contains the conflict notification banner structure."""
        try:
            # Read the index.html file to verify banner structure
            with open('frontend/main/index.html', 'r') as f:
                html_content = f.read()

            # Verify conflict banner elements exist
            self.assertIn('id="mic-conflict-banner"', html_content)
            self.assertIn('class="mic-conflict-banner hidden"', html_content)
            self.assertIn('id="conflict-message"', html_content)
            self.assertIn('id="conflict-dismiss"', html_content)
            self.assertIn('Microphone Conflict Detected', html_content)
            self.assertIn('Close browser dictation tabs', html_content)

        except FileNotFoundError:
            self.fail("index.html file not found")

    def test_css_conflict_styles_exist(self):
        """Test that CSS includes the conflict notification styling."""
        try:
            # Read the style.css file to verify conflict styling
            with open('frontend/styles/style.css', 'r') as f:
                css_content = f.read()

            # Verify conflict banner styles exist
            self.assertIn('.mic-conflict-banner', css_content)
            self.assertIn('.conflict-icon', css_content)
            self.assertIn('.conflict-content', css_content)
            self.assertIn('.conflict-dismiss', css_content)
            self.assertIn('@keyframes pulse-warning', css_content)
            self.assertIn('linear-gradient(135deg, #ff6b35, #ff8e53)', css_content)
            self.assertIn('conflict-banner-visible', css_content)

        except FileNotFoundError:
            self.fail("style.css file not found")

    def test_conflict_ui_javascript_structure(self):
        """Test that the conflict UI JavaScript module has proper structure."""
        try:
            # Read the renderer_conflict_ui.js file to verify structure
            with open('frontend/shared/renderer_conflict_ui.js', 'r') as f:
                js_content = f.read()

            # Verify ConflictNotificationManager class exists
            self.assertIn('class ConflictNotificationManager', js_content)
            self.assertIn('showConflictBanner', js_content)
            self.assertIn('hideConflictBanner', js_content)
            self.assertIn('updateConflictMessage', js_content)
            self.assertIn('isConflictVisible', js_content)
            self.assertIn('setupEventListeners', js_content)
            self.assertIn('setupAutoHide', js_content)

            # Verify export statements
            self.assertIn('export { conflictNotificationManager }', js_content)
            self.assertIn('window.conflictNotificationManager', js_content)

        except FileNotFoundError:
            self.fail("renderer_conflict_ui.js file not found")

    def test_renderer_state_integration(self):
        """Test that renderer state properly integrates conflict detection."""
        try:
            # Read the renderer_state.js file to verify integration
            with open('frontend/shared/renderer_state.js', 'r') as f:
                state_content = f.read()

            # Verify conflict notification integration
            self.assertIn('import { conflictNotificationManager }', state_content)
            self.assertIn('handleStatusMessage', state_content)
            self.assertIn('hideConflictNotification', state_content)
            self.assertIn('isConflictNotificationVisible', state_content)
            self.assertIn('lastConflictCheck', state_content)

            # Verify conflict detection keywords
            self.assertIn('microphone conflict detected', state_content)
            self.assertIn('detected active conflict', state_content)
            self.assertIn('definitiveConflictPhrases', state_content)

        except FileNotFoundError:
            self.fail("renderer_state.js file not found")

    def test_renderer_ipc_integration(self):
        """Test that renderer IPC properly integrates conflict detection."""
        try:
            # Read the renderer_ipc.js file to verify integration
            with open('frontend/shared/renderer_ipc.js', 'r') as f:
                ipc_content = f.read()

            # Verify IPC integration
            self.assertIn('import { updateStatusIndicator, handleStatusMessage }', ipc_content)
            self.assertIn('handleStatusMessage(statusText, color)', ipc_content)

            # Verify proper extraction of color and status text
            self.assertIn('const color = fullStatusMessage.substring(0, firstColorColonIndex)', ipc_content)
            self.assertIn('const statusText = messageAfterColor', ipc_content)

        except FileNotFoundError:
            self.fail("renderer_ipc.js file not found")


class TestConflictDetectionLogic(unittest.TestCase):
    """Test the logic for detecting different types of microphone conflicts."""

    def test_conflict_keywords_coverage(self):
        """Test that conflict detection covers all expected keywords."""
        try:
            # Read the renderer_state.js file to verify conflict keywords
            with open('frontend/shared/renderer_state.js', 'r') as f:
                state_content = f.read()

            # Expected definitive conflict phrases for precise detection
            expected_phrases = [
                'microphone conflict detected',
                'detected active conflict',
                'conflicting application detected',
                'microphone access blocked',
                'another application is using the microphone',
                'audio input conflict'
            ]

            for phrase in expected_phrases:
                self.assertIn(f"'{phrase}'", state_content, f"Missing conflict phrase: {phrase}")

            # Verify that overly broad keywords are not used anymore
            overly_broad_keywords = [
                "'sustained silent data'",
                "'silent/empty audio data'"
            ]
            
            for keyword in overly_broad_keywords:
                self.assertNotIn(keyword, state_content, f"Found overly broad keyword that should be removed: {keyword}")

        except FileNotFoundError:
            self.fail("renderer_state.js file not found")

    def test_suggestion_message_detection(self):
        """Test that suggestion messages are properly identified."""
        try:
            # Read the renderer_state.js file to verify suggestion detection
            with open('frontend/shared/renderer_state.js', 'r') as f:
                state_content = f.read()

            # Verify suggestion message detection logic
            self.assertIn('isSuggestionMessage', state_content)
            self.assertIn("statusText.includes('💡')", state_content)
            self.assertIn("statusText.toLowerCase().includes('note:')", state_content)
            self.assertIn("statusText.toLowerCase().includes('tip:')", state_content)

        except FileNotFoundError:
            self.fail("renderer_state.js file not found")

    def test_cooldown_mechanism(self):
        """Test that conflict notifications have proper cooldown to avoid spam."""
        try:
            # Read the renderer_state.js file to verify cooldown mechanism
            with open('frontend/shared/renderer_state.js', 'r') as f:
                state_content = f.read()

            # Verify cooldown logic exists
            self.assertIn('lastConflictCheck', state_content)
            self.assertIn('5000', state_content)  # 5 second cooldown
            self.assertIn('5 second cooldown', state_content)

        except FileNotFoundError:
            self.fail("renderer_state.js file not found")


class TestConflictNotificationFeatures(unittest.TestCase):
    """Test specific features of the conflict notification system."""

    def test_auto_hide_functionality(self):
        """Test that conflict notifications auto-hide after a delay."""
        try:
            # Read the renderer_conflict_ui.js file to verify auto-hide
            with open('frontend/shared/renderer_conflict_ui.js', 'r') as f:
                js_content = f.read()

            # Verify auto-hide functionality
            self.assertIn('setupAutoHide', js_content)
            self.assertIn('15000', js_content)  # 15 second auto-hide
            self.assertIn('15 seconds', js_content)
            self.assertIn('autoHideTimer', js_content)
            self.assertIn('clearTimeout', js_content)

        except FileNotFoundError:
            self.fail("renderer_conflict_ui.js file not found")

    def test_dismissible_notification(self):
        """Test that conflict notifications can be manually dismissed."""
        try:
            # Read the renderer_conflict_ui.js file to verify dismiss functionality
            with open('frontend/shared/renderer_conflict_ui.js', 'r') as f:
                js_content = f.read()

            # Verify dismiss functionality
            self.assertIn('conflict-dismiss', js_content)
            self.assertIn('addEventListener', js_content)
            self.assertIn('hideConflictBanner', js_content)
            self.assertIn('dismissButton', js_content)

        except FileNotFoundError:
            self.fail("renderer_conflict_ui.js file not found")

    def test_visual_prominence_features(self):
        """Test that the notification is visually prominent."""
        try:
            # Read the style.css file to verify visual prominence
            with open('frontend/styles/style.css', 'r') as f:
                css_content = f.read()

            # Verify prominent visual features
            self.assertIn('position: fixed', css_content)
            self.assertIn('top: 0', css_content)
            self.assertIn('z-index: 1000', css_content)
            self.assertIn('box-shadow:', css_content)
            self.assertIn('animation: pulse-warning', css_content)
            self.assertIn('linear-gradient', css_content)

        except FileNotFoundError:
            self.fail("style.css file not found")

    def test_responsive_message_updates(self):
        """Test that conflict messages can be updated dynamically."""
        try:
            # Read the renderer_conflict_ui.js file to verify update capability
            with open('frontend/shared/renderer_conflict_ui.js', 'r') as f:
                js_content = f.read()

            # Verify message update functionality
            self.assertIn('updateConflictMessage', js_content)
            self.assertIn('conflictMessage.textContent = newMessage', js_content)
            self.assertIn('Reset auto-hide timer', js_content)

        except FileNotFoundError:
            self.fail("renderer_conflict_ui.js file not found")


if __name__ == '__main__':
    print("Running conflict notification system tests...")
    unittest.main(verbosity=2) 