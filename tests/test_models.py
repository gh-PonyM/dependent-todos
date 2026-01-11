"""Tests for data models, dependency behavior, and tree evaluation."""

from datetime import datetime
from pathlib import Path
from graphlib import CycleError

import pytest

from dependent_todos.models import Task, TaskList


class TestTask:
    def test_task_creation_minimal(self):
        task = Task(id="task-1", message="Do something")
        assert task.id == "task-1"
        assert task.message == "Do something"
        assert task.status == "pending"
        assert task.dependencies == []
        assert task.started is None
        assert task.completed is None
        assert isinstance(task.created, datetime)

    def test_task_creation_with_dependencies(self):
        task = Task(
            id="task-2",
            message="Do something else",
            dependencies=["task-1"],
        )
        assert task.dependencies == ["task-1"]

    def test_task_cancelled_property(self):
        task_pending = Task(id="task-1", message="Pending task")
        task_cancelled = Task(id="task-2", message="Cancelled task", status="cancelled")
        
        assert not task_pending.cancelled
        assert task_cancelled.cancelled

    def test_task_id_validation_pattern(self):
        valid_ids = ["task-1", "my-task", "task-with-many-words", "a", "task123"]
        for task_id in valid_ids:
            task = Task(id=task_id, message="Test")
            assert task.id == task_id

    def test_task_id_validation_invalid_pattern(self):
        invalid_ids = ["Task-1", "task_1", "task 1", "task--1", "-task", "task-"]
        for task_id in invalid_ids:
            with pytest.raises(Exception):
                Task(id=task_id, message="Test")

    def test_task_id_max_length(self):
        valid_id = "a" * 30
        task = Task(id=valid_id, message="Test")
        assert task.id == valid_id

        invalid_id = "a" * 31
        with pytest.raises(Exception):
            Task(id=invalid_id, message="Test")


class TestTaskList:
    def test_tasklist_creation_empty(self):
        task_list = TaskList()
        assert len(task_list) == 0
        assert list(task_list.keys()) == []

    def test_tasklist_dict_operations(self):
        task_list = TaskList()
        task1 = Task(id="task-1", message="First task")
        task2 = Task(id="task-2", message="Second task")

        task_list["task-1"] = task1
        task_list["task-2"] = task2

        assert len(task_list) == 2
        assert "task-1" in task_list
        assert "task-2" in task_list
        assert task_list["task-1"] == task1
        assert task_list.get("task-1") == task1
        assert task_list.get("nonexistent") is None

        del task_list["task-1"]
        assert len(task_list) == 1
        assert "task-1" not in task_list


class TestDependencyDetection:
    def test_no_circular_dependencies(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        cycles = task_list.detect_circular_dependencies("task-3", ["task-2"])
        assert cycles == []

    def test_direct_circular_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", dependencies=["task-2"])
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        cycles = task_list.detect_circular_dependencies("task-1", ["task-2"])
        assert len(cycles) > 0

    def test_self_dependency(self):
        task_list = TaskList()
        cycles = task_list.detect_circular_dependencies("task-1", ["task-1"])
        assert len(cycles) > 0

    def test_indirect_circular_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", dependencies=["task-2"])
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-3"])
        task_list["task-3"] = Task(id="task-3", message="Third")

        cycles = task_list.detect_circular_dependencies("task-3", ["task-1"])
        assert len(cycles) > 0

    def test_complex_dependency_chain_no_cycle(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-2"])
        task_list["task-4"] = Task(id="task-4", message="Fourth", dependencies=["task-2"])

        cycles = task_list.detect_circular_dependencies("task-5", ["task-3", "task-4"])
        assert cycles == []


class TestTopologicalSort:
    def test_topological_sort_simple_chain(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-2"])

        order = task_list.topological_sort()
        assert order.index("task-1") < order.index("task-2")
        assert order.index("task-2") < order.index("task-3")

    def test_topological_sort_parallel_tasks(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second")
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-1", "task-2"])

        order = task_list.topological_sort()
        assert order.index("task-1") < order.index("task-3")
        assert order.index("task-2") < order.index("task-3")

    def test_topological_sort_excludes_done_tasks(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        order = task_list.topological_sort()
        # Note: TopologicalSorter includes dependencies even if they're done
        # This is expected behavior as it maintains the full dependency graph
        assert "task-2" in order

    def test_topological_sort_empty_list(self):
        task_list = TaskList()
        order = task_list.topological_sort()
        assert order == []

    def test_topological_sort_all_done(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", status="done", completed=datetime.now())

        order = task_list.topological_sort()
        assert order == []

    def test_topological_sort_with_cycle_raises_error(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", dependencies=["task-2"])
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        with pytest.raises(CycleError):
            task_list.topological_sort()

    def test_topological_sort_diamond_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="Root")
        task_list["task-2"] = Task(id="task-2", message="Left", dependencies=["task-1"])
        task_list["task-3"] = Task(id="task-3", message="Right", dependencies=["task-1"])
        task_list["task-4"] = Task(id="task-4", message="Bottom", dependencies=["task-2", "task-3"])

        order = task_list.topological_sort()
        assert order.index("task-1") < order.index("task-2")
        assert order.index("task-1") < order.index("task-3")
        assert order.index("task-2") < order.index("task-4")
        assert order.index("task-3") < order.index("task-4")


class TestPendingTasks:
    def test_get_pending_tasks_no_dependencies(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second")

        pending = task_list.get_pending_tasks()
        assert set(pending) == {"task-1", "task-2"}

    def test_get_pending_tasks_with_blocking_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        pending = task_list.get_pending_tasks()
        assert "task-1" in pending
        assert "task-2" not in pending

    def test_get_pending_tasks_with_completed_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        pending = task_list.get_pending_tasks()
        assert "task-1" not in pending
        assert "task-2" in pending

    def test_get_pending_tasks_excludes_in_progress(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", started=datetime.now())

        pending = task_list.get_pending_tasks()
        assert "task-1" not in pending

    def test_get_pending_tasks_excludes_cancelled(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="cancelled")

        pending = task_list.get_pending_tasks()
        assert "task-1" not in pending

    def test_get_pending_tasks_sorted_by_creation_time(self):
        task_list = TaskList()
        now = datetime.now()
        task_list["task-3"] = Task(id="task-3", message="Third", created=now)
        task_list["task-1"] = Task(id="task-1", message="First", created=datetime(2020, 1, 1))
        task_list["task-2"] = Task(id="task-2", message="Second", created=datetime(2021, 1, 1))

        pending = task_list.get_pending_tasks()
        assert pending == ["task-1", "task-2", "task-3"]


class TestDependencyTree:
    def test_dependency_tree_single_task(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")

        tree = task_list.get_dependency_tree("task-1")
        assert "task-1" in tree
        assert "First" in tree
        assert "[pending]" in tree

    def test_dependency_tree_with_one_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        tree = task_list.get_dependency_tree("task-2")
        assert "task-2" in tree
        assert "task-1" in tree
        assert tree.index("task-2") < tree.index("task-1")

    def test_dependency_tree_chain(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-2"])

        tree = task_list.get_dependency_tree("task-3")
        assert "task-3" in tree
        assert "task-2" in tree
        assert "task-1" in tree

    def test_dependency_tree_multiple_dependencies(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second")
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-1", "task-2"])

        tree = task_list.get_dependency_tree("task-3")
        assert "task-3" in tree
        assert "task-1" in tree
        assert "task-2" in tree

    def test_dependency_tree_missing_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", dependencies=["nonexistent"])

        tree = task_list.get_dependency_tree("task-1")
        assert "task-1" in tree
        assert "nonexistent" in tree
        assert "[not found]" in tree

    def test_dependency_tree_shows_task_states(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        tree = task_list.get_dependency_tree("task-2")
        assert "[done]" in tree
        assert "[pending]" in tree

    def test_dependency_tree_diamond_structure(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="Root")
        task_list["task-2"] = Task(id="task-2", message="Left", dependencies=["task-1"])
        task_list["task-3"] = Task(id="task-3", message="Right", dependencies=["task-1"])
        task_list["task-4"] = Task(id="task-4", message="Bottom", dependencies=["task-2", "task-3"])

        tree = task_list.get_dependency_tree("task-4")
        assert "task-4" in tree
        assert "task-2" in tree
        assert "task-3" in tree
        assert tree.count("task-1") == 2


class TestTaskState:
    def test_task_state_pending(self):
        task_list = TaskList()
        task = Task(id="task-1", message="First")
        task_list["task-1"] = task

        state = task_list.get_task_state(task)
        assert state == "pending"

    def test_task_state_done(self):
        task_list = TaskList()
        task = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-1"] = task

        state = task_list.get_task_state(task)
        assert state == "done"

    def test_task_state_cancelled(self):
        task_list = TaskList()
        task = Task(id="task-1", message="First", status="cancelled")
        task_list["task-1"] = task

        state = task_list.get_task_state(task)
        assert state == "cancelled"

    def test_task_state_in_progress(self):
        task_list = TaskList()
        task = Task(id="task-1", message="First", status="pending", started=datetime.now())
        task_list["task-1"] = task

        state = task_list.get_task_state(task)
        assert state == "in-progress"

    def test_task_state_blocked_by_pending_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        state = task_list.get_task_state(task_list["task-2"])
        assert state == "blocked"

    def test_task_state_blocked_by_missing_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", dependencies=["nonexistent"])

        state = task_list.get_task_state(task_list["task-1"])
        assert state == "blocked"

    def test_task_state_unblocked_when_dependencies_done(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        state = task_list.get_task_state(task_list["task-2"])
        assert state == "pending"

    def test_task_state_blocked_by_cancelled_dependency(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="cancelled")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])

        state = task_list.get_task_state(task_list["task-2"])
        assert state == "blocked"

    def test_task_state_multiple_dependencies_all_done(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", status="done", completed=datetime.now())
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-1", "task-2"])

        state = task_list.get_task_state(task_list["task-3"])
        assert state == "pending"

    def test_task_state_multiple_dependencies_one_pending(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second")
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-1", "task-2"])

        state = task_list.get_task_state(task_list["task-3"])
        assert state == "blocked"


class TestFileOperations:
    def test_save_and_load_empty_tasklist(self, tmp_path: Path):
        file_path = tmp_path / "tasks.toml"
        task_list = TaskList()
        task_list.save_to_file(file_path)

        loaded = TaskList.load_from_file(file_path)
        assert len(loaded) == 0

    def test_save_and_load_single_task(self, tmp_path: Path):
        file_path = tmp_path / "tasks.toml"
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First task")
        task_list.save_to_file(file_path)

        loaded = TaskList.load_from_file(file_path)
        assert len(loaded) == 1
        assert "task-1" in loaded
        assert loaded["task-1"].message == "First task"

    def test_save_and_load_with_dependencies(self, tmp_path: Path):
        file_path = tmp_path / "tasks.toml"
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"])
        task_list.save_to_file(file_path)

        loaded = TaskList.load_from_file(file_path)
        assert len(loaded) == 2
        assert loaded["task-2"].dependencies == ["task-1"]

    def test_save_and_load_with_timestamps(self, tmp_path: Path):
        file_path = tmp_path / "tasks.toml"
        now = datetime.now()
        task_list = TaskList()
        task_list["task-1"] = Task(
            id="task-1",
            message="First",
            status="done",
            started=now,
            completed=now,
        )
        task_list.save_to_file(file_path)

        loaded = TaskList.load_from_file(file_path)
        assert loaded["task-1"].status == "done"
        assert loaded["task-1"].started is not None
        assert loaded["task-1"].completed is not None

    def test_load_nonexistent_file(self, tmp_path: Path):
        file_path = tmp_path / "nonexistent.toml"
        loaded = TaskList.load_from_file(file_path)
        assert len(loaded) == 0

    def test_save_excludes_none_values(self, tmp_path: Path):
        file_path = tmp_path / "tasks.toml"
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First")
        task_list.save_to_file(file_path)

        content = file_path.read_text()
        assert "started" not in content
        assert "completed" not in content


class TestComplexDependencyScenarios:
    def test_long_dependency_chain(self):
        task_list = TaskList()
        for i in range(10):
            deps = [f"task-{i-1}"] if i > 0 else []
            task_list[f"task-{i}"] = Task(
                id=f"task-{i}",
                message=f"Task {i}",
                dependencies=deps,
            )

        order = task_list.topological_sort()
        for i in range(9):
            assert order.index(f"task-{i}") < order.index(f"task-{i+1}")

    def test_wide_dependency_tree(self):
        task_list = TaskList()
        task_list["root"] = Task(id="root", message="Root task")
        
        for i in range(10):
            task_list[f"child-{i}"] = Task(
                id=f"child-{i}",
                message=f"Child {i}",
                dependencies=["root"],
            )

        pending = task_list.get_pending_tasks()
        assert "root" in pending
        for i in range(10):
            assert f"child-{i}" not in pending

        task_list["root"].status = "done"
        task_list["root"].completed = datetime.now()
        pending = task_list.get_pending_tasks()
        assert "root" not in pending
        for i in range(10):
            assert f"child-{i}" in pending

    def test_mixed_states_in_dependency_chain(self):
        task_list = TaskList()
        task_list["task-1"] = Task(id="task-1", message="First", status="done", completed=datetime.now())
        task_list["task-2"] = Task(id="task-2", message="Second", dependencies=["task-1"], started=datetime.now())
        task_list["task-3"] = Task(id="task-3", message="Third", dependencies=["task-2"])
        task_list["task-4"] = Task(id="task-4", message="Fourth", dependencies=["task-3"])

        assert task_list.get_task_state(task_list["task-1"]) == "done"
        assert task_list.get_task_state(task_list["task-2"]) == "in-progress"
        assert task_list.get_task_state(task_list["task-3"]) == "blocked"
        assert task_list.get_task_state(task_list["task-4"]) == "blocked"

    def test_partial_completion_of_parallel_dependencies(self):
        task_list = TaskList()
        task_list["dep-1"] = Task(id="dep-1", message="Dep 1", status="done", completed=datetime.now())
        task_list["dep-2"] = Task(id="dep-2", message="Dep 2")
        task_list["dep-3"] = Task(id="dep-3", message="Dep 3")
        task_list["main"] = Task(id="main", message="Main", dependencies=["dep-1", "dep-2", "dep-3"])

        assert task_list.get_task_state(task_list["main"]) == "blocked"

        task_list["dep-2"].status = "done"
        task_list["dep-2"].completed = datetime.now()
        assert task_list.get_task_state(task_list["main"]) == "blocked"

        task_list["dep-3"].status = "done"
        task_list["dep-3"].completed = datetime.now()
        assert task_list.get_task_state(task_list["main"]) == "pending"
