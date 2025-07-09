from ..controllers.loom_controller import LoomController as LegacyController
from ..services import FreezeSvc, BulkExecSvc, StashCoordinator, RepoStatusService
from ..events.event_bus import EventBus
from ..views.repo_view import RepoView

class LoomController(LegacyController):
    """Thin wrapper integrating new services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.freeze_svc = FreezeSvc()
        self.bulk_exec_svc = BulkExecSvc()
        self.stash_coord = StashCoordinator()
        self.status_svc = RepoStatusService()
        self.events = EventBus()

    def status(self) -> str:
        return "TODO: aggregated status"
    
    def show_details(self) -> None:
        """Show repository details using the new RepoStatusService."""
        repos_config = self.config.load_repos()
        repos = repos_config.get("repos", [])
        if not repos:
            self.console.print("No repositories configured.")
            return

        dev_root = self.config.get_dev_root()
        foundry_dir = self.config.get_foundry_dir()
        if not dev_root:
            self.console.print(
                "Development root not configured. Please run 'loom init' first."
            )
            return

        repo_paths = {
            repo["name"]: repo["path"].replace("$DEV_ROOT", dev_root).replace(
                "$FOUNDRY_DIR", foundry_dir
            )
            for repo in repos
        }

        # Use the new RepoStatusService
        repos_data = self.status_svc.summaries_parallel(repo_paths)
        RepoView(self.console).display_multiple_repos(repos_data)
