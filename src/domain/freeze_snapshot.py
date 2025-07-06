from dataclasses import dataclass, field
from typing import Dict

@dataclass
class FreezeSnapshot:
    """Immutable snapshot of repo commit SHAs and BOM hash."""
    repos: Dict[str, str] = field(default_factory=dict)
    bom_hash: str = ""

    def describe(self) -> str:
        """Return human description."""
        return f"TODO: implement description for {len(self.repos)} repos"
