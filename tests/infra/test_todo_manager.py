"""Tests for src.infra.todo_manager.TodoManager."""

from pathlib import Path
import json

from src.infra.todo_manager import TodoManager


def _write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def test_collect_markdown_and_code(tmp_path):
    # Create a temporary repo-like directory structure
    md = tmp_path / "todo.md"
    _write(md, "- [ ] task A\n- [x] task B\n  - [ ] subtask 1\n    - [ ] leaf\n")

    code_file = tmp_path / "module.py"
    _write(code_file, "#todo: refactor\nprint('hi')  #todo: inline should NOT count\n")

    js_file = tmp_path / "script.js"
    _write(js_file, "//todo: port logic\nconst x = 1; // todo: inline\n")

    mgr = TodoManager(tmp_path)
    items = mgr.collect()

    # Expected TODOs:
    #   4 from markdown (top two + subtask + leaf) + 1 python + 1 js = 6
    assert len(items) == 6

    # Verify subtask has parent_task
    sub = next(i for i in items if isinstance(i, dict) and i.get("description") == "subtask 1")
    assert sub.get("parent_task") == ["task B"]

    leaf = next(i for i in items if isinstance(i, dict) and i.get("description") == "leaf")
    assert leaf.get("parent_task") == ["task B", "subtask 1"]

    # Ensure JSON conversion round-trips correctly.
    json_str = mgr.collect(as_json=True)
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert isinstance(parsed, list)
    assert len(parsed) == 6 