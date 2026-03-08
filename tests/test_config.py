"""Tests for configuration loading."""

import unittest

from jukebox.config import ConfigError, from_env


class FromEnvTests(unittest.TestCase):
    def test_defaults_are_used_when_environment_is_empty(self) -> None:
        settings = from_env({})

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.log_format, "console")

    def test_environment_overrides_are_normalized(self) -> None:
        settings = from_env(
            {
                "JUKEBOX_ENV": "local",
                "JUKEBOX_LOG_LEVEL": "debug",
                "JUKEBOX_LOG_FORMAT": "JSON",
            }
        )

        self.assertEqual(settings.environment, "local")
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.log_format, "json")

    def test_invalid_log_level_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_LOG_LEVEL": "verbose"})

    def test_invalid_log_format_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_LOG_FORMAT": "text"})
