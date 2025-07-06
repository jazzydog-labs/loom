class FreezeCreated:
    def __init__(self, freeze_id: str):
        self.freeze_id = freeze_id

class RepoStatusUpdated:
    def __init__(self, repo: str):
        self.repo = repo
