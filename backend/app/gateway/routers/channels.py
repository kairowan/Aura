"""Gateway router for IM channel management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aura.config.app_config import get_app_config, reload_app_config, save_channels_config_overlay

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelStatusResponse(BaseModel):
    service_running: bool
    channels: dict[str, dict]


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


class ManagedChannelConfig(BaseModel):
    enabled: bool = False
    assistant_id: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    bot_token: str | None = None
    app_token: str | None = None
    allowed_users: list[str] = Field(default_factory=list)


class ChannelConfigResponse(BaseModel):
    default_assistant_id: str | None = None
    feishu: ManagedChannelConfig = Field(default_factory=ManagedChannelConfig)
    slack: ManagedChannelConfig = Field(default_factory=ManagedChannelConfig)
    telegram: ManagedChannelConfig = Field(default_factory=ManagedChannelConfig)


class ChannelConfigSaveResponse(BaseModel):
    success: bool
    message: str
    status: ChannelStatusResponse


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _extract_current_channels_config() -> dict[str, Any]:
    config = get_app_config()
    extra = config.model_extra or {}
    raw = extra.get("channels", {})
    return dict(raw) if isinstance(raw, dict) else {}


def _to_response_model(raw: dict[str, Any]) -> ChannelConfigResponse:
    session = _as_dict(raw.get("session"))

    def build_channel(name: str) -> ManagedChannelConfig:
        channel = _as_dict(raw.get(name))
        channel_session = _as_dict(channel.get("session"))
        allowed_users = channel.get("allowed_users", [])
        if not isinstance(allowed_users, list):
            allowed_users = []
        return ManagedChannelConfig(
            enabled=bool(channel.get("enabled", False)),
            assistant_id=channel_session.get("assistant_id"),
            app_id=channel.get("app_id"),
            app_secret=channel.get("app_secret"),
            bot_token=channel.get("bot_token"),
            app_token=channel.get("app_token"),
            allowed_users=[str(item) for item in allowed_users],
        )

    return ChannelConfigResponse(
        default_assistant_id=session.get("assistant_id"),
        feishu=build_channel("feishu"),
        slack=build_channel("slack"),
        telegram=build_channel("telegram"),
    )


def _apply_form_values(raw: dict[str, Any], config: ChannelConfigResponse) -> dict[str, Any]:
    updated = dict(raw)

    if config.default_assistant_id:
        updated["session"] = {
            **_as_dict(updated.get("session")),
            "assistant_id": config.default_assistant_id.strip(),
        }
    elif "session" in updated:
        session = _as_dict(updated.get("session"))
        session.pop("assistant_id", None)
        updated["session"] = session

    def write_channel(name: str, item: ManagedChannelConfig) -> None:
        existing = _as_dict(updated.get(name))
        existing["enabled"] = item.enabled

        if item.assistant_id and item.assistant_id.strip():
            existing["session"] = {
                **_as_dict(existing.get("session")),
                "assistant_id": item.assistant_id.strip(),
            }
        elif "session" in existing:
            session = _as_dict(existing.get("session"))
            session.pop("assistant_id", None)
            existing["session"] = session

        for key in ("app_id", "app_secret", "bot_token", "app_token"):
            value = getattr(item, key)
            if value:
                existing[key] = value.strip()
            elif key in existing:
                existing.pop(key, None)

        if item.allowed_users:
            existing["allowed_users"] = [value.strip() for value in item.allowed_users if value.strip()]
        elif "allowed_users" in existing:
            existing.pop("allowed_users", None)

        updated[name] = existing

    write_channel("feishu", config.feishu)
    write_channel("slack", config.slack)
    write_channel("telegram", config.telegram)
    return updated


@router.get("/", response_model=ChannelStatusResponse)
async def get_channels_status() -> ChannelStatusResponse:
    """Get the status of all IM channels."""
    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is None:
        return ChannelStatusResponse(service_running=False, channels={})
    status = service.get_status()
    return ChannelStatusResponse(**status)


@router.get("/config", response_model=ChannelConfigResponse)
async def get_channels_config() -> ChannelConfigResponse:
    """Get the editable channel config exposed in the settings UI."""
    raw = _extract_current_channels_config()
    return _to_response_model(raw)


@router.post("/config", response_model=ChannelConfigSaveResponse)
async def save_channels_config(config: ChannelConfigResponse) -> ChannelConfigSaveResponse:
    """Persist channel config and hot-reload the channel service."""
    raw = _extract_current_channels_config()
    updated = _apply_form_values(raw, config)
    save_channels_config_overlay(updated)
    reload_app_config()

    from app.channels.service import get_channel_service, start_channel_service

    service = get_channel_service()
    try:
        if service is None:
            service = await start_channel_service()
        else:
            await service.reload_from_app_config()
    except Exception as e:
        logger.exception("Failed to reload channel service after config save")
        raise HTTPException(status_code=500, detail=f"渠道配置已保存，但热重载失败: {e}") from e

    status = ChannelStatusResponse(**service.get_status())
    return ChannelConfigSaveResponse(
        success=True,
        message="渠道配置已保存并完成热重载。",
        status=status,
    )


@router.post("/{name}/restart", response_model=ChannelRestartResponse)
async def restart_channel(name: str) -> ChannelRestartResponse:
    """Restart a specific IM channel."""
    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Channel service is not running")

    success = await service.restart_channel(name)
    if success:
        logger.info("Channel %s restarted successfully", name)
        return ChannelRestartResponse(success=True, message=f"Channel {name} restarted successfully")
    else:
        logger.warning("Failed to restart channel %s", name)
        return ChannelRestartResponse(success=False, message=f"Failed to restart channel {name}")
