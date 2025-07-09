from src.domain.freeze_snapshot import FreezeSnapshot
from src.services.freeze_svc import FreezeSvc
from src.services.bulk_exec_svc import BulkExecSvc
from src.services.stash_coordinator import StashCoordinator
from src.services.repo_status_service import RepoStatusService
from src.events.event_bus import EventBus
from src.infra.telemetry import Telemetry
from src.infra.git_cache import GitCache
from src.infra.git_gateway import GitGateway
from src.infra.fs_gateway import FSGateway
from src.infra.shell_gateway import ShellGateway
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
    # FreezeSvc now requires repos parameter and returns FreezeSnapshot
    from src.domain.repo import Repo
    freeze_svc = FreezeSvc()
    repos = [Repo(name="test-repo", path=".")]
    result = freeze_svc.create_freeze(repos, "v1")
    assert isinstance(result, FreezeSnapshot)
    
    # BulkExecSvc now returns CommandResult objects
    bulk_svc = BulkExecSvc()
    # Test with empty repos list (should return empty dict)
    results = bulk_svc.run("ls", repos=[])
    assert isinstance(results, dict)
    assert len(results) == 0
    
    # StashCoordinator now requires repos parameter
    coord = StashCoordinator()
    stash_result = coord.stash_all([])
    assert isinstance(stash_result, dict)
    assert "stashed" in stash_result
    
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
    
    # GitGateway now returns a dict with command results
    from unittest.mock import patch
    with patch.object(GitGateway, '_find_git_executable', return_value='/usr/bin/git'):
        git_gateway = GitGateway()
    result = git_gateway.run(['--version'], check=False)
    assert isinstance(result, dict)
    assert 'command' in result
    
    # FSGateway now provides comprehensive file operations
    fs_gateway = FSGateway()
    # Test basic functionality
    assert hasattr(fs_gateway, 'read_text')
    assert hasattr(fs_gateway, 'write_text')
    assert hasattr(fs_gateway, 'exists')
    
    # ShellGateway provides secure shell command execution
    shell_gateway = ShellGateway()
    result = shell_gateway.execute("echo test")
    assert hasattr(result, 'success')
    assert hasattr(result, 'stdout')
    assert hasattr(result, 'stderr')
    assert result.success is True
    assert "test" in result.stdout
    
    assert PolicyEnforcer().check("cmd") == "TODO: check policy for cmd"
    assert SecretsManager().load() == "TODO: load secrets"
    assert ConcurrencyController().run_limited(lambda: None) == "TODO: run with concurrency limits"
    assert AuthContext().current_user() == "TODO: identify user"
