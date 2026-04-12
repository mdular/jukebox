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
        self.assertEqual(settings.health_poll_interval_seconds, 5.0)
        self.assertEqual(settings.operator_http_bind, "127.0.0.1")
        self.assertEqual(settings.operator_http_port, 8080)
        self.assertEqual(settings.operator_state_path, "/var/lib/jukebox/state.json")
        self.assertEqual(settings.control_debounce_seconds, 1.0)
        self.assertEqual(settings.playback_mode_default, "replace")
        self.assertEqual(settings.volume_preset_low_percent, 35)
        self.assertEqual(settings.volume_preset_medium_percent, 55)
        self.assertEqual(settings.volume_preset_high_percent, 75)
        self.assertIsNone(settings.idle_shutdown_seconds)
        self.assertIsNone(settings.setup_ap_ssid)
        self.assertIsNone(settings.setup_ap_passphrase)
        self.assertEqual(settings.setup_fallback_grace_seconds, 120.0)
        self.assertEqual(settings.wifi_rollback_timeout_seconds, 120.0)
        self.assertEqual(settings.wifi_helper_command, "/usr/local/libexec/jukebox-wifi-helper")
        self.assertEqual(
            settings.spotifyd_auth_helper_command,
            "/usr/local/libexec/jukebox-spotifyd-auth-helper",
        )
        self.assertEqual(
            settings.shutdown_helper_command, "/usr/local/libexec/jukebox-shutdown-helper"
        )

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
                "JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS": "7.5",
                "JUKEBOX_OPERATOR_HTTP_BIND": "0.0.0.0",
                "JUKEBOX_OPERATOR_HTTP_PORT": "9090",
                "JUKEBOX_OPERATOR_STATE_PATH": "/tmp/jukebox-state.json",
                "JUKEBOX_CONTROL_DEBOUNCE_SECONDS": "1.25",
                "JUKEBOX_PLAYBACK_MODE_DEFAULT": "queue_tracks",
                "JUKEBOX_VOLUME_PRESET_LOW_PERCENT": "20",
                "JUKEBOX_VOLUME_PRESET_MEDIUM_PERCENT": "50",
                "JUKEBOX_VOLUME_PRESET_HIGH_PERCENT": "90",
                "JUKEBOX_IDLE_SHUTDOWN_SECONDS": "1800",
                "JUKEBOX_SETUP_AP_SSID": "jukebox-setup",
                "JUKEBOX_SETUP_AP_PASSPHRASE": "secret-pass",
                "JUKEBOX_SETUP_FALLBACK_GRACE_SECONDS": "180",
                "JUKEBOX_WIFI_ROLLBACK_TIMEOUT_SECONDS": "240",
                "JUKEBOX_WIFI_HELPER_COMMAND": "/opt/bin/wifi-helper",
                "JUKEBOX_SPOTIFYD_AUTH_HELPER_COMMAND": "/opt/bin/auth-helper",
                "JUKEBOX_SHUTDOWN_HELPER_COMMAND": "/opt/bin/shutdown-helper",
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
        self.assertEqual(settings.health_poll_interval_seconds, 7.5)
        self.assertEqual(settings.operator_http_bind, "0.0.0.0")
        self.assertEqual(settings.operator_http_port, 9090)
        self.assertEqual(settings.operator_state_path, "/tmp/jukebox-state.json")
        self.assertEqual(settings.control_debounce_seconds, 1.25)
        self.assertEqual(settings.playback_mode_default, "queue_tracks")
        self.assertEqual(settings.volume_preset_low_percent, 20)
        self.assertEqual(settings.volume_preset_medium_percent, 50)
        self.assertEqual(settings.volume_preset_high_percent, 90)
        self.assertEqual(settings.idle_shutdown_seconds, 1800.0)
        self.assertEqual(settings.setup_ap_ssid, "jukebox-setup")
        self.assertEqual(settings.setup_ap_passphrase, "secret-pass")
        self.assertEqual(settings.setup_fallback_grace_seconds, 180.0)
        self.assertEqual(settings.wifi_rollback_timeout_seconds, 240.0)
        self.assertEqual(settings.wifi_helper_command, "/opt/bin/wifi-helper")
        self.assertEqual(settings.spotifyd_auth_helper_command, "/opt/bin/auth-helper")
        self.assertEqual(settings.shutdown_helper_command, "/opt/bin/shutdown-helper")

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

    def test_health_poll_interval_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_HEALTH_POLL_INTERVAL_SECONDS": "0"})

    def test_playback_mode_default_must_be_supported(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_PLAYBACK_MODE_DEFAULT": "queue"})

    def test_operator_http_port_must_be_valid(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_OPERATOR_HTTP_PORT": "70000"})

    def test_volume_presets_must_be_between_zero_and_one_hundred(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_VOLUME_PRESET_HIGH_PERCENT": "101"})

    def test_idle_shutdown_seconds_must_be_positive_if_configured(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_IDLE_SHUTDOWN_SECONDS": "0"})

    def test_setup_ap_passphrase_must_be_long_enough(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_SETUP_AP_PASSPHRASE": "short"})

    def test_wifi_rollback_timeout_seconds_must_be_positive(self) -> None:
        with self.assertRaises(ConfigError):
            from_env({"JUKEBOX_WIFI_ROLLBACK_TIMEOUT_SECONDS": "0"})
