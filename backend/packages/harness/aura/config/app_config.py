import json
import logging
import os
from pathlib import Path
from typing import Any, Self

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from aura.config.acp_config import load_acp_config_from_dict
from aura.config.checkpointer_config import CheckpointerConfig, load_checkpointer_config_from_dict
from aura.config.extensions_config import ExtensionsConfig
from aura.config.guardrails_config import load_guardrails_config_from_dict
from aura.config.memory_config import load_memory_config_from_dict
from aura.config.model_config import ModelConfig
from aura.config.sandbox_config import SandboxConfig
from aura.config.skills_config import SkillsConfig
from aura.config.subagents_config import load_subagents_config_from_dict
from aura.config.summarization_config import load_summarization_config_from_dict
from aura.config.title_config import load_title_config_from_dict
from aura.config.token_usage_config import TokenUsageConfig
from aura.config.tool_config import ToolConfig, ToolGroupConfig
from aura.config.tool_search_config import ToolSearchConfig, load_tool_search_config_from_dict
from aura.config.paths import get_paths

load_dotenv()

logger = logging.getLogger(__name__)


def _merge_mapping_layers(base: Any, overlay: Any) -> Any:
    """Recursively merge two mapping-like objects, preferring overlay values."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            merged[key] = _merge_mapping_layers(merged.get(key), value)
        return merged
    return overlay if overlay is not None else base


def resolve_channels_config_path() -> Path:
    """Resolve the runtime channels config override path."""
    env_path = os.getenv("AURA_CHANNELS_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return get_paths().base_dir / "channels" / "config.json"


def load_channels_config_overlay() -> dict[str, Any]:
    """Load runtime channel overrides from disk."""
    config_path = resolve_channels_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error("Failed to load runtime channels config: %s", e)
        return {}


def save_channels_config_overlay(config: dict[str, Any]) -> Path:
    """Persist runtime channel overrides to disk."""
    config_path = resolve_channels_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config_path


def resolve_provider_config_path(config_path: Path | None = None) -> Path:
    """Resolve the runtime provider config path.

    Priority:
    1. `AURA_PROVIDER_CONFIG_PATH` environment variable
    2. `{AURA_HOME|base_dir}/provider_config.json`
    3. Legacy fallback: sibling `.aura/provider_config.json` next to config.yaml
    """
    env_path = os.getenv("AURA_PROVIDER_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()

    base_dir_candidate = get_paths().base_dir / "provider_config.json"
    if base_dir_candidate.exists():
        return base_dir_candidate

    if config_path is not None:
        return config_path.parent / ".aura" / "provider_config.json"
    return base_dir_candidate


def build_custom_provider_model_data(custom_config: dict[str, Any]) -> dict[str, Any] | None:
    """Build a transient model config from provider settings saved by the UI."""
    api_key = custom_config.get("api_key")
    base_url = custom_config.get("base_url")

    if not api_key or not base_url:
        return None

    return {
        "name": "custom-provider",
        "display_name": custom_config.get("display_name") or "Custom AI",
        "use": "langchain_openai:ChatOpenAI",
        "model": custom_config.get("model_id") or "gpt-4o",
        "base_url": base_url,
        "api_key": api_key,
        "supports_thinking": True,
        "supports_vision": True,
    }


class AppConfig(BaseModel):
    """Config for the Aura application"""

    log_level: str = Field(default="info", description="Logging level for aura modules (debug/info/warning/error)")
    token_usage: TokenUsageConfig = Field(default_factory=TokenUsageConfig, description="Token usage tracking configuration")
    models: list[ModelConfig] = Field(default_factory=list, description="Available models")
    sandbox: SandboxConfig = Field(description="Sandbox configuration")
    tools: list[ToolConfig] = Field(default_factory=list, description="Available tools")
    tool_groups: list[ToolGroupConfig] = Field(default_factory=list, description="Available tool groups")
    skills: SkillsConfig = Field(default_factory=SkillsConfig, description="Skills configuration")
    extensions: ExtensionsConfig = Field(default_factory=ExtensionsConfig, description="Extensions configuration (MCP servers and skills state)")
    tool_search: ToolSearchConfig = Field(default_factory=ToolSearchConfig, description="Tool search / deferred loading configuration")
    model_config = ConfigDict(extra="allow", frozen=False)
    checkpointer: CheckpointerConfig | None = Field(default=None, description="Checkpointer configuration")

    @classmethod
    def resolve_config_path(cls, config_path: str | None = None) -> Path:
        """Resolve the config file path.

        Priority:
        1. If provided `config_path` argument, use it.
        2. If provided `AURA_CONFIG_PATH` environment variable, use it.
        3. Otherwise, first check the `config.yaml` in the current directory, then fallback to `config.yaml` in the parent directory.
        """
        if config_path:
            path = Path(config_path)
            if not Path.exists(path):
                raise FileNotFoundError(f"Config file specified by param `config_path` not found at {path}")
            return path
        elif os.getenv("AURA_CONFIG_PATH"):
            path = Path(os.getenv("AURA_CONFIG_PATH"))
            if not Path.exists(path):
                raise FileNotFoundError(f"Config file specified by environment variable `AURA_CONFIG_PATH` not found at {path}")
            return path
        else:
            # Check if the config.yaml is in the current directory
            path = Path(os.getcwd()) / "config.yaml"
            if not path.exists():
                # Check if the config.yaml is in the parent directory of CWD
                path = Path(os.getcwd()).parent / "config.yaml"
                if not path.exists():
                    raise FileNotFoundError("`config.yaml` file not found at the current directory nor its parent directory")
            return path

    @classmethod
    def from_file(cls, config_path: str | None = None) -> Self:
        """Load config from YAML file.

        See `resolve_config_path` for more details.

        Args:
            config_path: Path to the config file.

        Returns:
            AppConfig: The loaded config.
        """
        resolved_path = cls.resolve_config_path(config_path)
        with open(resolved_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # Check config version before processing
        cls._check_config_version(config_data, resolved_path)

        config_data = cls.resolve_env_variables(config_data)

        # Load title config if present
        if "title" in config_data:
            load_title_config_from_dict(config_data["title"])

        # Load summarization config if present
        if "summarization" in config_data:
            load_summarization_config_from_dict(config_data["summarization"])

        # Load memory config if present
        if "memory" in config_data:
            load_memory_config_from_dict(config_data["memory"])

        # Load subagents config if present
        if "subagents" in config_data:
            load_subagents_config_from_dict(config_data["subagents"])

        # Load tool_search config if present
        if "tool_search" in config_data:
            load_tool_search_config_from_dict(config_data["tool_search"])

        # Load guardrails config if present
        if "guardrails" in config_data:
            load_guardrails_config_from_dict(config_data["guardrails"])

        # Load checkpointer config if present
        if "checkpointer" in config_data:
            load_checkpointer_config_from_dict(config_data["checkpointer"])

        # Always refresh ACP agent config so removed entries do not linger across reloads.
        load_acp_config_from_dict(config_data.get("acp_agents", {}))

        # Load extensions config separately (it's in a different file)
        extensions_config = ExtensionsConfig.from_file()
        config_data["extensions"] = extensions_config.model_dump()

        # Load custom provider config if present
        custom_provider_path = resolve_provider_config_path(resolved_path)
        if custom_provider_path.exists():
            try:
                with open(custom_provider_path, "r", encoding="utf-8") as f:
                    custom_config = json.load(f)
                    custom_model = build_custom_provider_model_data(custom_config)
                    if custom_model:
                        # Prepend to models list so it becomes the default
                        if "models" not in config_data:
                            config_data["models"] = []
                        config_data["models"] = [custom_model] + config_data["models"]
            except Exception as e:
                logger.error(f"Failed to load custom provider config: {e}")

        channels_overlay = load_channels_config_overlay()
        if channels_overlay:
            config_data["channels"] = _merge_mapping_layers(
                config_data.get("channels", {}),
                channels_overlay,
            )

        result = cls.model_validate(config_data)
        return result

    @classmethod
    def _check_config_version(cls, config_data: dict, config_path: Path) -> None:
        """Check if the user's config.yaml is outdated compared to config.example.yaml.

        Emits a warning if the user's config_version is lower than the example's.
        Missing config_version is treated as version 0 (pre-versioning).
        """
        try:
            user_version = int(config_data.get("config_version", 0))
        except (TypeError, ValueError):
            user_version = 0

        # Find config.example.yaml by searching config.yaml's directory and its parents
        example_path = None
        search_dir = config_path.parent
        for _ in range(5):  # search up to 5 levels
            candidate = search_dir / "config.example.yaml"
            if candidate.exists():
                example_path = candidate
                break
            parent = search_dir.parent
            if parent == search_dir:
                break
            search_dir = parent
        if example_path is None:
            return

        try:
            with open(example_path, encoding="utf-8") as f:
                example_data = yaml.safe_load(f)
            raw = example_data.get("config_version", 0) if example_data else 0
            try:
                example_version = int(raw)
            except (TypeError, ValueError):
                example_version = 0
        except Exception:
            return

        if user_version < example_version:
            logger.warning(
                "Your config.yaml (version %d) is outdated — the latest version is %d. Run `make config-upgrade` to merge new fields into your config.",
                user_version,
                example_version,
            )

    @classmethod
    def resolve_env_variables(cls, config: Any) -> Any:
        """Recursively resolve environment variables in the config.

        Environment variables are resolved using the `os.getenv` function. Example: $OPENAI_API_KEY

        Args:
            config: The config to resolve environment variables in.

        Returns:
            The config with environment variables resolved.
        """
        if isinstance(config, str):
            if config.startswith("$"):
                env_value = os.getenv(config[1:])
                if env_value is None:
                    raise ValueError(f"Environment variable {config[1:]} not found for config value {config}")
                return env_value
            return config
        elif isinstance(config, dict):
            return {k: cls.resolve_env_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [cls.resolve_env_variables(item) for item in config]
        return config

    def get_model_config(self, name: str) -> ModelConfig | None:
        """Get the model config by name.

        Args:
            name: The name of the model to get the config for.

        Returns:
            The model config if found, otherwise None.
        """
        return next((model for model in self.models if model.name == name), None)

    def get_tool_config(self, name: str) -> ToolConfig | None:
        """Get the tool config by name.

        Args:
            name: The name of the tool to get the config for.

        Returns:
            The tool config if found, otherwise None.
        """
        return next((tool for tool in self.tools if tool.name == name), None)

    def get_tool_group_config(self, name: str) -> ToolGroupConfig | None:
        """Get the tool group config by name.

        Args:
            name: The name of the tool group to get the config for.

        Returns:
            The tool group config if found, otherwise None.
        """
        return next((group for group in self.tool_groups if group.name == name), None)


_app_config: AppConfig | None = None
_app_config_path: Path | None = None
_app_config_mtime: float | None = None
_app_config_is_custom = False


def _get_config_mtime(config_path: Path) -> float | None:
    """Get the modification time of a config file if it exists."""
    try:
        return config_path.stat().st_mtime
    except OSError:
        return None


def _load_and_cache_app_config(config_path: str | None = None) -> AppConfig:
    """Load config from disk and refresh cache metadata."""
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom

    resolved_path = AppConfig.resolve_config_path(config_path)
    _app_config = AppConfig.from_file(str(resolved_path))
    _app_config_path = resolved_path
    _app_config_mtime = _get_config_mtime(resolved_path)
    _app_config_is_custom = False
    return _app_config


def get_app_config() -> AppConfig:
    """Get the Aura config instance.

    Returns a cached singleton instance and automatically reloads it when the
    underlying config file path or modification time changes. Use
    `reload_app_config()` to force a reload, or `reset_app_config()` to clear
    the cache.
    """
    global _app_config, _app_config_path, _app_config_mtime

    if _app_config is not None and _app_config_is_custom:
        return _app_config

    resolved_path = AppConfig.resolve_config_path()
    current_mtime = _get_config_mtime(resolved_path)

    should_reload = _app_config is None or _app_config_path != resolved_path or _app_config_mtime != current_mtime
    if should_reload:
        if _app_config_path == resolved_path and _app_config_mtime is not None and current_mtime is not None and _app_config_mtime != current_mtime:
            logger.info(
                "Config file has been modified (mtime: %s -> %s), reloading AppConfig",
                _app_config_mtime,
                current_mtime,
            )
        _load_and_cache_app_config(str(resolved_path))
    return _app_config


def reload_app_config(config_path: str | None = None) -> AppConfig:
    """Reload the config from file and update the cached instance.

    This is useful when the config file has been modified and you want
    to pick up the changes without restarting the application.

    Args:
        config_path: Optional path to config file. If not provided,
                     uses the default resolution strategy.

    Returns:
        The newly loaded AppConfig instance.
    """
    return _load_and_cache_app_config(config_path)


def reset_app_config() -> None:
    """Reset the cached config instance.

    This clears the singleton cache, causing the next call to
    `get_app_config()` to reload from file. Useful for testing
    or when switching between different configurations.
    """
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom
    _app_config = None
    _app_config_path = None
    _app_config_mtime = None
    _app_config_is_custom = False


def set_app_config(config: AppConfig) -> None:
    """Set a custom config instance.

    This allows injecting a custom or mock config for testing purposes.

    Args:
        config: The AppConfig instance to use.
    """
    global _app_config, _app_config_path, _app_config_mtime, _app_config_is_custom
    _app_config = config
    _app_config_path = None
    _app_config_mtime = None
    _app_config_is_custom = True
