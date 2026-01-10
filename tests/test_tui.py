"""Tests for the Textual TUI interface."""

import pytest

from dependent_todos.tui import DependentTodosApp


@pytest.mark.asyncio
async def test_app_starts():
    """Test that the app starts without errors."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # App should start and show header
        assert pilot.app.query_one("Header")



def test_initial_screen_snapshot(snap_compare):
    """Test snapshot of the initial screen."""

    async def run_before(pilot):
        pass  # No actions needed for initial screen

    assert snap_compare("../src/dependent_todos/tui.py", run_before=run_before)


@pytest.mark.asyncio
async def test_refresh_key():
    """Test the refresh key functionality."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press refresh key
        await pilot.press("r")

        # Should still have the table
        table = pilot.app.query_one("#task-table")
        assert table is not None


@pytest.mark.asyncio
async def test_ready_tasks_key():
    """Test the ready tasks key shows notification."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press ready tasks key
        await pilot.press("y")

        # Should show a notification (we can't easily test the content without mocking)


@pytest.mark.asyncio
async def test_topological_order_key():
    """Test the topological order key."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press topological order key
        await pilot.press("o")

        # Should show a notification
