"""Tests for the Textual TUI interface."""

import pytest
from typing import cast

from dependent_todos.tui import DependentTodosApp, FocusableTabs, TaskTable, TaskDetails


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
async def test_navigation_and_focus():
    """Test tab switching and focus navigation with up/down keys."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Add some tasks for table navigation
        from dependent_todos.models import Task

        app.tasks = {
            "task1": Task(
                id="task1",
                message="Task 1",
                dependencies=[],
                status="pending",
                cancelled=False,
                started=None,
                completed=None,
            ),
            "task2": Task(
                id="task2",
                message="Task 2",
                dependencies=[],
                status="pending",
                cancelled=False,
                started=None,
                completed=None,
            ),
        }
        # Refresh the table and details with new tasks
        table = cast(TaskTable, pilot.app.query_one("#task-table"))
        table.refresh_data(app.tasks)
        assert table.row_count == 2
        details_widget = cast(TaskDetails, pilot.app.query_one("#task-details"))
        details_widget.tasks = app.tasks
        details_widget.refresh()
        tabs = cast(FocusableTabs, pilot.app.query_one("#filter-tabs"))
        table = pilot.app.query_one("#task-table")
        app_instance = cast(DependentTodosApp, pilot.app)

        # Initially on "All" tab
        assert tabs.active_tab.label.plain == "All"
        assert app_instance.current_filter == "all"

        # Press Tab to next tab
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Ready"
        assert app_instance.current_filter == "ready"

        # Press Tab again
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Done"
        assert app_instance.current_filter == "done"

        # Press Tab again
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Pending"
        assert app_instance.current_filter == "pending"

        # Press Tab again to wrap around
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "All"
        assert app_instance.current_filter == "all"

        # Test shift+tab for previous
        await pilot.press("shift+tab")
        assert tabs.active_tab.label.plain == "Pending"
        assert app_instance.current_filter == "pending"

        # Now test focus switching
        # Initially, tabs are focused
        assert pilot.app.focused == tabs

        # Press down to focus table
        await pilot.press("down")
        assert pilot.app.focused == table

        # When table is focused, up/down should navigate (focus stays on table)
        await pilot.press("down")
        assert pilot.app.focused == table
        # After pressing down, cursor should be at row 1, details should show task2
        assert table.cursor_row == 1
        details = pilot.app.query_one("#task-details")
        assert "task2" in str(details.render())
        assert app_instance.current_task_id == "task2"

        await pilot.press("up")
        assert pilot.app.focused == table
        # After pressing up, cursor should be at row 0, details should show task1
        assert table.cursor_row == 0
        assert "task1" in str(details.render())
        assert app_instance.current_task_id == "task1"


@pytest.mark.asyncio
async def test_topological_order_key():
    """Test the topological order key."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press topological order key
        await pilot.press("o")

        # Should show a notification
