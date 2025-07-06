from __future__ import annotations

from typing import Dict, List
from hashlib import sha256

from .repo import Repo
from .freeze_snapshot import FreezeSnapshot


class Foundry:
    """Aggregate representing a collection of repositories under management."""

    def __init__(self, repos: List[Repo] | None = None):
        self._repos: Dict[str, Repo] = {r.name: r for r in repos} if repos else {}

    # ------------------------------------------------------------------
    # Repo management helpers
    # ------------------------------------------------------------------
    def add_repo(self, repo: Repo) -> None:
        self._repos[repo.name] = repo

    def get_repo(self, name: str) -> Repo | None:
        return self._repos.get(name)

    def all_repos(self) -> List[Repo]:
        return list(self._repos.values())

    # ------------------------------------------------------------------
    # Aggregate insights
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Dict[str, object]]:
        """Return status summaries for every repo in parallel."""
        from ..utils.worker_pool import map_parallel  # local import to avoid heavy top-level dependency

        names_paths = list(self._repos.items())

        def worker(item: tuple[str, Repo]):
            name, repo = item
            return name, repo.status_summary()

        results = map_parallel(worker, names_paths, preserve_order=False)
        return {name: summary for name, summary in results}

    def freeze(self) -> FreezeSnapshot:
        """Produce an immutable snapshot (commit SHA) for every repo."""
        from ..utils.worker_pool import map_parallel

        # Gather commit SHAs in parallel
        commits_list = map_parallel(lambda kv: (kv[0], kv[1].head_sha() or ""), self._repos.items(), preserve_order=False)
        commits = dict(commits_list)

        concatenated = "\n".join(f"{n}:{sha}" for n, sha in sorted(commits.items()))
        # FreezeSnapshot will compute BOM hash in __post_init__
        return FreezeSnapshot(repos=commits)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Foundry {len(self._repos)} repos>"
