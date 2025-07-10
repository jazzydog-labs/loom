"""Just recipe action handlers."""
from typing import Dict, Any, Optional

from src.app.json_action_router import ActionHandler, ActionResult
from src.app.loom_app import LoomApp


class JustRunHandler(ActionHandler):
    """Handler for running just recipes."""
    
    def get_action_name(self) -> str:
        return "just.run"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["recipe"],
            "properties": {
                "recipe": {
                    "type": "string",
                    "minLength": 1,
                    "description": "The just recipe to run"
                },
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional arguments to pass to the recipe"
                },
                "parallel": {
                    "type": "boolean",
                    "default": True
                },
                "continue_on_error": {
                    "type": "boolean",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3600,
                    "default": 300
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Run a just recipe across repositories."""
        try:
            # Get parameters
            recipe = payload["recipe"]
            repo_patterns = payload.get("repos", ["*"])
            args = payload.get("args", [])
            parallel = payload.get("parallel", True)
            continue_on_error = payload.get("continue_on_error", True)
            timeout = payload.get("timeout", 300)
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Run just recipe
            from src.app.loom_controller import LoomController
            controller = LoomController()
            
            # Build command
            command_parts = [recipe] + args
            
            # Execute across repos
            results = {}
            success_count = 0
            failed_count = 0
            
            for repo in repos:
                try:
                    # Check if repo has justfile
                    justfile_path = repo.path / "justfile"
                    if not justfile_path.exists():
                        justfile_path = repo.path / "Justfile"
                    
                    if not justfile_path.exists():
                        results[repo.name] = {
                            "success": False,
                            "error": "No justfile found",
                            "has_justfile": False
                        }
                        failed_count += 1
                        continue
                    
                    # Run the recipe (simplified - would use bulk service)
                    from src.services.bulk_exec_svc import BulkExecSvc
                    bulk_svc = BulkExecSvc()
                    
                    result = bulk_svc.run(f"just {' '.join(command_parts)}", [repo])
                    cmd_result = result.get(repo, None)
                    
                    if cmd_result and cmd_result.return_code == 0:
                        success_count += 1
                        results[repo.name] = {
                            "success": True,
                            "output": cmd_result.stdout,
                            "duration": cmd_result.duration
                        }
                    else:
                        failed_count += 1
                        results[repo.name] = {
                            "success": False,
                            "error": cmd_result.stderr if cmd_result else "Unknown error",
                            "return_code": cmd_result.return_code if cmd_result else -1
                        }
                        
                except Exception as e:
                    failed_count += 1
                    results[repo.name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            overall_success = failed_count == 0 or (continue_on_error and success_count > 0)
            
            return ActionResult(
                success=overall_success,
                data={
                    "recipe": recipe,
                    "args": args,
                    "results": results,
                    "summary": {
                        "total": len(repos),
                        "success": success_count,
                        "failed": failed_count
                    }
                },
                error="Some repositories failed" if failed_count > 0 and overall_success else None
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to run just recipe: {str(e)}",
                error_details={"exception": type(e).__name__}
            )