#!/usr/bin/env python3
"""
Integration tests for stop/cancel functionality.
Tests the complete flow from renderer controls to Python backend.
"""

import unittest
import json
import subprocess
import time
import os
import signal
import sys
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch, Mock


class TestStopCancelIntegration(unittest.TestCase):
    """Integration tests for stop/cancel button functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_timeout = 15
        self.test_commands = []
        
    def tearDown(self):
        """Clean up after tests."""
        # Clean up any test processes
        pass
        
    def test_stop_dictation_command_flow(self):
        """Test complete flow for stop dictation command."""
        # Test that the command flows correctly:
        # Renderer -> IPC -> Main Process -> Python Backend
        
        # 1. Verify renderer_controls.js has stop button handler
        with open('frontend/shared/renderer_controls.js', 'r') as f:
            controls_content = f.read()
        self.assertIn('window.electronAPI.stopDictation()', controls_content)
        
        # 2. Verify preload.js exposes stopDictation API
        with open('frontend/main/preload.js', 'r') as f:
            preload_content = f.read()
        self.assertIn('stopDictation: () => ipcRenderer.send(\'stop-dictation\')', preload_content)
        
        # 3. Verify electron_ipc.js handles stop-dictation IPC
        with open('electron/electron_ipc.js', 'r') as f:
            ipc_content = f.read()
        self.assertIn('ipcMain.on(\'stop-dictation\'', ipc_content)
        self.assertIn('STOP_DICTATION', ipc_content)
        
        # 4. Verify main.py handles STOP_DICTATION command
        with open('main.py', 'r') as f:
            main_content = f.read()
        self.assertIn('elif command_line == "STOP_DICTATION":', main_content)
        self.assertIn('app._trigger_stop_dictation()', main_content)
        
    def test_abort_dictation_command_flow(self):
        """Test complete flow for abort dictation command."""
        # Test that the command flows correctly:
        # Renderer -> IPC -> Main Process -> Python Backend
        
        # 1. Verify renderer_controls.js has cancel button handler
        with open('frontend/shared/renderer_controls.js', 'r') as f:
            controls_content = f.read()
        self.assertIn('window.electronAPI.abortDictation()', controls_content)
        
        # 2. Verify preload.js exposes abortDictation API
        with open('frontend/main/preload.js', 'r') as f:
            preload_content = f.read()
        self.assertIn('abortDictation: () => ipcRenderer.send(\'abort-dictation\')', preload_content)
        
        # 3. Verify electron_ipc.js handles abort-dictation IPC
        with open('electron/electron_ipc.js', 'r') as f:
            ipc_content = f.read()
        self.assertIn('ipcMain.on(\'abort-dictation\'', ipc_content)
        self.assertIn('ABORT_DICTATION', ipc_content)
        
        # 4. Verify main.py handles ABORT_DICTATION command
        with open('main.py', 'r') as f:
            main_content = f.read()
        self.assertIn('elif command_line == "ABORT_DICTATION":', main_content)
        self.assertIn('app._trigger_abort_dictation()', main_content)
        
    def test_keyboard_shortcuts_integration(self):
        """Test keyboard shortcuts are properly integrated."""
        # Verify Space and Escape keys trigger the correct actions
        with open('frontend/shared/renderer_controls.js', 'r') as f:
            controls_content = f.read()
            
        # Check Space key handler
        self.assertIn('event.code === \'Space\'', controls_content)
        self.assertIn('window.electronAPI.stopDictation()', controls_content)
        
        # Check Escape key handler
        self.assertIn('event.code === \'Escape\'', controls_content)
        self.assertIn('window.electronAPI.abortDictation()', controls_content)
        
    def test_python_backend_methods_exist(self):
        """Test that required Python backend methods exist and are callable."""
        # Import the modules to verify they exist and are properly structured
        sys.path.append('.')
        
        try:
            import main
            # Verify the Application class has required methods
            app_methods = dir(main.Application)
            self.assertIn('_trigger_stop_dictation', app_methods)
            self.assertIn('_trigger_abort_dictation', app_methods)
            
            # Verify audio_handler has abort_dictation method
            import src.audio.audio_handler as audio_handler
            handler_methods = dir(audio_handler.AudioHandler)
            self.assertIn('abort_dictation', handler_methods)
            
        except ImportError as e:
            self.fail(f"Failed to import required modules: {e}")
            
    def test_config_constants_integration(self):
        """Test that config constants are properly integrated."""
        sys.path.append('.')
        
        try:
            from src.config import config
            # Verify required constants exist
            self.assertTrue(hasattr(config, 'COMMAND_STOP_DICTATE'))
            self.assertTrue(hasattr(config, 'COMMAND_ABORT_DICTATE'))
            
            # Verify constants have correct values
            self.assertEqual(config.COMMAND_STOP_DICTATE, 'stop_dictate')
            self.assertEqual(config.COMMAND_ABORT_DICTATE, 'abort_dictate')
            
        except ImportError as e:
            self.fail(f"Failed to import config module: {e}")
            
    def test_html_button_integration(self):
        """Test that HTML buttons are properly integrated with JavaScript."""
        # Read HTML to verify button structure
        with open('frontend/main/index.html', 'r') as f:
            html_content = f.read()
            
        # Verify buttons exist with correct IDs
        self.assertIn('id="stop-button"', html_content)
        self.assertIn('id="cancel-button"', html_content)
        
        # Verify keyboard shortcut labels match implementation
        self.assertIn('<kbd>Space</kbd>', html_content)
        self.assertIn('<kbd>Esc</kbd>', html_content)
        
        # Read renderer_ui.js to verify button exports
        with open('frontend/shared/renderer_ui.js', 'r') as f:
            ui_content = f.read()
            
        self.assertIn('stopButton = document.getElementById(\'stop-button\')', ui_content)
        self.assertIn('cancelButton = document.getElementById(\'cancel-button\')', ui_content)
        
    def test_module_initialization_order(self):
        """Test that modules are initialized in the correct order."""
        # Verify renderer.js initializes controls after DOM is ready
        with open('frontend/main/renderer.js', 'r') as f:
            renderer_content = f.read()
            
        # Controls should be initialized after DOM is loaded
        dom_ready_section = renderer_content[renderer_content.find('DOMContentLoaded'):]
        self.assertIn('initializeControls()', dom_ready_section)
        
    def test_error_handling_integration(self):
        """Test that error handling works correctly throughout the chain."""
        # Verify error handling in renderer_controls.js
        with open('frontend/shared/renderer_controls.js', 'r') as f:
            controls_content = f.read()
            
        # Should check for electronAPI availability
        self.assertIn('window.electronAPI && window.electronAPI.stopDictation', controls_content)
        self.assertIn('window.electronAPI && window.electronAPI.abortDictation', controls_content)
        
        # Should log errors when API is not available
        self.assertIn('electronAPI.stopDictation not available', controls_content)
        self.assertIn('electronAPI.abortDictation not available', controls_content)


class TestButtonStateIntegration(unittest.TestCase):
    """Test button state management integration."""
    
    def test_button_state_updates(self):
        """Test that button states are updated correctly."""
        # Verify renderer_state.js manages button states
        with open('frontend/shared/renderer_state.js', 'r') as f:
            state_content = f.read()
            
        # Should import button elements
        self.assertIn('stopButton, cancelButton', state_content)
        
        # Should disable/enable buttons based on state
        self.assertIn('stopButton.disabled', state_content)
        self.assertIn('cancelButton.disabled', state_content)
        
    def test_dictation_state_button_behavior(self):
        """Test button behavior during different dictation states."""
        with open('frontend/shared/renderer_state.js', 'r') as f:
            state_content = f.read()
            
        # During dictation, buttons should be enabled
        dictation_section = state_content[state_content.find('case \'dictation\''):]
        next_case = dictation_section.find('case ')
        if next_case > 0:
            dictation_section = dictation_section[:next_case]
            
        self.assertIn('stopButton.disabled = false', dictation_section)
        self.assertIn('cancelButton.disabled = false', dictation_section)


if __name__ == '__main__':
    print("Running stop/cancel integration tests...")
    unittest.main(verbosity=2) 