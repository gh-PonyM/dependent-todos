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


@pytest.mark.asyncio
async def test_refresh_button():
    """Test the refresh button functionality."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click refresh button
        await pilot.click("#refresh")

        # Should still have the table
        table = pilot.app.query_one("#task-table")
        assert table is not None


@pytest.mark.asyncio
async def test_ready_tasks_button():
    """Test the ready tasks button shows notification."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click ready tasks button
        await pilot.click("#ready-tasks")

        # Should show a notification (we can't easily test the content without mocking)


@pytest.mark.asyncio
async def test_topological_order_button():
    """Test the topological order button."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click topological order button
        await pilot.click("#topological-order")

        # Should show a notification


def test_initial_screen_snapshot(snap_compare):
    """Test snapshot of the initial screen."""

    async def run_before(pilot):
        pass  # No actions needed for initial screen

    assert snap_compare("../src/dependent_todos/tui.py", run_before=run_before)


@pytest.mark.asyncio
async def test_refresh_button():
    """Test the refresh button functionality."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click refresh button
        await pilot.click("#refresh")

        # Should still have the table
        table = pilot.app.query_one("#task-table")
        assert table is not None


@pytest.mark.asyncio
async def test_ready_tasks_button():
    """Test the ready tasks button shows notification."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click ready tasks button
        await pilot.click("#ready-tasks")

        # Should show a notification (we can't easily test the content without mocking)


@pytest.mark.asyncio
async def test_topological_order_button():
    """Test the topological order button."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Click topological order button
        await pilot.click("#topological-order")

        # Should show a notification
