"""Sanity tests for Repo and Foundry aggregates."""

from src.domain.repo import Repo
from src.domain.foundry import Foundry


def test_repo_status_nonexistent(tmp_path):
    repo = Repo(name="dummy", path=str(tmp_path / "nonexistent"))
    summary = repo.status_summary()
    assert summary["exists"] is False
    assert summary["git"] is False


def test_foundry_summary_and_freeze(monkeypatch):
    # Create stub repos with monkeypatched methods to avoid Git dependencies
    r1 = Repo(name="a", path="/dev/null")
    r2 = Repo(name="b", path="/dev/null")

    monkeypatch.setattr(r1, "status_summary", lambda: {"value": 1})
    monkeypatch.setattr(r1, "head_sha", lambda: "sha1")
    monkeypatch.setattr(r2, "status_summary", lambda: {"value": 2})
    monkeypatch.setattr(r2, "head_sha", lambda: "sha2")

    f = Foundry([r1, r2])
    assert f.summary() == {"a": {"value": 1}, "b": {"value": 2}}

    snap = f.freeze()
    assert snap.repos == {"a": "sha1", "b": "sha2"}
    # BOM hash should be deterministic and non-empty for non-empty repos
    assert len(snap.bom_hash) == 64 