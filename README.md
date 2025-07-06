# 🪡 Loom

Loom orchestrates all repositories in the Jazzydog foundry. It clones repos,
coordinates commands, and keeps your development directory organized.

## Quick Start

```bash
git clone git@github.com:jazzydog-labs/loom.git
cd loom
pip install -r requirements.txt
python3 loom.py init --dev-root ~/dev     # add --no-bootstrap to skip extra setup
```

`loom init` clones all repositories listed in `config/repos.yaml` and then
attempts to run the `foundry-bootstrap/bootstrap.sh` script.  The bootstrapper
installs system wide tools (Homebrew, pyenv, etc.) which may not run in
restricted environments.  If the bootstrap step fails you can re-run
`bootstrap.sh` manually or disable it via `--no-bootstrap`.

## Basic Commands

```bash
python3 loom.py init      # set up repositories
python3 loom.py details   # show repository details
python3 loom.py go <repo> # enter a repository
```

## Configuration

- **repos.yaml** – registry of sibling repositories
- **config/defaults.yaml** – default settings
- **~/.loomrc** – optional user overrides

## Directory Layout

After running `loom init`, repositories live under `$DEV_ROOT/foundry/`:

```
foundry/
├── crucible/
├── forge/
├── ledger/
├── vault/
└── loom/
```

## Architecture

`src/main.py` contains only the Typer CLI definitions and forwards all
operations to `LoomController` located in `src/controllers/loom_controller.py`.
The controller coordinates the managers in `src/core` and implements the actual
command logic. This separation keeps the entry point small and the logic
testable.
This repository now includes a skeleton DDD architecture under `src/` with packages like `app`, `services`, `domain`, `infra`, `plugins`, and `events` for future expansion.


## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

[Add your license here]

---

**Loom** – weaving the foundry ecosystem into place. 🧵
