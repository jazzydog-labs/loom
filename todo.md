# TODO

## Workflow
- [x] Create a json-based interface to get all todos in a directory, from ./todo.md, and comments with `#todo:` in all code, for a particular repo. this should go in src/infra/todo_manager.py
- [x] Document desired workflows

## Architecture Skeleton
- [x] Integrate new `cli` package with Typer commands
- [x] Wire `app.LoomController` into existing CLI
- [x] Flesh out domain aggregates (`Repo`, `Foundry`, `FreezeSnapshot`)
- [x] Use existing framework to flesh out a minimal solution for getting all repos to `git pull` in parallel. This may require using GitManager and utils.worker_pool map_parallel
- [ ] Implement services
  - [ ] Move RepoStatusReader functionality to `RepoStatusSvc` (and rename `RepoStatusSvc` to `RepoStatusService`), making sure everything works (and tests pass).
  - [ ] `BulkExecSvc`
  - [ ] `FreezeSvc`
  - [ ] `StashCoordinator`
- [ ] Infrastructure gateways
  - [ ] `GitGateway` with proper subprocess handling
  - [ ] `FSGateway` for file operations
  - [ ] `ShellGateway` with concurrency limits
  - [ ] `GitCache` for commit graph lookup
  - [ ] `Telemetry` hooks for all services
  - [ ] `PolicyEnforcer` for command vetting
  - [ ] `SecretsManager` to load SSH/GPG keys
  - [ ] `ConcurrencyController` with circuit breakers
  - [ ] `AuthContext` capturing user info
- [ ] Event bus and basic events
  - [ ] `FreezeCreated`
  - [ ] `RepoStatusUpdated`
- [ ] Plugin registry for repo-specific actions
- [ ] Unit of Work pattern across services
- [ ] Persistent freeze snapshots for time-travel


