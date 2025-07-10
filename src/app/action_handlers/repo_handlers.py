"""Repository action handlers."""
from typing import Dict, Any, Optional

from src.app.json_action_router import ActionHandler, ActionResult
from src.services.repo_status_service import RepoStatusService
from src.app.repo_utils import resolve_repos


class RepoStatusHandler(ActionHandler):
    """Handler for repository status."""
    
    def get_action_name(self) -> str:
        return "repo.status"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "detailed": {
                    "type": "boolean",
                    "default": False
                },
                "include": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["branch", "status", "remotes", "stash", "tags"]
                    },
                    "default": ["branch", "status"]
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Get repository status."""
        try:
            # Get parameters
            repo_patterns = payload.get("repos", ["*"])
            detailed = payload.get("detailed", False)
            include = payload.get("include", ["branch", "status"])
            
            # Get repos
            repos = resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Get status for each repo
            status_svc = RepoStatusService()
            results = {}
            errors = []
            
            for repo in repos:
                try:
                    status = status_svc.status(repo.path)
                    results[repo.name] = status
                except Exception as e:
                    errors.append({
                        "repo": repo.name,
                        "error": str(e)
                    })
            
            return ActionResult(
                success=len(errors) == 0,
                data={
                    "repositories": results,
                    "summary": {
                        "total": len(repos),
                        "success": len(results),
                        "failed": len(errors)
                    }
                },
                error="Some repositories failed" if errors else None,
                error_details={"errors": errors} if errors else None
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to get repository status: {str(e)}",
                error_details={"exception": type(e).__name__}
            )


class RepoHealthHandler(ActionHandler):
    """Handler for repository health checks."""
    
    def get_action_name(self) -> str:
        return "repo.health"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["*"]
                },
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "uncommitted_changes",
                            "unpushed_commits",
                            "untracked_files",
                            "merge_conflicts",
                            "large_files",
                            "stale_branches"
                        ]
                    },
                    "default": [
                        "uncommitted_changes",
                        "unpushed_commits",
                        "untracked_files"
                    ]
                },
                "thresholds": {
                    "type": "object",
                    "properties": {
                        "large_file_size_mb": {
                            "type": "number",
                            "default": 100
                        },
                        "stale_branch_days": {
                            "type": "integer",
                            "default": 30
                        }
                    }
                }
            }
        }
    
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Check repository health."""
        try:
            # Get parameters
            repo_patterns = payload.get("repos", ["*"])
            checks = payload.get("checks", ["uncommitted_changes", "unpushed_commits", "untracked_files"])
            thresholds = payload.get("thresholds", {})
            
            # Get repos
            repos = resolve_repos(repo_patterns)
            
            if not repos:
                return ActionResult(
                    success=False,
                    error="No repositories found matching patterns",
                    error_details={"patterns": repo_patterns}
                )
            
            # Run health checks
            results = {}
            unhealthy_count = 0
            
            for repo in repos:
                health_issues = []
                
                # Run basic health checks (simplified)
                status_svc = RepoStatusService()
                try:
                    status = status_svc.status(repo.path)
                    repo_status = status.get("repo_status", {})
                    
                    if "uncommitted_changes" in checks:
                        if repo_status.get("has_changes", False):
                            health_issues.append({
                                "check": "uncommitted_changes",
                                "severity": "warning",
                                "message": "Repository has uncommitted changes"
                            })
                    
                    if "untracked_files" in checks:
                        if repo_status.get("untracked_count", 0) > 0:
                            health_issues.append({
                                "check": "untracked_files",
                                "severity": "info",
                                "message": f"Repository has {repo_status['untracked_count']} untracked files"
                            })
                    
                    results[repo.name] = {
                        "healthy": len(health_issues) == 0,
                        "issues": health_issues
                    }
                    
                    if health_issues:
                        unhealthy_count += 1
                        
                except Exception as e:
                    results[repo.name] = {
                        "healthy": False,
                        "issues": [{
                            "check": "error",
                            "severity": "error",
                            "message": f"Failed to check health: {str(e)}"
                        }]
                    }
                    unhealthy_count += 1
            
            return ActionResult(
                success=True,
                data={
                    "repositories": results,
                    "summary": {
                        "total": len(repos),
                        "healthy": len(repos) - unhealthy_count,
                        "unhealthy": unhealthy_count,
                        "checks_performed": checks
                    }
                }
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to check repository health: {str(e)}",
                error_details={"exception": type(e).__name__}
            )