"""Tests for the Textual TUI interface."""

import pytest
from typing import cast
from textual.widgets import TextArea

from dependent_todos.tui import (
    DependentTodosApp,
    FocusableTabs,
    TaskTable,
    TaskDetails,
    DeleteTaskModal,
    UpdateTaskModal,
)


@pytest.mark.asyncio
async def test_app_starts(temp_dir):
    """Test that the app starts without errors."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # App should start and show header
        assert pilot.app.query_one("Header")


def test_initial_screen_snapshot(temp_dir, snap_compare):
    """Test snapshot of the initial screen."""

    async def run_before(pilot):
        pass  # No actions needed for initial screen

    assert snap_compare("../src/dependent_todos/tui.py", run_before=run_before)


@pytest.mark.asyncio
async def test_refresh_key(temp_dir):
    """Test the refresh key functionality."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press refresh key
        await pilot.press("r")

        # Should still have the table
        table = pilot.app.query_one("#task-table")
        assert table is not None


@pytest.mark.asyncio
async def test_ready_tasks_key(temp_dir):
    """Test the ready tasks key shows notification."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press ready tasks key
        await pilot.press("y")

        # Should show a notification (we can't easily test the content without mocking)


@pytest.mark.asyncio
async def test_navigation_and_focus(temp_dir):
    """Test tab switching and focus navigation with up/down keys."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Add some tasks for table navigation
        from dependent_todos.models import Task

        from datetime import datetime

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
            "task3": Task(
                id="task3",
                message="Task 3",
                dependencies=[],
                status="done",
                cancelled=False,
                started=datetime.now(),
                completed=datetime.now(),
            ),
        }
        # Refresh the table and details with new tasks
        table = cast(TaskTable, pilot.app.query_one("#task-table"))
        table.refresh_data(app.tasks)
        assert table.row_count == 3
        details_widget = cast(TaskDetails, pilot.app.query_one("#task-details"))
        details_widget.tasks = app.tasks
        details_widget.refresh()
        tabs = cast(FocusableTabs, pilot.app.query_one("#filter-tabs"))
        table = pilot.app.query_one("#task-table")
        app_instance = cast(DependentTodosApp, pilot.app)

        # Now test focus switching
        # Initially, tabs are focused
        assert pilot.app.focused == tabs

        # Initially on "All" tab
        assert tabs.active_tab.label.plain == "All"
        assert app_instance.current_filter == "all"
        assert cast(TaskTable, table).row_count == 3  # All tasks displayed

        # Press Tab to next tab
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Todo"
        assert app_instance.current_filter == "todo"
        assert table.row_count == 2  # task1 and task2 are todo (pending state)

        # Press Tab again
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Done"
        assert app_instance.current_filter == "done"
        assert table.row_count == 1  # task3 is done

        # Press Tab again
        await pilot.press("tab")
        assert tabs.active_tab.label.plain == "Pending"
        assert app_instance.current_filter == "pending"
        assert table.row_count == 2  # task1 and task2 are pending/blocked/in-progress

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

        # Test modal interactions: delete modal abort
        # Press 'd' to open delete modal
        await pilot.press("d")
        # Modal should be open
        assert isinstance(pilot.app.screen, DeleteTaskModal)
        # Abort with escape
        await pilot.press("escape")
        # Should be back to main screen
        assert not isinstance(pilot.app.screen, DeleteTaskModal)

        # Test edit modal: open, edit, save
        # Press 'e' to open edit modal
        await pilot.press("e")
        # Modal should be open
        assert isinstance(pilot.app.screen, UpdateTaskModal)
        # TextArea should be focused and have current message
        textarea = cast(TextArea, pilot.app.screen.query_one("TextArea"))
        assert textarea.text == "Task 1"  # current message of task1
        # Edit the message
        textarea.text = "Updated Task 1"
        # Click the ok button to save
        await pilot.click("#ok")
        # Should be back to main screen
        assert not isinstance(pilot.app.screen, UpdateTaskModal)
        # Check table has updated message
        cast(TaskTable, table).refresh_data(app.tasks)  # ensure refreshed
        row_keys = list(cast(TaskTable, table).rows.keys())
        task1_row_key = next(
            row_key
            for row_key in row_keys
            if cast(TaskTable, table).get_row(row_key)[0] == "task1"
        )
        task1_row = cast(TaskTable, table).get_row(task1_row_key)
        assert task1_row[2] == "Updated Task 1"


@pytest.mark.asyncio
async def test_mark_done_key(temp_dir):
    """Test the mark done key functionality."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Add a pending task
        from dependent_todos.models import Task
        from datetime import datetime

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
        }
        # Refresh the table
        table = cast(TaskTable, pilot.app.query_one("#task-table"))
        table.refresh_data(app.tasks)

        # Select the task
        app.current_task_id = "task1"

        # Press mark done key
        await pilot.press("m")

        # Check that the task is marked as done
        task = app.tasks["task1"]
        assert task.status == "done"
        assert task.completed is not None
        # Should be recent timestamp
        assert (datetime.now() - task.completed).total_seconds() < 1


@pytest.mark.asyncio
async def test_topological_order_key(temp_dir):
    """Test the topological order key."""
    app = DependentTodosApp()
    async with app.run_test() as pilot:
        # Press topological order key
        await pilot.press("o")

        # Should show a notification
