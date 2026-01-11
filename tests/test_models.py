"""Tests for dependency behavior and dependency trees in models.py."""

import pytest

from dependent_todos.models import Task, TaskList


@pytest.fixture
def sample_tasklist():
    """Fixture providing a TaskList with some sample tasks."""
    tasks = TaskList()
    tasks["task-a"] = Task(id="task-a", message="Task A", dependencies=[])
    tasks["task-b"] = Task(id="task-b", message="Task B", dependencies=["task-a"])
    tasks["task-c"] = Task(id="task-c", message="Task C", dependencies=["task-b"])
    return tasks


def test_circular_dependency_detection(sample_tasklist):
    """Test that circular dependencies are detected when adding dependencies."""
    # Initially no cycles
    assert sample_tasklist.detect_circular_dependencies("task-d", ["task-c"]) == []

    # Adding a dependency that creates a cycle: task-a depends on task-c
    # This would create: task-a -> task-b -> task-c -> task-a
    cycle_deps = sample_tasklist.detect_circular_dependencies("task-a", ["task-c"])
    assert cycle_deps == ["task-c"]


def test_topological_sort_with_dependencies(sample_tasklist):
    """Test topological sorting orders dependencies correctly."""
    # Add a task with no dependencies
    sample_tasklist["task-d"] = Task(id="task-d", message="Task D", dependencies=[])

    # Get topological order
    order = sample_tasklist.topological_sort()

    # task-d and task-a should come before task-b, task-b before task-c
    task_d_idx = order.index("task-d")
    task_a_idx = order.index("task-a")
    task_b_idx = order.index("task-b")
    task_c_idx = order.index("task-c")

    assert task_d_idx < task_b_idx  # task-d before task-b
    assert task_a_idx < task_b_idx  # task-a before task-b
    assert task_b_idx < task_c_idx  # task-b before task-c


def test_dependency_tree_visualization(sample_tasklist):
    """Test that dependency tree generates correct string representation."""
    tree = sample_tasklist.get_dependency_tree("task-c")

    # Check that the tree contains the expected structure
    lines = tree.strip().split("\n")
    assert len(lines) == 3  # task-c, task-b, task-a

    # First line should be task-c
    assert "task-c: Task C" in lines[0]
    # Second line should be task-b
    assert "task-b: Task B" in lines[1]
    # Third line should be task-a
    assert "task-a: Task A" in lines[2]

    # Check tree structure with proper prefixes
    assert lines[0].startswith("└── task-c:")
    assert "    └── task-b:" in lines[1]  # task-b is the only child of task-c
    assert "        └── task-a:" in lines[2]  # task-a is the only child of task-b
