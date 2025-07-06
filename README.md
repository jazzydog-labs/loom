# 🪡 Loom

Loom orchestrates all repositories in the Jazzydog foundry. It clones repos,
coordinates commands, and keeps your development directory organized.

## Quick Start

```bash
git clone git@github.com:jazzydog-labs/loom.git
cd loom
./bootstrap.sh  # installs dependencies and runs `loom init`
```

## Basic Commands

```bash
python3 loom.py init             # clone or update repositories
python3 loom.py status           # show repository status
python3 loom.py pull             # pull the latest changes
python3 loom.py exec -- <cmd>    # run a command in each repo
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

## Development

Run tests with:

```bash
python3 run_tests.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

[Add your license here]

---

**Loom** – weaving the foundry ecosystem into place. 🧵
