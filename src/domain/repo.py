from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

from git import Repo as GitRepo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError


@dataclass
class Repo:
    """Domain aggregate representing a managed Git repository."""

    name: str
    path: str

    # Internal GitPython repo instance – populated lazily
    _repo: Optional[GitRepo] = None

    # ---------------------------------------------------------------------
    # Lazy helpers
    # ---------------------------------------------------------------------
    def _ensure_repo(self) -> Optional[GitRepo]:
        if self._repo is not None:
            return self._repo

        try:
            self._repo = GitRepo(Path(self.path).expanduser().resolve())
        except (InvalidGitRepositoryError, NoSuchPathError):
            self._repo = None
        return self._repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def head_sha(self) -> Optional[str]:
        repo = self._ensure_repo()
        return repo.head.commit.hexsha if repo else None

    def branch(self) -> Optional[str]:
        repo = self._ensure_repo()
        if not repo:
            return None
        try:
            return repo.active_branch.name
        except TypeError:
            # Detached HEAD
            return None

    def is_dirty(self, *, include_untracked: bool = True) -> bool:
        repo = self._ensure_repo()
        return repo.is_dirty(untracked_files=include_untracked) if repo else False

    def ahead_behind(self) -> tuple[int, int]:
        """Return (ahead, behind) counts relative to upstream."""
        repo = self._ensure_repo()
        if not repo:
            return 0, 0
        try:
            ahead = len(list(repo.iter_commits("@{u}..")))
            behind = len(list(repo.iter_commits("..@{u}")))
            return ahead, behind
        except GitCommandError:
            return 0, 0

    def status_summary(self) -> Dict[str, object]:
        repo = self._ensure_repo()
        if not repo:
            return {"exists": False, "git": False}

        ahead, behind = self.ahead_behind()
        return {
            "branch": self.branch(),
            "head": self.head_sha(),
            "dirty": self.is_dirty(),
            "ahead": ahead,
            "behind": behind,
        }

    # Convenience dunder helpers ------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Repo {self.name} at {self.path}>"
