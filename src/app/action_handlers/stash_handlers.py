"""Stash action handlers."""
from typing import Dict, Any, Optional

from src.app.json_action_router import ActionHandler, ActionResult
from src.services.stash_coordinator import StashCoordinator
from src.app.loom_app import LoomApp


class StashSaveHandler(ActionHandler):
    """Handler for saving stashes."""
    
    def get_action_name(self) -> str:
        return "stash.save"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "message": {
                    "type": "string",
                    "maxLength": 500
                },
                "include_untracked": {
                    "type": "boolean",
                    "default": True
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Save stashes across repositories."""
        try:
            # Get parameters
            repo_patterns = payload.get("repos", ["*"])
            message = payload.get("message", "Stash via JSON action")
            include_untracked = payload.get("include_untracked", True)
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Save stashes
            stash_coord = StashCoordinator()
            result = stash_coord.stash_all(repos, message)
            
            stashed = result.get("stashed", [])
            failed = result.get("failed", [])
            
            return ActionResult(
                success=len(failed) == 0,
                data={
                    "stashed": stashed,
                    "failed": failed,
                    "summary": {
                        "total": len(repos),
                        "stashed": len(stashed),
                        "failed": len(failed)
                    }
                },
                error="Some repositories failed to stash" if failed else None
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to save stashes: {str(e)}",
                error_details={"exception": type(e).__name__}
            )


class StashRestoreHandler(ActionHandler):
    """Handler for restoring stashes."""
    
    def get_action_name(self) -> str:
        return "stash.restore"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "index": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0
                },
                "apply": {
                    "type": "boolean",
                    "default": False,
                    "description": "Apply stash without removing it"
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Restore stashes across repositories."""
        try:
            # Get parameters
            repo_patterns = payload.get("repos", ["*"])
            index = payload.get("index", 0)
            apply_only = payload.get("apply", False)
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Restore stashes
            stash_coord = StashCoordinator()
            result = stash_coord.restore_all(repos, index)
            
            restored = result.get("restored", [])
            failed = result.get("failed", [])
            
            return ActionResult(
                success=len(failed) == 0,
                data={
                    "restored": restored,
                    "failed": failed,
                    "summary": {
                        "total": len(repos),
                        "restored": len(restored),
                        "failed": len(failed)
                    }
                },
                error="Some repositories failed to restore" if failed else None
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to restore stashes: {str(e)}",
                error_details={"exception": type(e).__name__}
            )


class StashListHandler(ActionHandler):
    """Handler for listing stashes."""
    
    def get_action_name(self) -> str:
        return "stash.list"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "verbose": {
                    "type": "boolean",
                    "default": False
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """List stashes across repositories."""
        try:
            # Get parameters
            repo_patterns = payload.get("repos", ["*"])
            verbose = payload.get("verbose", False)
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # List stashes
            stash_coord = StashCoordinator()
            result = stash_coord.list_all(repos)
            
            stashes = result.get("stashes", {})
            
            # Format results
            formatted_stashes = {}
            total_stashes = 0
            
            for repo_name, stash_list in stashes.items():
                if verbose:
                    formatted_stashes[repo_name] = stash_list
                else:
                    formatted_stashes[repo_name] = len(stash_list)
                total_stashes += len(stash_list)
            
            return ActionResult(
                success=True,
                data={
                    "stashes": formatted_stashes,
                    "summary": {
                        "total_repos": len(stashes),
                        "total_stashes": total_stashes,
                        "repos_with_stashes": sum(1 for s in stashes.values() if s)
                    }
                }
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to list stashes: {str(e)}",
                error_details={"exception": type(e).__name__}
            )