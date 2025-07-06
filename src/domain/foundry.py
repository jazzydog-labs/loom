class Foundry:
    """Aggregate representing a collection of repositories."""

    def __init__(self, repos=None):
        self.repos = repos or []

    def summary(self) -> str:
        return "TODO: foundry summary"
