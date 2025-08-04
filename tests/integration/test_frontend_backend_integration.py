#!/usr/bin/env python3
"""
Integration tests for frontend-backend connectivity after file reorganization.
These tests ensure that the interconnects work properly after moving files around.
"""

import os
import sys
import json
import subprocess
import time
import unittest
from pathlib import Path
import re

class FrontendBackendIntegrationTest(unittest.TestCase):
    """Test suite to validate frontend-backend connectivity after file reorganization."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.frontend_main_dir = self.project_root / "frontend" / "main"
        self.frontend_shared_dir = self.project_root / "frontend" / "shared"
        self.frontend_styles_dir = self.project_root / "frontend" / "styles"

    def test_file_organization_integrity(self):
        """Test that all files are in their expected locations after reorganization."""
        
        # Frontend main files
        main_files = [
            self.frontend_main_dir / "index.html",
            self.frontend_main_dir / "renderer.js",
            self.frontend_main_dir / "preload.js"
        ]
        
        for file_path in main_files:
            self.assertTrue(file_path.exists(), f"Missing main file: {file_path}")

        # Frontend shared files
        shared_files = [
            self.frontend_shared_dir / "renderer_ipc.js",
            self.frontend_shared_dir / "renderer_state.js",
            self.frontend_shared_dir / "renderer_waveform.js",
            self.frontend_shared_dir / "renderer_controls.js",
            self.frontend_shared_dir / "renderer_expansion_ui.js",
            self.frontend_shared_dir / "renderer_utils.js",
            self.frontend_shared_dir / "renderer_conflict_ui.js",
            self.frontend_shared_dir / "renderer_ui.js"
        ]
        
        for file_path in shared_files:
            self.assertTrue(file_path.exists(), f"Missing shared file: {file_path}")

        # CSS files
        css_files = [
            self.frontend_styles_dir / "style.css"
        ]
        
        for file_path in css_files:
            self.assertTrue(file_path.exists(), f"Missing CSS file: {file_path}")

    def test_renderer_import_paths(self):
        """Test that renderer.js has correct import paths after reorganization."""
        
        renderer_file = self.frontend_main_dir / "renderer.js"
        self.assertTrue(renderer_file.exists(), "renderer.js not found")
        
        with open(renderer_file, 'r') as f:
            content = f.read()
        
        # Check for correct relative import paths
        expected_imports = [
            "from '../shared/renderer_waveform.js'",
            "from '../shared/renderer_ipc.js'",
            "from '../shared/renderer_utils.js'",
            "from '../shared/renderer_expansion_ui.js'",
            "from '../shared/renderer_state.js'",
            "from '../shared/renderer_controls.js'"
        ]
        
        for expected_import in expected_imports:
            self.assertIn(expected_import, content, 
                         f"Missing or incorrect import path: {expected_import}")
        
        # Check that old (broken) import paths are not present
        broken_imports = [
            "from './renderer_waveform.js'",
            "from './renderer_ipc.js'",
            "from './renderer_utils.js'",
            "from './renderer_expansion_ui.js'",
            "from './renderer_state.js'",
            "from './renderer_controls.js'"
        ]
        
        for broken_import in broken_imports:
            self.assertNotIn(broken_import, content,
                           f"Found broken import path: {broken_import}")

    def test_css_link_paths(self):
        """Test that index.html has correct CSS link paths after reorganization."""
        
        index_file = self.frontend_main_dir / "index.html"
        self.assertTrue(index_file.exists(), "index.html not found")
        
        with open(index_file, 'r') as f:
            content = f.read()
        
        # Check for correct CSS link path
        self.assertIn('href="../styles/style.css"', content,
                     "Missing or incorrect CSS link path")
        
        # Check that old (broken) CSS path is not present
        self.assertNotIn('href="style.css"', content,
                        "Found broken CSS link path")

    def test_shared_modules_cross_imports(self):
        """Test that shared modules correctly import from each other."""
        
        # Test renderer_state.js imports
        state_file = self.frontend_shared_dir / "renderer_state.js"
        with open(state_file, 'r') as f:
            state_content = f.read()
        
        expected_state_imports = [
            "from './renderer_ui.js'",
            "from './renderer_conflict_ui.js'"
        ]
        
        for expected_import in expected_state_imports:
            self.assertIn(expected_import, state_content,
                         f"Missing import in renderer_state.js: {expected_import}")

        # Test renderer_ipc.js imports
        ipc_file = self.frontend_shared_dir / "renderer_ipc.js"
        with open(ipc_file, 'r') as f:
            ipc_content = f.read()
        
        expected_ipc_imports = [
            "from './renderer_utils.js'",
            "from './renderer_state.js'",
            "from './renderer_ui.js'"
        ]
        
        for expected_import in expected_ipc_imports:
            self.assertIn(expected_import, ipc_content,
                         f"Missing import in renderer_ipc.js: {expected_import}")

    def test_tray_icon_functionality(self):
        """Test that tray icon state management works correctly."""
        
        # Check electron_tray.js exists and has proper functions
        tray_file = self.project_root / "electron_tray.js"
        self.assertTrue(tray_file.exists(), "electron_tray.js not found")
        
        with open(tray_file, 'r') as f:
            tray_content = f.read()
        
        required_functions = [
            "function setTrayIconByState",
            "setTrayIcon",
            "inactive",
            "activation", 
            "dictation",
            "processing"
        ]
        
        for func in required_functions:
            self.assertIn(func, tray_content,
                         f"Missing tray functionality: {func}")

    def test_electron_python_status_processing(self):
        """Test that electron_python.js properly processes STATUS messages for tray updates."""
        
        electron_python_file = self.project_root / "electron_python.js"
        self.assertTrue(electron_python_file.exists(), "electron_python.js not found")
        
        with open(electron_python_file, 'r') as f:
            content = f.read()
        
        # Check for STATUS message processing
        self.assertIn("if (trimmedMessage.startsWith('STATUS:'))", content,
                     "Missing STATUS message processing")
        
        # Check for tray icon state mapping
        status_checks = [
            "Listening for activation words",
            "Listening for dictation",
            "Dictation started",
            "Loading",
            "Processing"
        ]
        
        for check in status_checks:
            self.assertIn(check, content,
                         f"Missing STATUS message check: {check}")

    def test_conflict_notification_styling(self):
        """Test that conflict notification has proper styling."""
        
        css_file = self.frontend_styles_dir / "style.css"
        with open(css_file, 'r') as f:
            css_content = f.read()
        
        required_css_classes = [
            ".mic-conflict-banner",
            ".conflict-title",
            ".conflict-message",
            ".conflict-dismiss",
            ".conflict-content"
        ]
        
        for css_class in required_css_classes:
            self.assertIn(css_class, css_content,
                         f"Missing CSS class: {css_class}")

    def test_critical_ui_elements_exist(self):
        """Test that critical UI elements exist in index.html."""
        
        index_file = self.frontend_main_dir / "index.html"
        with open(index_file, 'r') as f:
            html_content = f.read()
        
        critical_elements = [
            'id="mic-conflict-banner"',
            'id="conflict-dismiss"',
            'id="status-dot"',
            'id="waveform-canvas"',
            'id="app-container"',
            'id="control-bar"'
        ]
        
        for element in critical_elements:
            self.assertIn(element, html_content,
                         f"Missing critical UI element: {element}")

    def test_python_backend_paths(self):
        """Test that Python backend can find all required modules after reorganization."""
        
        # Check main.py exists and has correct imports
        main_file = self.project_root / "main.py"
        self.assertTrue(main_file.exists(), "main.py not found")
        
        with open(main_file, 'r') as f:
            main_content = f.read()
        
        expected_imports = [
            "from src.config import config",
            "from src.utils.utils import log_text",
            "from src.audio.audio_handler import AudioHandler"
        ]
        
        for expected_import in expected_imports:
            self.assertIn(expected_import, main_content,
                         f"Missing import in main.py: {expected_import}")

    def test_no_missing_files_references(self):
        """Test that there are no references to files in old locations."""
        
        # Check electron_windows.js for correct file paths
        electron_windows_file = self.project_root / "electron_windows.js"
        if electron_windows_file.exists():
            with open(electron_windows_file, 'r') as f:
                content = f.read()
            
            # Should reference frontend/main/, not root
            self.assertIn("frontend/main/index.html", content,
                         "Missing correct path to index.html")
            self.assertIn("frontend/main/preload.js", content,
                         "Missing correct path to preload.js")

    def test_import_syntax_validity(self):
        """Test that all import statements use valid ES6 syntax."""
        
        js_files = list(self.frontend_shared_dir.glob("*.js"))
        js_files.append(self.frontend_main_dir / "renderer.js")
        
        for js_file in js_files:
            with open(js_file, 'r') as f:
                content = f.read()
            
            # Find all import statements
            import_pattern = r"import\s+.*?from\s+['\"](.+?)['\"]"
            imports = re.findall(import_pattern, content, re.MULTILINE)
            
            for import_path in imports:
                # Validate import path format
                self.assertTrue(
                    import_path.startswith('./') or import_path.startswith('../'),
                    f"Invalid import path format in {js_file}: {import_path}"
                )
                
                # Validate that imported files exist
                if import_path.startswith('./'):
                    full_path = js_file.parent / import_path[2:]
                elif import_path.startswith('../'):
                    full_path = js_file.parent / import_path
                
                self.assertTrue(full_path.exists(),
                               f"Import references non-existent file: {import_path} in {js_file}")


def run_integration_tests():
    """Run the integration test suite."""
    unittest.main()


if __name__ == '__main__':
    run_integration_tests() 