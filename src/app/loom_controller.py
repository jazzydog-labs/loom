from ..controllers.loom_controller import LoomController as LegacyController
from ..services import FreezeSvc, BulkExecSvc, StashCoordinator, RepoStatusSvc
from ..events.event_bus import EventBus

class LoomController(LegacyController):
    """Thin wrapper integrating new services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.freeze_svc = FreezeSvc()
        self.bulk_exec_svc = BulkExecSvc()
        self.stash_coord = StashCoordinator()
        self.status_svc = RepoStatusSvc()
        self.events = EventBus()

    def status(self) -> str:
        return "TODO: aggregated status"
