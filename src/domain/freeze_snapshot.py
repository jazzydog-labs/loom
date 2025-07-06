from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Dict


@dataclass(frozen=True, slots=True)
class FreezeSnapshot:
    """Immutable snapshot of repo commit SHAs and BOM hash."""

    repos: Dict[str, str] = field(default_factory=dict)
    bom_hash: str = field(default="", init=False)

    def __post_init__(self):  # type: ignore[override]
        # Compute BOM hash deterministically from sorted repo commits
        concatenated = "\n".join(f"{name}:{sha}" for name, sha in sorted(self.repos.items()))
        object.__setattr__(self, "bom_hash", sha256(concatenated.encode()).hexdigest() if concatenated else "")

    # ------------------------------------------------------------------
    # Human-readable helpers
    # ------------------------------------------------------------------
    def describe(self) -> str:
        """Return a human-readable description of the snapshot."""
        count = len(self.repos)
        short_hash = self.bom_hash[:8] if self.bom_hash else ""
        return (
            f"Freeze snapshot capturing {count} repo(s) \u2013 BOM {short_hash}"
            if count
            else "Freeze snapshot (empty)"
        )
