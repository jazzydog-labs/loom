class Repo:
    """Domain aggregate representing a managed repository."""

    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path

    def status(self) -> str:
        return "TODO: repo status"
