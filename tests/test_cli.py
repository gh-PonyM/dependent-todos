"""Tests for the CLI interface."""

import pytest
from click.testing import CliRunner

from dependent_todos.main import cli
from dependent_todos.storage import load_tasks_from_file


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path):
    """Temporary config file path."""
    return tmp_path / ".todos.toml"


def test_list_empty(runner, temp_config):
    """Test listing tasks when none exist."""
    result = runner.invoke(cli, ["--config", str(temp_config), "list"])
    assert result.exit_code == 0
    assert "No tasks found." in result.output


def test_add_task(runner, temp_config):
    """Test adding a new task."""
    # Add a task with --no-interactive to avoid menu
    result = runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )
    assert result.exit_code == 0
    assert "added successfully" in result.output

    # Verify it was saved
    tasks = load_tasks_from_file(temp_config)
    assert len(tasks) == 1
    task = list(tasks.values())[0]
    assert task.message == "Test task"
    assert task.status == "pending"


def test_list_with_tasks(runner, temp_config):
    """Test listing tasks when they exist."""
    # Add a task first
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )

    # List tasks
    result = runner.invoke(cli, ["--config", str(temp_config), "list"])
    assert result.exit_code == 0
    assert "Test task" in result.output
    assert "pending" in result.output


def test_show_task(runner, temp_config):
    """Test showing task details."""
    # Add a task first
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )

    # Get the task ID from the tasks
    tasks = load_tasks_from_file(temp_config)
    task_id = list(tasks.keys())[0]

    # Show task details
    result = runner.invoke(cli, ["--config", str(temp_config), "show", task_id])
    assert result.exit_code == 0
    assert task_id in result.output
    assert "Test task" in result.output
    assert "pending" in result.output


def test_done_task(runner, temp_config):
    """Test marking a task as done."""
    # Add a task first
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )

    # Get the task ID
    tasks = load_tasks_from_file(temp_config)
    task_id = list(tasks.keys())[0]

    # Mark as done
    result = runner.invoke(cli, ["--config", str(temp_config), "done", task_id])
    assert result.exit_code == 0
    assert "marked as done" in result.output

    # Verify status changed
    tasks = load_tasks_from_file(temp_config)
    task = tasks[task_id]
    assert task.status == "done"
    assert task.completed is not None


def test_remove_task(runner, temp_config):
    """Test removing a task."""
    # Add a task first
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )

    # Get the task ID
    tasks = load_tasks_from_file(temp_config)
    task_id = list(tasks.keys())[0]
    assert len(tasks) == 1

    # Remove the task
    result = runner.invoke(cli, ["--config", str(temp_config), "remove", task_id])
    assert result.exit_code == 0
    assert "removed" in result.output

    # Verify it was removed
    tasks = load_tasks_from_file(temp_config)
    assert len(tasks) == 0


def test_add_task_with_dependencies(runner, temp_config):
    """Test adding a task with dependencies."""
    # Add base task
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Base task\n\n",
    )

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    result = runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input=f"Dependent task\n\n{base_id}\n",
    )
    assert result.exit_code == 0
    assert "added successfully" in result.output

    # Verify dependency was saved
    tasks = load_tasks_from_file(temp_config)
    dep_task = [t for t in tasks.values() if t.message == "Dependent task"][0]
    assert base_id in dep_task.dependencies


def test_tree_command(runner, temp_config):
    """Test tree command shows dependency structure."""
    # Add tasks with dependencies
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Base task\n\n",
    )
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input=f"Dependent task\n\n{base_id}\n",
    )

    # Test tree command
    result = runner.invoke(cli, ["--config", str(temp_config), "tree"])
    assert result.exit_code == 0
    assert "Base task" in result.output
    assert "Dependent task" in result.output
    assert "└──" in result.output or "├──" in result.output


def test_ready_command(runner, temp_config):
    """Test ready command shows unblocked tasks."""
    # Add base task
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Base task\n\n",
    )

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input=f"Dependent task\n\n{base_id}\n",
    )

    # Test ready command - should show base task
    result = runner.invoke(cli, ["--config", str(temp_config), "ready"])
    assert result.exit_code == 0
    assert "Base task" in result.output
    assert "Dependent task" not in result.output


def test_order_command(runner, temp_config):
    """Test order command shows topological sort."""
    # Add base task
    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Base task\n\n",
    )

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input=f"Dependent task\n\n{base_id}\n",
    )

    # Test order command
    result = runner.invoke(cli, ["--config", str(temp_config), "order"])
    assert result.exit_code == 0
    assert "Base task" in result.output
    assert "Dependent task" in result.output

    # Base task should come before dependent task
    base_pos = result.output.find("Base task")
    dep_pos = result.output.find("Dependent task")
    assert base_pos < dep_pos


def test_add_task_interactive_flag(runner, temp_config):
    """Test add command accepts --interactive flag."""
    # Test with --no-interactive flag (should use manual input)
    result = runner.invoke(
        cli,
        ["--config", str(temp_config), "add", "--no-interactive"],
        input="Test task\n\n",
    )
    assert result.exit_code == 0
    assert "added successfully" in result.output


def test_tui_command_exists(runner, temp_config):
    """Test that tui command exists (doesn't run it due to interactivity)."""
    # Just test that the command is recognized
    result = runner.invoke(cli, ["--config", str(temp_config), "tui", "--help"])
    assert result.exit_code == 0
    assert "Launch the Textual TUI interface" in result.output


def test_add_task_with_circular_dependency_detection(runner, temp_config):
    """Test that circular dependencies are detected in interactive mode."""
    # Add two tasks
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Task A\n\n")
    tasks = load_tasks_from_file(temp_config)
    task_a_id = list(tasks.keys())[0]

    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Task B\n\n")

    # Try to add a task that depends on itself (simulate circular)
    # This is hard to test with the interactive menu, so we'll test the underlying function
    from dependent_todos.dependencies import detect_circular_dependencies

    tasks = load_tasks_from_file(temp_config)
    circular = detect_circular_dependencies(task_a_id, [task_a_id], tasks)
    assert task_a_id in circular


def test_select_dependencies_interactive_empty_tasks():
    """Test interactive dependency selection with no available tasks."""
    from dependent_todos.dependencies import select_dependencies_interactive

    # Test with empty task dict
    result = select_dependencies_interactive({})
    assert result == []


def test_select_dependencies_interactive_exclude_self():
    """Test that tasks exclude themselves from dependency selection."""
    from dependent_todos.dependencies import select_dependencies_interactive
    from dependent_todos.models import Task

    # Create a test task
    task = Task(id="test-task", message="Test task")
    tasks = {"test-task": task}

    # Should return empty since no other tasks available
    result = select_dependencies_interactive(tasks, exclude_task_id="test-task")
    assert result == []
