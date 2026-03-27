from pathlib import Path
import json
import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/provider", tags=["provider"])
logger = logging.getLogger(__name__)

# Storage path for custom provider config
# Using root-level .aura directory if it exists, else fallback to current dir
ROOT_DIR = Path(os.getcwd())
if not (ROOT_DIR / ".aura").exists() and (ROOT_DIR.parent / ".aura").exists():
    ROOT_DIR = ROOT_DIR.parent

CONFIG_PATH = ROOT_DIR / ".aura" / "provider_config.json"

class ProviderConfig(BaseModel):
    """Model for AI Provider configuration."""
    base_url: str | None = Field(None, description="API Base URL (e.g., https://api.openai.com/v1)")
    api_key: str | None = Field(None, description="API Key")
    model_id: str | None = Field(None, description="Model ID (e.g., gpt-4o, deepseek-chat)")
    display_name: str | None = Field(None, description="Human-readable name")

@router.get("/config", response_model=ProviderConfig)
async def get_provider_config():
    """Get the current custom provider configuration."""
    if not CONFIG_PATH.exists():
        return ProviderConfig()
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ProviderConfig(**data)
    except Exception as e:
        logger.error(f"Failed to read provider config: {e}")
        return ProviderConfig()

@router.post("/config")
async def save_provider_config(config: ProviderConfig):
    """Save the custom provider configuration."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Touch config.yaml to trigger AppConfig reload if needed
        # (Though we'll also update AppConfig to check this file)
        config_yaml = ROOT_DIR / "config.yaml"
        if config_yaml.exists():
            config_yaml.touch()
            
        return {"status": "success", "message": "Provider configuration saved"}
    except Exception as e:
        logger.error(f"Failed to save provider config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")
