"""Test configuration and fixtures."""

import os
import pytest
from pathlib import Path

from dependent_todos.tui import DependentTodosApp


@pytest.fixture
def temp_dir(tmp_path: Path):
    """Fixture that sets TODOS_CONFIG env var to use a temporary toml file."""
    config_path = tmp_path / "todos.toml"
    old_value = os.environ.get("TODOS_CONFIG")
    os.environ["TODOS_CONFIG"] = str(config_path)
    try:
        yield tmp_path
    finally:
        if old_value is not None:
            os.environ["TODOS_CONFIG"] = old_value
        else:
            del os.environ["TODOS_CONFIG"]


@pytest.fixture
async def pilot():
    """Pilot fixture for testing the TUI."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        yield pilot
