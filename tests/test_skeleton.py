from src.domain.freeze_snapshot import FreezeSnapshot
from src.services.freeze_svc import FreezeSvc
from src.services.bulk_exec_svc import BulkExecSvc
from src.services.stash_coordinator import StashCoordinator
from src.services.repo_status_service import RepoStatusService
from src.events.event_bus import EventBus
from src.infra.telemetry import Telemetry
from src.infra.git_cache import GitCache
from src.infra.policy_enforcer import PolicyEnforcer
from src.infra.secrets_manager import SecretsManager
from src.infra.concurrency_controller import ConcurrencyController
from src.infra.auth_context import AuthContext


def test_freeze_snapshot():
    snap = FreezeSnapshot()
    # Empty snapshot should report no repos and blank BOM hash
    assert snap.describe().startswith("Freeze snapshot")
    assert snap.bom_hash == ""


def test_services():
    assert FreezeSvc().create_freeze("v1") == "TODO: create freeze for v1"
    
    # BulkExecSvc now returns CommandResult objects
    bulk_svc = BulkExecSvc()
    # Test with empty repos list (should return empty dict)
    results = bulk_svc.run("ls", repos=[])
    assert isinstance(results, dict)
    assert len(results) == 0
    
    coord = StashCoordinator()
    assert coord.stash_all() == "TODO: stash all"
    
    # RepoStatusService now returns a dict with repo status
    status_svc = RepoStatusService()
    result = status_svc.status(".")
    assert isinstance(result, dict)
    assert "repo_status" in result or "error" in result.get("repo_status", {})


def test_event_bus():
    bus = EventBus()
    called = []
    bus.subscribe("test", lambda p: called.append(p))
    bus.publish("test", 1)
    assert called == [1]


def test_cross_cutting():
    assert Telemetry().log("msg") == "TODO: log msg"
    assert GitCache().get("repo") == "TODO: cached data for repo"
    assert PolicyEnforcer().check("cmd") == "TODO: check policy for cmd"
    assert SecretsManager().load() == "TODO: load secrets"
    assert ConcurrencyController().run_limited(lambda: None) == "TODO: run with concurrency limits"
    assert AuthContext().current_user() == "TODO: identify user"
