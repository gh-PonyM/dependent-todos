"""Tests for the CLI interface."""

import pytest
from pathlib import Path
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
    # Add a task
    result = runner.invoke(
        cli, ["--config", str(temp_config), "add"], input="Test task\n\n"
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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Test task\n\n")

    # List tasks
    result = runner.invoke(cli, ["--config", str(temp_config), "list"])
    assert result.exit_code == 0
    assert "Test task" in result.output
    assert "pending" in result.output


def test_show_task(runner, temp_config):
    """Test showing task details."""
    # Add a task first
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Test task\n\n")

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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Test task\n\n")

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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Test task\n\n")

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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Base task\n\n")

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    result = runner.invoke(
        cli,
        ["--config", str(temp_config), "add"],
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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Base task\n\n")
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add"],
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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Base task\n\n")

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add"],
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
    runner.invoke(cli, ["--config", str(temp_config), "add"], input="Base task\n\n")

    # Add dependent task
    tasks = load_tasks_from_file(temp_config)
    base_id = list(tasks.keys())[0]

    runner.invoke(
        cli,
        ["--config", str(temp_config), "add"],
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
