"""Todo discovery manager for a repository.

Scans a given *root* directory for two types of TODO items and returns them
in a JSON-serialisable structure (a list of dictionaries):

1. Markdown checklist items inside any file named ``todo.md`` (case-insensitive).
   Lines that match the GitHub-style pattern ``- [ ]`` or ``- [x]`` are
   interpreted as unchecked/checked tasks respectively.
2. In-code comments containing the marker ``#todo:`` (case-insensitive). The
   text following the marker on that line becomes the task description.

The resulting task dictionaries have the following fields:

* ``description`` – Human-readable task text (str)
* ``status``      – ``"todo"`` | ``"done"``
* ``source``      – ``"markdown"`` | ``"code"``
* ``path``        – File path relative to *root* (str)
* ``line``        – One-indexed line number where the task was found (int)

Example::

    >>> mgr = TodoManager("/path/to/repo")
    >>> tasks = mgr.collect()
    >>> print(json.dumps(tasks, indent=2))

This module purposefully lives in *infra* because it talks directly to the
filesystem; higher-level packages (e.g. *services*) should depend on this
interface instead of re-implementing their own file scans.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Union

# Regex patterns compiled once at import time for efficiency
_MD_CHECKBOX = re.compile(r"^\s*-\s*\[\s*([xX ])?\s*\]\s*(.*)")
# Comment TODOs must appear at the *start* of the line (ignoring leading
# whitespace) and be preceded by a language comment token ("#" for Python, "//"
# for C-style languages). This avoids matching inline occurrences like
# ``x = 1  #todo``.
#
# Pattern breakdown:
#   ^\s*          – optional leading whitespace
#   (?:#|//)      – comment token
#   \s*           – optional whitespace
#   todo          – literal "todo" (case-insensitive)
#   :?            – optional colon
#   \s*(.*)       – capture description
_CODE_TODO = re.compile(r"^\s*(?:#|//)todo:?\s*(.*)", re.IGNORECASE)

__all__ = ["TodoManager"]


class TodoManager:
    """Aggregate TODO items inside *root* directory."""

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root).expanduser().resolve()

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def collect(self, *, as_json: bool = False) -> Union[List[Dict[str, object]], str]:
        """Return TODO items found under *root*.

        Args:
            as_json: If ``True`` the function returns an *indented* JSON string
                      instead of the raw Python structure.
        """
        todos: List[Dict[str, object]] = []

        # 1. Markdown TODOs -------------------------------------------------
        for md_file in self._markdown_files():
            todos.extend(self._parse_markdown(md_file))

        # 2. In-code #todo: comments ---------------------------------------
        for code_file in self._code_files():
            todos.extend(self._parse_code_comments(code_file))

        return json.dumps(todos, indent=2) if as_json else todos

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _markdown_files(self) -> List[Path]:
        """Return all *todo.md* files under *root* (case-insensitive)."""
        return [p for p in self.root.rglob("todo.md") if p.is_file()]

    def _code_files(self) -> List[Path]:
        """Return candidate source files that may contain ``#todo:`` comments."""
        # Simple heuristic: anything with a common text-based extension.
        exts = {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".sh",
            ".bash",
            ".zsh",
            ".go",
            ".rb",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".java",
            ".kt",
            ".swift",
            ".md",  # Other markdown files may contain inline TODOs
        }
        return [
            p
            for p in self.root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in exts
            and p.name.lower() not in {"todo.md"}
        ]

    def _parse_markdown(self, path: Path) -> List[Dict[str, object]]:
        """Extract checklist TODOs from *path* (a markdown file)."""
        todos: List[Dict[str, object]] = []
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return todos  # pragma: no cover – unreadable file

        # Track nested list hierarchy using indentation width (spaces before dash)
        parent_stack: list[tuple[int, str]] = []  # (indent, description)

        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _MD_CHECKBOX.match(line)
            if not match:
                continue

            leading_spaces = len(line) - len(line.lstrip(" "))
            status_char, desc = match.groups()
            desc = desc.strip()

            # Adjust stack to current indentation level
            while parent_stack and parent_stack[-1][0] >= leading_spaces:
                parent_stack.pop()

            parent_tasks = [d for (_, d) in parent_stack]

            todos.append(
                {
                    "description": desc,
                    "status": "done" if (status_char or "").lower() == "x" else "todo",
                    "source": "markdown",
                    "path": str(path.relative_to(self.root)),
                    "line": lineno,
                    **({"parent_task": parent_tasks} if parent_tasks else {}),
                }
            )

            # Push current as potential parent for deeper indents
            parent_stack.append((leading_spaces, desc))
        return todos

    def _parse_code_comments(self, path: Path) -> List[Dict[str, object]]:
        """Extract ``#todo:`` comments from *path* (source file)."""
        todos: List[Dict[str, object]] = []
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return todos  # pragma: no cover – binary or unreadable file

        for lineno, line in enumerate(text.splitlines(), start=1):
            m = _CODE_TODO.search(line)
            if m:
                desc = m.group(1).strip()
                if desc:  # Ignore empty descriptions
                    todos.append(
                        {
                            "description": desc,
                            "status": "todo",
                            "source": "code",
                            "path": str(path.relative_to(self.root)),
                            "line": lineno,
                        }
                    )
        return todos 