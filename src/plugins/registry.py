class PluginRegistry:
    """Registry for repo-specific adapters."""

    def __init__(self):
        self.plugins = {}

    def register(self, name: str, plugin):
        self.plugins[name] = plugin

    def get(self, name: str):
        return self.plugins.get(name)
