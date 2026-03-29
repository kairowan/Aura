from pathlib import Path
import json
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from starlette.concurrency import run_in_threadpool

from aura.config.app_config import build_custom_provider_model_data
from aura.config.model_config import ModelConfig
from aura.reflection import resolve_class

router = APIRouter(prefix="/api/provider", tags=["provider"])
logger = logging.getLogger(__name__)


def _resolve_root_dir() -> Path:
    """Resolve the project root directory for config touch fallback."""
    root_dir = Path(os.getcwd())
    if not (root_dir / ".aura").exists() and (root_dir.parent / ".aura").exists():
        root_dir = root_dir.parent
    return root_dir


def _resolve_provider_config_path() -> Path:
    """Resolve the provider config path, allowing desktop runtime override."""
    env_path = os.getenv("AURA_PROVIDER_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return _resolve_root_dir() / ".aura" / "provider_config.json"

class ProviderConfig(BaseModel):
    """Model for AI Provider configuration."""
    base_url: str | None = Field(None, description="API Base URL (e.g., https://api.openai.com/v1)")
    api_key: str | None = Field(None, description="API Key")
    model_id: str | None = Field(None, description="Model ID (e.g., gpt-4o, deepseek-chat)")
    display_name: str | None = Field(None, description="Human-readable name")


class ProviderValidationResponse(BaseModel):
    success: bool = Field(..., description="Whether the provider validation succeeded")
    message: str = Field(..., description="Validation result message")


def _sanitize_error_message(message: str, api_key: str | None) -> str:
    sanitized = message
    if api_key:
        sanitized = sanitized.replace(api_key, "[REDACTED]")
    return sanitized


def _build_validation_model(config: ProviderConfig) -> BaseChatModel:
    model_data = build_custom_provider_model_data(config.model_dump(exclude_none=True))
    if not model_data:
        raise ValueError("Base URL 和 API Key 都是必填项。")

    model_config = ModelConfig.model_validate(model_data)
    model_class = resolve_class(model_config.use, BaseChatModel)
    model_settings = model_config.model_dump(
        exclude_none=True,
        exclude={
            "use",
            "name",
            "display_name",
            "description",
            "supports_thinking",
            "supports_reasoning_effort",
            "when_thinking_enabled",
            "thinking",
            "supports_vision",
        },
    )
    return model_class(**model_settings)

@router.get("/config", response_model=ProviderConfig)
async def get_provider_config():
    """Get the current custom provider configuration."""
    config_path = _resolve_provider_config_path()
    if not config_path.exists():
        return ProviderConfig()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ProviderConfig(**data)
    except Exception as e:
        logger.error(f"Failed to read provider config: {e}")
        return ProviderConfig()

@router.post("/config")
async def save_provider_config(config: ProviderConfig):
    """Save the custom provider configuration."""
    try:
        config_path = _resolve_provider_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Touch config.yaml to trigger AppConfig reload if needed
        # (Though we'll also update AppConfig to check this file)
        config_yaml_env = os.getenv("AURA_CONFIG_PATH")
        config_yaml = Path(config_yaml_env).expanduser() if config_yaml_env else _resolve_root_dir() / "config.yaml"
        if config_yaml.exists():
            config_yaml.touch()
            
        return {"status": "success", "message": "Provider configuration saved"}
    except Exception as e:
        logger.error(f"Failed to save provider config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@router.post("/validate", response_model=ProviderValidationResponse)
async def validate_provider_config(config: ProviderConfig):
    """Validate the provider settings by performing a minimal model call."""
    try:
        model = _build_validation_model(config)
        response = await run_in_threadpool(
            model.invoke,
            [HumanMessage(content="Reply with OK only.")],
        )
        response_text = getattr(response, "content", "") or "OK"
        response_text = str(response_text).strip()[:120]
        return ProviderValidationResponse(
            success=True,
            message=f"连接成功，模型已返回: {response_text}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        message = _sanitize_error_message(str(e), config.api_key)
        logger.warning("Provider validation failed: %s", message)
        raise HTTPException(
            status_code=400,
            detail=f"连接失败: {message}",
        ) from e
