"""Configuration management for the dependent todos application."""

import os
from pathlib import Path


def get_config_path(config_override: str | None = None) -> Path:
    """Get the path to the todos configuration file.

    Priority order:
    1. --config CLI flag (highest priority)
    2. TODOS_CONFIG environment variable
    3. Default local path in current working directory

    Args:
        config_override: Explicit config path from CLI flag or env var

    Returns:
        Path to the configuration file
    """
    if config_override:
        return Path(config_override).expanduser().resolve()

    # Check environment variable
    env_config = os.environ.get("TODOS_CONFIG")
    if env_config:
        return Path(env_config).expanduser().resolve()

    # Default local path
    return Path.cwd() / "todos.toml"


def ensure_config_directory(config_path: Path) -> None:
    """Ensure the configuration directory exists.

    Args:
        config_path: Path to the config file
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
