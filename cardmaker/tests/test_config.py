from __future__ import annotations

import pytest

from cardmaker.config import ConfigurationError, Settings


def test_settings_load_required_spotify_values_and_defaults() -> None:
    settings = Settings.from_environ(
        {
            "CARDMAKER_SPOTIFY_CLIENT_ID": "client-id",
            "CARDMAKER_SPOTIFY_CLIENT_SECRET": "client-secret",
            "CARDMAKER_SPOTIFY_MARKET": "de",
        }
    )

    assert settings.spotify_client_id == "client-id"
    assert settings.spotify_client_secret == "client-secret"
    assert settings.spotify_market == "DE"
    assert settings.http_bind == "127.0.0.1"
    assert settings.http_port == 8081
    assert settings.log_level == "INFO"


@pytest.mark.parametrize(
    "missing_name",
    [
        "CARDMAKER_SPOTIFY_CLIENT_ID",
        "CARDMAKER_SPOTIFY_CLIENT_SECRET",
        "CARDMAKER_SPOTIFY_MARKET",
    ],
)
def test_settings_name_a_missing_required_variable(missing_name: str) -> None:
    environ = {
        "CARDMAKER_SPOTIFY_CLIENT_ID": "client-id",
        "CARDMAKER_SPOTIFY_CLIENT_SECRET": "client-secret",
        "CARDMAKER_SPOTIFY_MARKET": "DE",
    }
    del environ[missing_name]

    with pytest.raises(ConfigurationError, match=missing_name):
        Settings.from_environ(environ)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CARDMAKER_SPOTIFY_MARKET", "Germany"),
        ("CARDMAKER_HTTP_PORT", "not-a-port"),
        ("CARDMAKER_HTTP_PORT", "70000"),
        ("CARDMAKER_LOG_LEVEL", "VERBOSE"),
    ],
)
def test_settings_reject_invalid_values(name: str, value: str) -> None:
    environ = {
        "CARDMAKER_SPOTIFY_CLIENT_ID": "client-id",
        "CARDMAKER_SPOTIFY_CLIENT_SECRET": "client-secret",
        "CARDMAKER_SPOTIFY_MARKET": "DE",
        name: value,
    }

    with pytest.raises(ConfigurationError, match=name):
        Settings.from_environ(environ)
