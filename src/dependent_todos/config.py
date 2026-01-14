"""Configuration management for the dependent todos application."""

import os
from pathlib import Path

from dependent_todos.constants import TODOS_CONFIG_ENV_KEY, TODOS_CONFIG_NAME


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
    # Check environment variable
    env_config = os.environ.get(TODOS_CONFIG_ENV_KEY)
    p = TODOS_CONFIG_NAME
    if config_override:
        p = config_override
        if config_override == TODOS_CONFIG_NAME and env_config:
            p = env_config
    elif env_config:
        p = env_config
    return Path(p).expanduser().resolve()


def ensure_config_directory(config_path: Path) -> None:
    """Ensure the configuration directory exists.

    Args:
        config_path: Path to the config file
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
