#!/usr/bin/env python3
"""
Configuration Validation Tests

These tests validate application configuration at startup to prevent runtime failures.
Config errors often cause mysterious failures that are hard to debug.

Prevents issues like:
- Missing model files causing crashes during operation
- Invalid audio parameters causing stream failures
- Malformed configuration values causing unpredictable behavior
- Environment-specific issues not caught during development
"""

import unittest
import os
import tempfile
import shutil
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock


class ConfigValidator:
    """Configuration validator for CitrixTranscriber"""

    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """Validate all configuration sections"""
        self.errors.clear()
        self.warnings.clear()

        self.validate_audio_config()
        self.validate_model_paths()
        self.validate_llm_config()
        self.validate_hotkey_config()
        self.validate_file_paths()
        self.validate_numeric_ranges()

        return len(self.errors) == 0

    def validate_audio_config(self):
        """Validate audio parameters are reasonable"""

        # Sample rate validation
        sample_rate = self.config.get("SAMPLE_RATE", 16000)
        valid_sample_rates = [8000, 11025, 16000, 22050, 44100, 48000]
        if sample_rate not in valid_sample_rates:
            self.errors.append(
                f"Invalid SAMPLE_RATE: {sample_rate}. Must be one of {valid_sample_rates}"
            )

        # VAD aggressiveness validation
        vad_aggressiveness = self.config.get("VAD_AGGRESSIVENESS", 1)
        if not isinstance(vad_aggressiveness, int) or vad_aggressiveness not in [
            0,
            1,
            2,
            3,
        ]:
            self.errors.append(
                f"Invalid VAD_AGGRESSIVENESS: {vad_aggressiveness}. Must be 0, 1, 2, or 3"
            )

        # Frame duration validation
        frame_duration = self.config.get("FRAME_DURATION_MS", 20)
        if (
            not isinstance(frame_duration, int)
            or frame_duration < 10
            or frame_duration > 100
        ):
            self.errors.append(
                f"Invalid FRAME_DURATION_MS: {frame_duration}. Must be between 10-100ms"
            )

        # Channels validation
        channels = self.config.get("CHANNELS", 1)
        if not isinstance(channels, int) or channels not in [1, 2]:
            self.errors.append(
                f"Invalid CHANNELS: {channels}. Must be 1 (mono) or 2 (stereo)"
            )

        # Buffer size validation
        ring_buffer_duration = self.config.get("RING_BUFFER_DURATION_MS", 500)
        if not isinstance(ring_buffer_duration, int) or ring_buffer_duration < 100:
            self.errors.append(
                f"Invalid RING_BUFFER_DURATION_MS: {ring_buffer_duration}. Must be at least 100ms"
            )

        # Silence detection
        silence_limit = self.config.get("SILENCE_LIMIT", 0.8)
        if (
            not isinstance(silence_limit, (int, float))
            or silence_limit < 0.1
            or silence_limit > 5.0
        ):
            self.errors.append(
                f"Invalid SILENCE_LIMIT: {silence_limit}. Must be between 0.1-5.0 seconds"
            )

    def validate_model_paths(self):
        """Validate all model paths exist and are accessible"""

        # Vosk model path
        vosk_path = self.config.get("VOSK_MODEL_PATH")
        if not vosk_path:
            self.errors.append("VOSK_MODEL_PATH not specified")
        elif not os.path.exists(vosk_path):
            self.errors.append(f"VOSK_MODEL_PATH does not exist: {vosk_path}")
        elif not os.path.isdir(vosk_path):
            self.errors.append(f"VOSK_MODEL_PATH is not a directory: {vosk_path}")

        # LLM models
        available_llms = self.config.get("AVAILABLE_LLMS", {})
        if not isinstance(available_llms, dict):
            self.errors.append("AVAILABLE_LLMS must be a dictionary")
        else:
            for model_name, model_path in available_llms.items():
                if not isinstance(model_name, str):
                    self.errors.append(f"LLM model name must be string: {model_name}")
                    continue

                if not isinstance(model_path, str):
                    self.errors.append(
                        f"LLM model path must be string for {model_name}: {model_path}"
                    )
                    continue

                if not os.path.exists(model_path):
                    self.errors.append(
                        f"LLM model path does not exist for {model_name}: {model_path}"
                    )
                elif not os.path.isdir(model_path):
                    self.errors.append(
                        f"LLM model path is not a directory for {model_name}: {model_path}"
                    )

        # Default LLM validation
        default_llm = self.config.get("DEFAULT_LLM")
        if default_llm and default_llm not in available_llms:
            self.errors.append(
                f"DEFAULT_LLM '{default_llm}' not found in AVAILABLE_LLMS"
            )

    def validate_llm_config(self):
        """Validate LLM configuration parameters"""

        # Max tokens validation
        max_tokens = self.config.get("MAX_TOKENS", 2048)
        if not isinstance(max_tokens, int) or max_tokens < 100 or max_tokens > 32000:
            self.errors.append(
                f"Invalid MAX_TOKENS: {max_tokens}. Must be between 100-32000"
            )

        # Temperature validation
        temperature = self.config.get("TEMPERATURE", 0.7)
        if (
            not isinstance(temperature, (int, float))
            or temperature < 0.0
            or temperature > 2.0
        ):
            self.errors.append(
                f"Invalid TEMPERATURE: {temperature}. Must be between 0.0-2.0"
            )

        # Top-p validation
        top_p = self.config.get("TOP_P", 0.9)
        if not isinstance(top_p, (int, float)) or top_p < 0.0 or top_p > 1.0:
            self.errors.append(f"Invalid TOP_P: {top_p}. Must be between 0.0-1.0")

        # Tokenizers parallelism
        tokenizers_parallelism = self.config.get("TOKENIZERS_PARALLELISM", "false")
        if tokenizers_parallelism not in ["true", "false"]:
            self.warnings.append(
                f"TOKENIZERS_PARALLELISM should be 'true' or 'false', got: {tokenizers_parallelism}"
            )

    def validate_hotkey_config(self):
        """Validate hotkey configuration"""

        # Wake words validation
        wake_words = self.config.get("WAKE_WORDS", {})
        if not isinstance(wake_words, dict):
            self.errors.append("WAKE_WORDS must be a dictionary")
        else:
            required_commands = ["START_DICTATE", "START_PROOFREAD", "START_LETTER"]
            for cmd in required_commands:
                cmd_key = f"COMMAND_{cmd}"
                if cmd_key not in self.config:
                    self.errors.append(f"Missing command configuration: {cmd_key}")

        # Hotkey validation
        hotkeys = self.config.get("HOTKEYS", {})
        if not isinstance(hotkeys, dict):
            self.errors.append("HOTKEYS must be a dictionary")
        else:
            for hotkey_name, hotkey_combo in hotkeys.items():
                if not isinstance(hotkey_combo, str):
                    self.errors.append(
                        f"Hotkey combo must be string for {hotkey_name}: {hotkey_combo}"
                    )
                elif not hotkey_combo.strip():
                    self.errors.append(
                        f"Hotkey combo cannot be empty for {hotkey_name}"
                    )

    def validate_file_paths(self):
        """Validate file paths and directories"""

        # Log file directory
        log_dir = self.config.get("LOG_DIRECTORY", ".")
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                self.warnings.append(f"Created log directory: {log_dir}")
            except Exception as e:
                self.errors.append(f"Cannot create log directory {log_dir}: {e}")
        elif not os.path.isdir(log_dir):
            self.errors.append(f"Log directory is not a directory: {log_dir}")

        # Cache directory
        cache_dir = self.config.get("CACHE_DIRECTORY", "./cache")
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                self.warnings.append(f"Created cache directory: {cache_dir}")
            except Exception as e:
                self.errors.append(f"Cannot create cache directory {cache_dir}: {e}")

    def validate_numeric_ranges(self):
        """Validate numeric configuration values are in reasonable ranges"""

        numeric_configs = {
            "MEMORY_LIMIT_MB": (100, 8000, "Memory limit"),
            "CHUNK_SIZE": (1024, 65536, "Chunk size"),
            "TIMEOUT_SECONDS": (5, 300, "Timeout"),
            "MAX_RETRIES": (0, 10, "Max retries"),
            "BUFFER_SIZE": (1024, 1024 * 1024, "Buffer size"),
        }

        for config_key, (min_val, max_val, description) in numeric_configs.items():
            value = self.config.get(config_key)
            if value is not None:
                if not isinstance(value, (int, float)):
                    self.errors.append(
                        f"{description} must be numeric: {config_key}={value}"
                    )
                elif value < min_val or value > max_val:
                    self.errors.append(
                        f"{description} out of range: {config_key}={value} (should be {min_val}-{max_val})"
                    )

    def get_validation_report(self) -> str:
        """Get a formatted validation report"""
        report = []

        if self.errors:
            report.append("CONFIGURATION ERRORS:")
            for error in self.errors:
                report.append(f"  ❌ {error}")
            report.append("")

        if self.warnings:
            report.append("CONFIGURATION WARNINGS:")
            for warning in self.warnings:
                report.append(f"  ⚠️  {warning}")
            report.append("")

        if not self.errors and not self.warnings:
            report.append("✅ Configuration validation passed!")

        return "\n".join(report)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation"""

    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.vosk_model_dir = os.path.join(self.temp_dir, "vosk-model")
        self.llm_model_dir = os.path.join(self.temp_dir, "llm-model")

        os.makedirs(self.vosk_model_dir)
        os.makedirs(self.llm_model_dir)

        # Base valid configuration
        self.valid_config = {
            "SAMPLE_RATE": 16000,
            "VAD_AGGRESSIVENESS": 1,
            "FRAME_DURATION_MS": 20,
            "CHANNELS": 1,
            "RING_BUFFER_DURATION_MS": 500,
            "SILENCE_LIMIT": 0.8,
            "VOSK_MODEL_PATH": self.vosk_model_dir,
            "AVAILABLE_LLMS": {"test_model": self.llm_model_dir},
            "DEFAULT_LLM": "test_model",
            "MAX_TOKENS": 2048,
            "TEMPERATURE": 0.7,
            "TOP_P": 0.9,
            "TOKENIZERS_PARALLELISM": "false",
            "WAKE_WORDS": {"test": "test"},
            "COMMAND_START_DICTATE": "dictate",
            "COMMAND_START_PROOFREAD": "proofread",
            "COMMAND_START_LETTER": "letter",
            "HOTKEYS": {"test_key": "ctrl+shift+t"},
            "LOG_DIRECTORY": os.path.join(self.temp_dir, "logs"),
            "CACHE_DIRECTORY": os.path.join(self.temp_dir, "cache"),
        }

    def tearDown(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_configuration(self):
        """Test that valid configuration passes validation"""

        validator = ConfigValidator(self.valid_config)
        is_valid = validator.validate_all()

        self.assertTrue(
            is_valid,
            f"Valid config failed validation: {validator.get_validation_report()}",
        )
        self.assertEqual(len(validator.errors), 0)

    def test_invalid_audio_parameters(self):
        """Test detection of invalid audio parameters"""

        invalid_configs = [
            # Invalid sample rate
            {"SAMPLE_RATE": 32000},
            # Invalid VAD aggressiveness
            {"VAD_AGGRESSIVENESS": 5},
            {"VAD_AGGRESSIVENESS": "high"},
            # Invalid frame duration
            {"FRAME_DURATION_MS": 5},
            {"FRAME_DURATION_MS": 200},
            # Invalid channels
            {"CHANNELS": 3},
            {"CHANNELS": "stereo"},
            # Invalid silence limit
            {"SILENCE_LIMIT": -1},
            {"SILENCE_LIMIT": 10},
        ]

        for invalid_update in invalid_configs:
            with self.subTest(invalid_config=invalid_update):
                config = self.valid_config.copy()
                config.update(invalid_update)

                validator = ConfigValidator(config)
                is_valid = validator.validate_all()

                self.assertFalse(
                    is_valid, f"Invalid config passed validation: {invalid_update}"
                )
                self.assertGreater(len(validator.errors), 0)

    def test_missing_model_paths(self):
        """Test detection of missing model paths"""

        # Missing Vosk model
        config = self.valid_config.copy()
        config["VOSK_MODEL_PATH"] = "/nonexistent/path"

        validator = ConfigValidator(config)
        is_valid = validator.validate_all()

        self.assertFalse(is_valid)
        self.assertTrue(
            any("VOSK_MODEL_PATH does not exist" in error for error in validator.errors)
        )

        # Missing LLM model
        config = self.valid_config.copy()
        config["AVAILABLE_LLMS"] = {"test_model": "/nonexistent/llm/path"}

        validator = ConfigValidator(config)
        is_valid = validator.validate_all()

        self.assertFalse(is_valid)
        self.assertTrue(
            any("LLM model path does not exist" in error for error in validator.errors)
        )

    def test_invalid_llm_parameters(self):
        """Test detection of invalid LLM parameters"""

        invalid_configs = [
            # Invalid max tokens
            {"MAX_TOKENS": 50},
            {"MAX_TOKENS": 50000},
            {"MAX_TOKENS": "many"},
            # Invalid temperature
            {"TEMPERATURE": -0.5},
            {"TEMPERATURE": 3.0},
            {"TEMPERATURE": "hot"},
            # Invalid top-p
            {"TOP_P": -0.1},
            {"TOP_P": 1.5},
            {"TOP_P": "high"},
        ]

        for invalid_update in invalid_configs:
            with self.subTest(invalid_config=invalid_update):
                config = self.valid_config.copy()
                config.update(invalid_update)

                validator = ConfigValidator(config)
                is_valid = validator.validate_all()

                self.assertFalse(
                    is_valid, f"Invalid LLM config passed: {invalid_update}"
                )
                self.assertGreater(len(validator.errors), 0)

    def test_missing_required_commands(self):
        """Test detection of missing required command configurations"""

        config = self.valid_config.copy()
        del config["COMMAND_START_DICTATE"]

        validator = ConfigValidator(config)
        is_valid = validator.validate_all()

        self.assertFalse(is_valid)
        self.assertTrue(
            any("COMMAND_START_DICTATE" in error for error in validator.errors)
        )

    def test_invalid_hotkey_configuration(self):
        """Test detection of invalid hotkey configuration"""

        invalid_configs = [
            # Non-dict wake words
            {"WAKE_WORDS": "not_a_dict"},
            # Non-dict hotkeys
            {"HOTKEYS": "not_a_dict"},
            # Empty hotkey combo
            {"HOTKEYS": {"test_key": ""}},
            # Non-string hotkey combo
            {"HOTKEYS": {"test_key": 123}},
        ]

        for invalid_update in invalid_configs:
            with self.subTest(invalid_config=invalid_update):
                config = self.valid_config.copy()
                config.update(invalid_update)

                validator = ConfigValidator(config)
                is_valid = validator.validate_all()

                self.assertFalse(
                    is_valid, f"Invalid hotkey config passed: {invalid_update}"
                )
                self.assertGreater(len(validator.errors), 0)

    def test_directory_creation(self):
        """Test automatic directory creation for missing directories"""

        config = self.valid_config.copy()
        new_log_dir = os.path.join(self.temp_dir, "new_logs")
        new_cache_dir = os.path.join(self.temp_dir, "new_cache")

        config["LOG_DIRECTORY"] = new_log_dir
        config["CACHE_DIRECTORY"] = new_cache_dir

        # Ensure directories don't exist initially
        self.assertFalse(os.path.exists(new_log_dir))
        self.assertFalse(os.path.exists(new_cache_dir))

        validator = ConfigValidator(config)
        is_valid = validator.validate_all()

        # Should be valid and directories should be created
        self.assertTrue(is_valid)
        self.assertTrue(os.path.exists(new_log_dir))
        self.assertTrue(os.path.exists(new_cache_dir))

        # Should have warnings about directory creation
        self.assertGreater(len(validator.warnings), 0)
        self.assertTrue(
            any("Created log directory" in warning for warning in validator.warnings)
        )
        self.assertTrue(
            any("Created cache directory" in warning for warning in validator.warnings)
        )

    def test_numeric_range_validation(self):
        """Test validation of numeric configuration ranges"""

        invalid_configs = [
            # Memory limit out of range
            {"MEMORY_LIMIT_MB": 50},  # Too low
            {"MEMORY_LIMIT_MB": 10000},  # Too high
            # Invalid chunk size
            {"CHUNK_SIZE": 100},  # Too low
            {"CHUNK_SIZE": 2000000},  # Too high
            # Invalid timeout
            {"TIMEOUT_SECONDS": 1},  # Too low
            {"TIMEOUT_SECONDS": 500},  # Too high
            # Non-numeric values
            {"MAX_RETRIES": "many"},
            {"BUFFER_SIZE": "large"},
        ]

        for invalid_update in invalid_configs:
            with self.subTest(invalid_config=invalid_update):
                config = self.valid_config.copy()
                config.update(invalid_update)

                validator = ConfigValidator(config)
                is_valid = validator.validate_all()

                self.assertFalse(
                    is_valid, f"Invalid numeric config passed: {invalid_update}"
                )
                self.assertGreater(len(validator.errors), 0)

    def test_default_llm_validation(self):
        """Test validation of default LLM against available models"""

        config = self.valid_config.copy()
        config["DEFAULT_LLM"] = "nonexistent_model"

        validator = ConfigValidator(config)
        is_valid = validator.validate_all()

        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "DEFAULT_LLM" in error and "not found in AVAILABLE_LLMS" in error
                for error in validator.errors
            )
        )

    def test_validation_report_formatting(self):
        """Test that validation report is properly formatted"""

        # Create config with both errors and warnings
        config = self.valid_config.copy()
        config["SAMPLE_RATE"] = 32000  # Invalid - will cause error
        config["TOKENIZERS_PARALLELISM"] = "maybe"  # Invalid - will cause warning

        validator = ConfigValidator(config)
        validator.validate_all()

        report = validator.get_validation_report()

        # Should contain both errors and warnings sections
        self.assertIn("CONFIGURATION ERRORS:", report)
        self.assertIn("❌", report)

        # Check for specific error content
        self.assertIn("SAMPLE_RATE", report)
        self.assertIn("32000", report)

    def test_empty_configuration(self):
        """Test validation of empty configuration"""

        validator = ConfigValidator({})
        is_valid = validator.validate_all()

        # Should fail with many errors
        self.assertFalse(is_valid)
        self.assertGreaterEqual(
            len(validator.errors), 3
        )  # Should have multiple errors (adjusted expectation)

        # Should include errors about missing required configurations
        error_text = " ".join(validator.errors)
        self.assertIn("VOSK_MODEL_PATH", error_text)
        self.assertIn("COMMAND_START_DICTATE", error_text)


class TestConfigValidationIntegration(unittest.TestCase):
    """Integration tests for configuration validation"""

    def test_config_validation_in_startup_sequence(self):
        """Test configuration validation as part of application startup"""

        # Mock the actual config module
        mock_config = {
            "SAMPLE_RATE": 16000,
            "VAD_AGGRESSIVENESS": 1,
            "VOSK_MODEL_PATH": "/tmp/test_vosk",
            "AVAILABLE_LLMS": {},
            "WAKE_WORDS": {},
            "HOTKEYS": {},
        }

        # This would be called during app initialization
        validator = ConfigValidator(mock_config)
        is_valid = validator.validate_all()

        # In real app, this would prevent startup if invalid
        if not is_valid:
            errors = validator.errors
            # Would raise exception or exit with error message
            self.assertGreater(len(errors), 0)

    def test_runtime_config_revalidation(self):
        """Test revalidation when configuration changes at runtime"""

        # Start with valid config
        temp_dir = tempfile.mkdtemp()
        try:
            config = {
                "SAMPLE_RATE": 16000,
                "VAD_AGGRESSIVENESS": 1,
                "FRAME_DURATION_MS": 20,
                "CHANNELS": 1,
                "RING_BUFFER_DURATION_MS": 500,
                "SILENCE_LIMIT": 0.8,
                "TEMPERATURE": 0.7,
                "MAX_TOKENS": 2048,
                "TOP_P": 0.9,
                "VOSK_MODEL_PATH": temp_dir,
                "AVAILABLE_LLMS": {"test": temp_dir},
                "WAKE_WORDS": {},
                "COMMAND_START_DICTATE": "dictate",
                "COMMAND_START_PROOFREAD": "proofread",
                "COMMAND_START_LETTER": "letter",
                "HOTKEYS": {},
            }

            validator = ConfigValidator(config)
            self.assertTrue(validator.validate_all())

            # Simulate runtime config change
            config["TEMPERATURE"] = 5.0  # Invalid value

            validator = ConfigValidator(config)
            self.assertFalse(validator.validate_all())

            # Should detect the invalid change
            self.assertTrue(any("TEMPERATURE" in error for error in validator.errors))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
