"""Freeze action handlers."""
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.app.json_action_router import ActionHandler, ActionResult
from src.services.freeze_svc import FreezeSvc
from src.domain.repo import Repo
from src.app.loom_app import LoomApp


class FreezeCreateHandler(ActionHandler):
    """Handler for creating freeze snapshots."""
    
    def get_action_name(self) -> str:
        return "freeze.create"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "pattern": "^[a-zA-Z0-9_-]+$"
                },
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
                    "default": False
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9_-]+$"
                    }
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Create a freeze snapshot."""
        try:
            # Get parameters
            name = payload["name"]
            repo_patterns = payload.get("repos", ["*"])
            message = payload.get("message", "")
            include_untracked = payload.get("include_untracked", False)
            tags = payload.get("tags", [])
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Create freeze
            freeze_svc = FreezeSvc()
            snapshot = freeze_svc.create_freeze(repos, name, message)
            
            # Add tags if provided (would need to extend FreezeSvc)
            if tags:
                self.logger.info(f"Tags would be added: {tags}")
            
            return ActionResult(
                success=True,
                data={
                    "name": name,
                    "bom_hash": snapshot.bom_hash,
                    "repo_count": len(snapshot.repos),
                    "message": message,
                    "tags": tags
                }
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to create freeze: {str(e)}",
                error_details={"exception": type(e).__name__}
            )


class FreezeRestoreHandler(ActionHandler):
    """Handler for restoring freeze snapshots."""
    
    def get_action_name(self) -> str:
        return "freeze.restore"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "repos": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "force": {
                    "type": "boolean",
                    "default": False
                },
                "partial": {
                    "type": "boolean",
                    "default": False
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Restore from a freeze snapshot."""
        try:
            # Get parameters
            name = payload["name"]
            repo_patterns = payload.get("repos")
            force = payload.get("force", False)
            partial = payload.get("partial", False)
            
            # Get repos if specified
            repos = None
            if repo_patterns:
                app = LoomApp()
                repos = app._resolve_repos(repo_patterns)
                if not repos and not partial:
                    return ActionResult(
                        success=False,
                        error="No repositories found matching patterns",
                        error_details={"patterns": repo_patterns}
                    )
            
            # Restore freeze
            freeze_svc = FreezeSvc()
            result = freeze_svc.restore_freeze(name, repos)
            
            return ActionResult(
                success=True,
                data={
                    "name": name,
                    "restored_count": result.get("restored_count", 0),
                    "repos": result.get("repos", [])
                }
            )
            
        except FileNotFoundError:
            return ActionResult(
                success=False,
                error=f"Freeze snapshot not found: {name}"
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to restore freeze: {str(e)}",
                error_details={"exception": type(e).__name__}
            )


class FreezeListHandler(ActionHandler):
    """Handler for listing freeze snapshots."""
    
    def get_action_name(self) -> str:
        return "freeze.list"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "created_after": {
                            "type": "string",
                            "format": "date-time"
                        },
                        "created_before": {
                            "type": "string",
                            "format": "date-time"
                        }
                    }
                },
                "sort": {
                    "type": "string",
                    "enum": ["name", "created", "-name", "-created"],
                    "default": "-created"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """List freeze snapshots."""
        try:
            # Get parameters
            filter_opts = payload.get("filter", {})
            sort = payload.get("sort", "-created")
            limit = payload.get("limit", 100)
            
            # List freezes
            freeze_svc = FreezeSvc()
            freezes = freeze_svc.list_freezes()
            
            # Apply filters (simplified for now)
            if filter_opts.get("name_pattern"):
                import re
                pattern = re.compile(filter_opts["name_pattern"])
                freezes = [f for f in freezes if pattern.match(f.get("name", ""))]
            
            # Sort (simplified)
            if sort == "name":
                freezes.sort(key=lambda f: f.get("name", ""))
            elif sort == "-name":
                freezes.sort(key=lambda f: f.get("name", ""), reverse=True)
            # Default is by creation time (would need to be added to freeze data)
            
            # Limit
            freezes = freezes[:limit]
            
            return ActionResult(
                success=True,
                data={
                    "freezes": freezes,
                    "count": len(freezes),
                    "total": len(freeze_svc.list_freezes())
                }
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to list freezes: {str(e)}",
                error_details={"exception": type(e).__name__}
            )