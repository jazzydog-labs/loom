"""Handler registry for JSON Action Router.

This module provides a centralized registry of all action handlers
that can be used with the JSON Action Router.
"""

from src.app.json_action_router import JsonActionRouter
from src.app.action_handlers import (
    FreezeCreateHandler,
    FreezeRestoreHandler,
    FreezeListHandler,
    BulkExecuteHandler,
    StashSaveHandler,
    StashRestoreHandler,
    StashListHandler,
    RepoStatusHandler,
    RepoHealthHandler,
    JustRunHandler,
)


def register_all_handlers(router: JsonActionRouter) -> None:
    """Register all available handlers with the router.
    
    Args:
        router: The JsonActionRouter instance to register handlers with
    """
    # Freeze handlers
    router.register_handler(FreezeCreateHandler(router))
    router.register_handler(FreezeRestoreHandler(router))
    router.register_handler(FreezeListHandler(router))
    
    # Bulk execution handler
    router.register_handler(BulkExecuteHandler(router))
    
    # Stash handlers
    router.register_handler(StashSaveHandler(router))
    router.register_handler(StashRestoreHandler(router))
    router.register_handler(StashListHandler(router))
    
    # Repository handlers
    router.register_handler(RepoStatusHandler(router))
    router.register_handler(RepoHealthHandler(router))
    
    # Just handler
    router.register_handler(JustRunHandler(router))


def create_configured_router() -> JsonActionRouter:
    """Create a JsonActionRouter with all handlers registered.
    
    Returns:
        Configured JsonActionRouter instance
    """
    router = JsonActionRouter()
    register_all_handlers(router)
    return router