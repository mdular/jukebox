"""Tests for configuration loading."""

import unittest

from jukebox.config import ConfigError, from_env


class FromEnvTests(unittest.TestCase):
    def test_defaults_are_used_when_environment_is_empty(self) -> None:
        settings = from_env({})

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.log_format, "console")
        self.assertEqual(settings.playback_backend, "stub")
        self.assertEqual(settings.duplicate_window_seconds, 2.0)
        self.assertEqual(settings.input_backend, "stdin")
        self.assertIsNone(settings.scanner_device)
        self.assertIsNone(settings.spotify_client_id)
        self.assertIsNone(settings.spotify_client_secret)
        self.assertIsNone(settings.spotify_refresh_token)
        self.assertIsNone(settings.spotify_device_id)
        self.assertIsNone(settings.spotify_target_device_name)
        self.assertEqual(settings.spotify_confirm_timeout_seconds, 5.0)
        self.assertEqual(settings.spotify_confirm_poll_interval_seconds, 0.25)

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

    def test_epic_one_settings_are_loaded(self) -> None:
        settings = from_env(
            {
                "JUKEBOX_PLAYBACK_BACKEND": "spotify",
                "JUKEBOX_DUPLICATE_WINDOW_SECONDS": "1.5",
                "JUKEBOX_INPUT_BACKEND": "evdev",
                "JUKEBOX_SCANNER_DEVICE": "/dev/input/by-id/scanner-event-kbd",
                "JUKEBOX_SPOTIFY_CLIENT_ID": "client-id",
                "JUKEBOX_SPOTIFY_CLIENT_SECRET": "client-secret",
                "JUKEBOX_SPOTIFY_REFRESH_TOKEN": "refresh-token",
                "JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME": "jukebox",
                "JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS": "3.5",
                "JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS": "0.5",
            }
        )

        self.assertEqual(settings.playback_backend, "spotify")
        self.assertEqual(settings.duplicate_window_seconds, 1.5)
        self.assertEqual(settings.input_backend, "evdev")
        self.assertEqual(settings.scanner_device, "/dev/input/by-id/scanner-event-kbd")
        self.assertEqual(settings.spotify_client_id, "client-id")
        self.assertEqual(settings.spotify_client_secret, "client-secret")
        self.assertEqual(settings.spotify_refresh_token, "refresh-token")
        self.assertIsNone(settings.spotify_device_id)
        self.assertEqual(settings.spotify_target_device_name, "jukebox")
        self.assertEqual(settings.spotify_confirm_timeout_seconds, 3.5)
        self.assertEqual(settings.spotify_confirm_poll_interval_seconds, 0.5)

    def test_invalid_log_level_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_LOG_LEVEL": "verbose"})

    def test_invalid_log_format_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_LOG_FORMAT": "text"})

    def test_invalid_playback_backend_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_PLAYBACK_BACKEND": "local"})

    def test_invalid_input_backend_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_INPUT_BACKEND": "keyboard"})

    def test_duplicate_window_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_DUPLICATE_WINDOW_SECONDS": "0"})

    def test_spotify_backend_requires_credentials(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_PLAYBACK_BACKEND": "spotify"})

    def test_evdev_backend_requires_scanner_device(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_INPUT_BACKEND": "evdev"})

    def test_spotify_backend_requires_target_device_name_or_device_id(self) -> None:
        with self.assertRaises(ConfigError):
            from_env(
                {
                    "JUKEBOX_PLAYBACK_BACKEND": "spotify",
                    "JUKEBOX_SPOTIFY_CLIENT_ID": "client-id",
                    "JUKEBOX_SPOTIFY_CLIENT_SECRET": "client-secret",
                    "JUKEBOX_SPOTIFY_REFRESH_TOKEN": "refresh-token",
                }
            )

    def test_poll_interval_must_be_positive_and_not_exceed_timeout(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS": "0"})

        with self.assertRaises(ConfigError):
            from_env(
                {
                    "JUKEBOX_PLAYBACK_BACKEND": "spotify",
                    "JUKEBOX_SPOTIFY_CLIENT_ID": "client-id",
                    "JUKEBOX_SPOTIFY_CLIENT_SECRET": "client-secret",
                    "JUKEBOX_SPOTIFY_REFRESH_TOKEN": "refresh-token",
                    "JUKEBOX_SPOTIFY_TARGET_DEVICE_NAME": "jukebox",
                    "JUKEBOX_SPOTIFY_CONFIRM_TIMEOUT_SECONDS": "1.0",
                    "JUKEBOX_SPOTIFY_CONFIRM_POLL_INTERVAL_SECONDS": "1.5",
                }
            )
