# 🪡 Loom

**The central orchestrator for the foundry ecosystem** - a collection of locally-managed, agent-augmented repositories.

## 🎯 Purpose

Loom acts as the **weaver** that links all sibling repos into a cohesive local development environment. It's responsible for:

- **Cloning, updating, and relocating** repositories
- **Coordinating commands** across all ecosystem repos
- **Self-organizing** the foundry directory structure
- **Bootstrap integration** with foundry-bootstrap

Loom can be run either **before or after** the foundational tooling is bootstrapped via `foundry-bootstrap`, and is designed to bring a fresh system into working state *without requiring manual repo setup*.

## 🏗️ Philosophy

- **Declarative**: Tool and repo structure lives in `repos.yaml` and isn't hardcoded
- **Composable**: Easy to add/remove new repos or orchestration logic
- **Agent-Ready**: Exposes Python APIs, structured logs, and eventual agent hooks
- **Local-First**: Assumes local development first, optional cloud augmentations later
- **Self-aware**: Loom can relocate and organize itself

## 📁 Directory Structure

After running `loom init`, your development environment will be organized as:

```
$DEV_ROOT/foundry/
├── crucible/           # Domain modeling and entity design
├── forge/              # Code generation and scaffolding
├── foundry-bootstrap/  # Foundational tooling setup
├── ledger/             # Session tracking and artifacts
├── vault/              # Secure storage and secrets
└── loom/               # This orchestrator (moved here)
```

## 🚀 Quick Start

### 1. Clone Loom

```bash
git clone git@github.com:jazzydog-labs/loom.git
cd loom
```

### 2. Run Bootstrap (Recommended)

```bash
./bootstrap.sh
```

This will:
- Install Python dependencies
- Run `loom init` to set up the ecosystem
- Execute `foundry-bootstrap` for foundational tooling

### 3. Manual Setup (Alternative)

```bash
# Install dependencies
pip3 install -r requirements.txt

# Initialize the ecosystem
python3 loom.py init
```

## 📖 Usage

### Initialize the Ecosystem

```bash
python3 loom.py init [--dev-root PATH] [--bootstrap/--no-bootstrap]
```

- `--dev-root`: Specify development root directory (default: `~/dev/jazzydog-labs`)
- `--bootstrap`: Run foundry-bootstrap after setup (default: true)
- `--no-bootstrap`: Skip foundry-bootstrap

### Check Repository Status

```bash
python3 loom.py status
```

Shows a table with:
- Repository status (clean/dirty/missing)
- Current branch
- Ahead/behind remote
- Local path

### Pull Latest Changes

```bash
python3 loom.py pull
```

Pulls latest changes for all repositories in parallel.

### Execute Commands

```bash
python3 loom.py exec -- <command>
```

Examples:
```bash
python3 loom.py exec -- git status
python3 loom.py exec -- ls -la
python3 loom.py exec -- python3 --version
```

## ⚙️ Configuration

### Repository Registry

Edit `repos.yaml` to add or modify repositories:

```yaml
repos:
- name: crucible
  url: git@github.com:jazzydog-labs/crucible.git
  path: $DEV_ROOT/foundry/crucible

- name: new-repo
  url: git@github.com:jazzydog-labs/new-repo.git
  path: $DEV_ROOT/foundry/new-repo
```

### User Configuration

Loom stores user configuration in `~/.loomrc`:

```yaml
dev_root: ~/dev/jazzydog-labs
```

### Default Settings

Default configuration is in `config/defaults.yaml`:

```yaml
defaults:
  dev_root: ~/dev/jazzydog-labs
  foundry_dir: foundry
  git_timeout: 30
  parallel_operations: true
  log_level: INFO
```

## 🔧 Development

### Project Structure

```
loom/
├── loom.py                 # Entrypoint CLI
├── repos.yaml              # Config for sibling repos
├── config/
│   └── defaults.yaml       # Default paths, dev_root, etc.
├── scripts/                # Optional helpers
├── loomlib/                # Modular orchestration logic
│   ├── git.py
│   ├── config.py
│   └── repo_manager.py
├── README.md
├── requirements.txt
├── bootstrap.sh
└── .loomrc                 # Optional persistent user config
```

### Adding New Repositories

1. Add the repository to `repos.yaml`:
   ```yaml
   - name: new-repo
     url: git@github.com:jazzydog-labs/new-repo.git
     path: $DEV_ROOT/foundry/new-repo
   ```

2. Run `loom init` to clone the new repository

### Extending Functionality

The modular design makes it easy to extend:

- **Git operations**: Extend `GitManager` in `loomlib/git.py`
- **Configuration**: Extend `ConfigManager` in `loomlib/config.py`
- **Orchestration**: Extend `RepoManager` in `loomlib/repo_manager.py`
- **CLI commands**: Add new commands to `loom.py`

## 🎨 Features

### Rich CLI (Optional)

Loom uses `rich` for beautiful terminal output when available:
- Progress bars with spinners
- Colorized tables
- Interactive prompts
- Fallback to basic output when `rich` isn't installed

### Parallel Operations

Repository operations (pull, status) run in parallel for better performance.

### Self-Relocation

Loom automatically moves itself to the correct location within the foundry ecosystem.

### Bootstrap Integration

Seamless integration with foundry-bootstrap for complete environment setup.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license here]

---

**Loom** - Weaving the foundry ecosystem into place, one repository at a time. 🧵 