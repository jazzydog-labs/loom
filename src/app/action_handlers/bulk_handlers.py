"""Bulk execution action handlers."""
from typing import Dict, Any, Optional

from src.app.json_action_router import ActionHandler, ActionResult
from src.services.bulk_exec_svc import BulkExecSvc
from src.app.loom_app import LoomApp


class BulkExecuteHandler(ActionHandler):
    """Handler for bulk command execution."""
    
    def get_action_name(self) -> str:
        return "bulk.execute"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "minLength": 1
                },
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
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
                },
                "shell": {
                    "type": "boolean",
                    "default": True
                },
                "env": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute command across multiple repositories."""
        try:
            # Get parameters
            command = payload["command"]
            repo_patterns = payload.get("repos", ["*"])
            parallel = payload.get("parallel", True)
            continue_on_error = payload.get("continue_on_error", True)
            timeout = payload.get("timeout", 300)
            shell = payload.get("shell", True)
            env = payload.get("env", {})
            
            # Get repos
            app = LoomApp()
            repos = app._resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Execute command
            bulk_svc = BulkExecSvc()
            results = bulk_svc.run(command, repos, parallel=parallel)
            
            # Process results
            success_count = sum(1 for r in results.values() if r.return_code == 0)
            failed_count = len(results) - success_count
            
            # Format results for response
            formatted_results = {}
            for repo, result in results.items():
                formatted_results[repo.name] = {
                    "success": result.return_code == 0,
                    "return_code": result.return_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": result.duration
                }
            
            overall_success = failed_count == 0 or (continue_on_error and success_count > 0)
            
            return ActionResult(
                success=overall_success,
                data={
                    "command": command,
                    "results": formatted_results,
                    "summary": {
                        "total": len(results),
                        "success": success_count,
                        "failed": failed_count
                    }
                },
                error="Some repositories failed" if failed_count > 0 and overall_success else None
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to execute bulk command: {str(e)}",
                error_details={"exception": type(e).__name__}
            )