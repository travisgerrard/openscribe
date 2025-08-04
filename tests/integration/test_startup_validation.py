#!/usr/bin/env python3
"""
Startup Validation Integration Tests

Tests to catch the issues we encountered during refactoring:
1. Conda environment validation (whisper-env vs whisper_env)
2. Python backend startup failures  
3. Missing dependencies (pyaudio, etc.)
4. Configuration file loading
5. Model file accessibility

These tests should run before any other tests to catch environment issues early.
"""

import unittest
import subprocess
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json


class TestStartupValidation(unittest.TestCase):
    """Test suite to validate application startup requirements."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.main_py = self.project_root / "main.py"
        self.config_dir = self.project_root / "src" / "config"
        
    def test_conda_environment_availability(self):
        """Test that the correct conda environment exists and is accessible."""
        try:
            # Check if conda is available
            result = subprocess.run(['conda', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, "Conda not available")
            
            # Check if whisper-env exists (not whisper_env)
            result = subprocess.run(['conda', 'env', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, "Failed to list conda environments")
            
            env_list = result.stdout
            self.assertIn('whisper-env', env_list, 
                         "whisper-env conda environment not found. This was the issue that caused startup failures.")
            
            # Ensure whisper_env (underscore) doesn't exist to prevent confusion
            if 'whisper_env' in env_list:
                self.fail("Found whisper_env (underscore) environment which conflicts with whisper-env (hyphen). Remove the underscore version.")
                
        except subprocess.TimeoutExpired:
            self.fail("Conda command timed out - conda may not be properly installed")
        except FileNotFoundError:
            self.fail("Conda not found in PATH")

    def test_python_dependencies_in_conda_env(self):
        """Test that required Python packages are available in the whisper-env environment."""
        required_packages = [
            'pyaudio',      # The missing package that caused our startup failure
            'vosk',         # Speech recognition
            'whisper',      # OpenAI Whisper
            'numpy',        # Audio processing
            'scipy',        # Signal processing
            'webrtcvad',    # Voice activity detection
            'pynput'        # Hotkey functionality
        ]
        
        for package in required_packages:
            try:
                # Test import in the conda environment
                cmd = ['conda', 'run', '-n', 'whisper-env', 'python', '-c', f'import {package}']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode != 0:
                    self.fail(f"Package '{package}' not available in whisper-env environment. "
                             f"Error: {result.stderr}. This type of missing dependency caused our startup failure.")
                             
            except subprocess.TimeoutExpired:
                self.fail(f"Import test for {package} timed out")
            except FileNotFoundError:
                self.fail("Conda not found - cannot test package availability")

    def test_main_py_syntax_validation(self):
        """Test that main.py can be parsed without syntax errors."""
        try:
            # Test syntax by compiling without executing
            with open(self.main_py, 'r') as f:
                source = f.read()
            
            compile(source, str(self.main_py), 'exec')
            
        except SyntaxError as e:
            self.fail(f"Syntax error in main.py: {e}")
        except FileNotFoundError:
            self.fail(f"main.py not found at {self.main_py}")

    def test_config_import_accessibility(self):
        """Test that config module can be imported without errors."""
        try:
            # Test config import in conda environment
            cmd = ['conda', 'run', '-n', 'whisper-env', 'python', '-c', 
                   'import sys; sys.path.insert(0, "."); from src.config import config']
            
            result = subprocess.run(cmd, cwd=str(self.project_root),
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                self.fail(f"Config import failed: {result.stderr}. "
                         f"This indicates missing dependencies or import path issues.")
                         
        except subprocess.TimeoutExpired:
            self.fail("Config import test timed out")

    def test_model_files_exist(self):
        """Test that required model files exist and are accessible."""
        # Look for Vosk model directory (may vary by version)
        vosk_pattern = "vosk-model-small-en-us-*"
        vosk_dirs = list(self.project_root.glob(vosk_pattern))
        
        if not vosk_dirs:
            self.skipTest(f"No Vosk model directory found matching pattern: {vosk_pattern}")
            
        vosk_model_path = vosk_dirs[0]  # Use first match
        self.assertTrue(vosk_model_path.exists(), 
                       f"Vosk model not found at {vosk_model_path}")
        self.assertTrue(vosk_model_path.is_dir(), 
                       f"Vosk model path is not a directory: {vosk_model_path}")
        
        # Check for key Vosk model files
        required_vosk_files = ["final.mdl", "graph", "tree"]
        missing_files = []
        for file_name in required_vosk_files:
            file_path = vosk_model_path / file_name
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        if missing_files:
            self.skipTest(f"Vosk model files missing (model may be incomplete): {missing_files}")

        # OpenWakeWord model directory (optional)
        oww_model_path = self.project_root / "openwakeword"
        if oww_model_path.exists():
            self.assertTrue(oww_model_path.is_dir(), 
                           f"OpenWakeWord path is not a directory: {oww_model_path}")

    def test_backend_startup_sequence(self):
        """Test that Python backend can start without immediate crashes."""
        try:
            # Start backend with timeout to test initialization
            cmd = ['conda', 'run', '-n', 'whisper-env', 'python', 'main.py']
            
            process = subprocess.Popen(cmd, cwd=str(self.project_root),
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            # Let it run for a few seconds to get past initialization
            time.sleep(5)
            
            # Check if process is still running (good sign)
            poll_result = process.poll()
            
            if poll_result is not None:
                # Process has terminated, check why
                stdout, stderr = process.communicate(timeout=5)
                self.fail(f"Backend process terminated unexpectedly with code {poll_result}. "
                         f"STDOUT: {stdout[:500]}... STDERR: {stderr[:500]}...")
            
            # Terminate the test process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
        except subprocess.TimeoutExpired:
            self.fail("Backend startup test timed out")
        except FileNotFoundError:
            self.fail("Failed to start backend - conda or python not found")

    def test_configuration_file_loading(self):
        """Test that configuration files can be loaded successfully."""
        config_files = [
            self.project_root / "user_settings.json"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    self.fail(f"Invalid JSON in {config_file}: {e}")

    def test_directory_structure_integrity(self):
        """Test that the reorganized directory structure is intact."""
        required_dirs = [
            self.project_root / "src",
            self.project_root / "src" / "config", 
            self.project_root / "src" / "audio",
            self.project_root / "frontend",
            self.project_root / "frontend" / "main",
            self.project_root / "frontend" / "shared",
            self.project_root / "frontend" / "styles"
        ]
        
        for dir_path in required_dirs:
            self.assertTrue(dir_path.exists(), 
                           f"Required directory missing: {dir_path}")
            self.assertTrue(dir_path.is_dir(), 
                           f"Path exists but is not a directory: {dir_path}")
        
        # Optional directories (may not exist in all configurations)
        optional_dirs = [
            self.project_root / "src" / "speech",
                ]
        
        for dir_path in optional_dirs:
            if not dir_path.exists():
                print(f"INFO: Optional directory not found: {dir_path}")
            elif not dir_path.is_dir():
                self.fail(f"Optional path exists but is not a directory: {dir_path}")

    def test_electron_file_accessibility(self):
        """Test that Electron files are accessible."""
        electron_files = [
            self.project_root / "main.js",
            self.project_root / "electron" / "electron_python.js",
            self.project_root / "electron" / "electron_tray.js",
            self.project_root / "package.json"
        ]

        for file_path in electron_files:
            self.assertTrue(file_path.exists(),
                           f"Electron file missing: {file_path}")

    def test_no_conflicting_environments(self):
        """Test that there are no conflicting conda environments."""
        try:
            result = subprocess.run(['conda', 'env', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, "Failed to list conda environments")
            
            env_list = result.stdout
            
            # Check for potential conflicts
            conflicts = []
            if 'whisper_env' in env_list and 'whisper-env' in env_list:
                conflicts.append("Both whisper_env and whisper-env exist")
            
            if conflicts:
                self.fail(f"Environment conflicts detected: {', '.join(conflicts)}. "
                         f"These can cause confusion about which environment to use.")
                         
        except subprocess.TimeoutExpired:
            self.fail("Environment conflict check timed out")


if __name__ == '__main__':
    unittest.main() 