# Loom Configuration

This directory contains configuration files for the loom system.

## Emoji Configuration

The `emojis.yaml` file centralizes all emoji usage across the loom codebase. This provides consistency and makes it easy to update emojis across the entire system.

### Usage

#### In Python Code

```python
from loomlib.emojis import get_emoji_manager

# Get the emoji manager
emoji_mgr = get_emoji_manager()

# Use emojis by category and key
success_emoji = emoji_mgr.get_status('success')  # ✅
error_emoji = emoji_mgr.get_status('error')      # ❌
folder_emoji = emoji_mgr.get_files('folder')     # 📁
loom_emoji = emoji_mgr.get_special('loom')       # 🧵
```

#### Convenience Functions

For common emojis, you can use convenience functions:

```python
from loomlib.emojis import success, error, warning, folder, loom

print(f"{success()} Operation completed")
print(f"{error()} Something went wrong")
print(f"{warning()} Please check your input")
print(f"{folder()} Directory structure")
print(f"{loom()} Loom system")
```

### Categories

The emoji configuration is organized into categories:

- **status**: Success, error, warning, info
- **process**: Loading, running, completed, failed, etc.
- **files**: Folder, file, document, script, config, template
- **git**: Modified, deleted, added, renamed, unmerged, etc.
- **development**: Code, tool, build, test, debug, deploy, package
- **ui**: Progress, spinner, checkmark, cross, arrows
- **special**: Loom-specific emojis like loom, foundry, bootstrap, setup, init

### Updating Emojis

To change an emoji across the entire system:

1. Edit `config/emojis.yaml`
2. Update the emoji value for the desired key
3. All code using that emoji will automatically use the new value

### Generating Shell Scripts

For shell scripts that can't easily read YAML, use the `scripts/generate_bootstrap.sh` script to generate shell scripts with the correct emojis from the config.

### Benefits

- **Consistency**: All emojis are defined in one place
- **Maintainability**: Easy to update emojis across the entire system
- **Type Safety**: Python code gets proper type checking and autocomplete
- **Flexibility**: Easy to add new emoji categories or change existing ones
- **Documentation**: Clear organization and naming conventions 