"""Test configuration and fixtures."""

import pytest
from pathlib import Path

from dependent_todos.tui import DependentTodosApp


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Temporary config file path for testing."""
    return tmp_path / ".todos.toml"


@pytest.fixture
async def pilot():
    """Pilot fixture for testing the TUI."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        yield pilot
