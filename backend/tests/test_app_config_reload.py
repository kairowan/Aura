from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from aura.config.app_config import get_app_config, reset_app_config


def _write_config(path: Path, *, model_name: str, supports_thinking: bool) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "sandbox": {"use": "aura.sandbox.local:LocalSandboxProvider"},
                "models": [
                    {
                        "name": model_name,
                        "use": "langchain_openai:ChatOpenAI",
                        "model": "gpt-test",
                        "supports_thinking": supports_thinking,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_extensions_config(path: Path) -> None:
    path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")


def _write_provider_config(path: Path, *, base_url: str, api_key: str, model_id: str = "gpt-test") -> None:
    path.write_text(
        json.dumps(
            {
                "base_url": base_url,
                "api_key": api_key,
                "model_id": model_id,
                "display_name": "Custom Provider",
            }
        ),
        encoding="utf-8",
    )


def _write_channels_config(
    path: Path,
    *,
    default_assistant_id: str = "lead_agent",
    telegram_bot_token: str = "telegram-token",
) -> None:
    path.write_text(
        json.dumps(
            {
                "session": {
                    "assistant_id": default_assistant_id,
                },
                "telegram": {
                    "enabled": True,
                    "bot_token": telegram_bot_token,
                    "session": {
                        "assistant_id": "mobile_agent",
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def test_get_app_config_reloads_when_file_changes(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    extensions_path = tmp_path / "extensions_config.json"
    _write_extensions_config(extensions_path)
    _write_config(config_path, model_name="first-model", supports_thinking=False)

    monkeypatch.setenv("AURA_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AURA_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    reset_app_config()

    try:
        initial = get_app_config()
        assert initial.models[0].supports_thinking is False

        _write_config(config_path, model_name="first-model", supports_thinking=True)
        next_mtime = config_path.stat().st_mtime + 5
        os.utime(config_path, (next_mtime, next_mtime))

        reloaded = get_app_config()
        assert reloaded.models[0].supports_thinking is True
        assert reloaded is not initial
    finally:
        reset_app_config()


def test_get_app_config_reloads_when_config_path_changes(tmp_path, monkeypatch):
    config_a = tmp_path / "config-a.yaml"
    config_b = tmp_path / "config-b.yaml"
    extensions_path = tmp_path / "extensions_config.json"
    _write_extensions_config(extensions_path)
    _write_config(config_a, model_name="model-a", supports_thinking=False)
    _write_config(config_b, model_name="model-b", supports_thinking=True)

    monkeypatch.setenv("AURA_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    monkeypatch.setenv("AURA_CONFIG_PATH", str(config_a))
    reset_app_config()

    try:
        first = get_app_config()
        assert first.models[0].name == "model-a"

        monkeypatch.setenv("AURA_CONFIG_PATH", str(config_b))
        second = get_app_config()
        assert second.models[0].name == "model-b"
        assert second is not first
    finally:
        reset_app_config()


def test_get_app_config_injects_custom_provider_with_base_url(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    extensions_path = tmp_path / "extensions_config.json"
    provider_path = tmp_path / "provider_config.json"

    _write_extensions_config(extensions_path)
    config_path.write_text(
        yaml.safe_dump(
            {
                "sandbox": {"use": "aura.sandbox.local:LocalSandboxProvider"},
                "models": [],
            }
        ),
        encoding="utf-8",
    )
    _write_provider_config(
        provider_path,
        base_url="https://example.com/v1",
        api_key="test-key",
        model_id="custom-model",
    )

    monkeypatch.setenv("AURA_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AURA_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    monkeypatch.setenv("AURA_PROVIDER_CONFIG_PATH", str(provider_path))
    reset_app_config()

    try:
        config = get_app_config()
        assert config.models[0].name == "custom-provider"
        assert config.models[0].model == "custom-model"
        assert config.models[0].model_extra["base_url"] == "https://example.com/v1"
        assert "api_base" not in config.models[0].model_extra
    finally:
        reset_app_config()


def test_get_app_config_reloads_when_provider_config_changes_and_config_is_touched(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    extensions_path = tmp_path / "extensions_config.json"
    provider_path = tmp_path / "provider_config.json"

    _write_extensions_config(extensions_path)
    config_path.write_text(
        yaml.safe_dump(
            {
                "sandbox": {"use": "aura.sandbox.local:LocalSandboxProvider"},
                "models": [],
            }
        ),
        encoding="utf-8",
    )
    _write_provider_config(
        provider_path,
        base_url="https://example.com/v1",
        api_key="test-key",
        model_id="first-model",
    )

    monkeypatch.setenv("AURA_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AURA_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    monkeypatch.setenv("AURA_PROVIDER_CONFIG_PATH", str(provider_path))
    reset_app_config()

    try:
        initial = get_app_config()
        assert initial.models[0].model == "first-model"

        _write_provider_config(
            provider_path,
            base_url="https://example.com/v2",
            api_key="test-key-2",
            model_id="second-model",
        )
        next_mtime = config_path.stat().st_mtime + 5
        os.utime(config_path, (next_mtime, next_mtime))

        reloaded = get_app_config()
        assert reloaded.models[0].model == "second-model"
        assert reloaded.models[0].model_extra["base_url"] == "https://example.com/v2"
        assert reloaded is not initial
    finally:
        reset_app_config()


def test_get_app_config_merges_runtime_channels_overlay(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    extensions_path = tmp_path / "extensions_config.json"
    channels_path = tmp_path / "channels_config.json"

    _write_extensions_config(extensions_path)
    config_path.write_text(
        yaml.safe_dump(
            {
                "sandbox": {"use": "aura.sandbox.local:LocalSandboxProvider"},
                "models": [],
            }
        ),
        encoding="utf-8",
    )
    _write_channels_config(
        channels_path,
        default_assistant_id="ops_agent",
        telegram_bot_token="secret-token",
    )

    monkeypatch.setenv("AURA_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AURA_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    monkeypatch.setenv("AURA_CHANNELS_CONFIG_PATH", str(channels_path))
    reset_app_config()

    try:
        config = get_app_config()
        extra = config.model_extra or {}
        channels = extra["channels"]
        assert channels["session"]["assistant_id"] == "ops_agent"
        assert channels["telegram"]["enabled"] is True
        assert channels["telegram"]["bot_token"] == "secret-token"
        assert channels["telegram"]["session"]["assistant_id"] == "mobile_agent"
    finally:
        reset_app_config()
