# TODO

## Workflow
- [x] Create a json-based interface to get all todos in a directory, from ./todo.md, and comments with `#todo:` in all code, for a particular repo. this should go in src/infra/todo_manager.py
- [x] Document desired workflows

## Refactoring
- Extract a clean JSON interface
- Run jobs in parallel for each git repository
- Extract color configuration
  - Provide a color schema
  - Allow declarative color selection
- Move configuration settings from Python into files

## Bootstrap
- [ ] Make `foundry-bootstrap/bootstrap.sh` detect unsupported environments and
      skip Homebrew/pyenv installation when running inside a minimal container.
      This will allow `loom init` to succeed in CI or Docker without manual
      intervention.

## Architecture Skeleton
- [x] Integrate new `cli` package with Typer commands
- [x] Wire `app.LoomController` into existing CLI
- [x] Flesh out domain aggregates (`Repo`, `Foundry`, `FreezeSnapshot`)
- [ ] Use existing framework to flesh out a minimal solution for getting all repos to `git pull` in parallel. This may require using GitManager and utils.worker_pool map_parallel
- [ ] Implement services
  - [ ] `RepoStatusSvc`
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
