"""JSON Action Router for unified Loom operations."""
import json
import logging
from typing import Dict, Any, Optional, Type, Callable, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from abc import ABC, abstractmethod

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = ValueError  # Fallback

from src.domain.repo import Repo


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.data is not None:
            result["data"] = self.data
        
        if self.error:
            result["error"] = self.error
            if self.error_details:
                result["error_details"] = self.error_details
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


class ActionHandler(ABC):
    """Base class for action handlers."""
    
    def __init__(self, router: 'JsonActionRouter'):
        self.router = router
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_action_name(self) -> str:
        """Return the action name this handler processes."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this action's payload."""
        pass
    
    @abstractmethod
    def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute the action with given payload and metadata."""
        pass
    
    def validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate payload against schema."""
        schema = self.get_schema()
        if schema and HAS_JSONSCHEMA:
            try:
                validate(instance=payload, schema=schema)
            except ValidationError as e:
                raise ValueError(f"Invalid payload: {e.message if hasattr(e, 'message') else str(e)}")


class JsonActionRouter:
    """Router for JSON-based actions."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """Initialize the router.
        
        Args:
            schema_dir: Directory containing JSON schemas
        """
        self.handlers: Dict[str, ActionHandler] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.schema_dir = schema_dir or Path(__file__).parent.parent.parent / "touchpoints" / "schemas"
        self._load_base_schema()
    
    def _load_base_schema(self) -> None:
        """Load the base action schema."""
        base_schema_path = self.schema_dir / "base.schema.json"
        if base_schema_path.exists():
            with open(base_schema_path, 'r') as f:
                self.base_schema = json.load(f)
        else:
            # Fallback schema if file doesn't exist
            self.base_schema = {
                "type": "object",
                "required": ["action", "version"],
                "properties": {
                    "action": {"type": "string"},
                    "version": {"type": "string"},
                    "payload": {"type": "object"},
                    "metadata": {"type": "object"}
                }
            }
    
    def register_handler(self, handler: ActionHandler) -> None:
        """Register an action handler.
        
        Args:
            handler: The action handler to register
        """
        action_name = handler.get_action_name()
        if action_name in self.handlers:
            raise ValueError(f"Handler for action '{action_name}' already registered")
        
        self.handlers[action_name] = handler
        self.logger.info(f"Registered handler for action: {action_name}")
    
    def register_function(self, action_name: str, func: Callable[[Dict[str, Any]], Any],
                         schema: Optional[Dict[str, Any]] = None) -> None:
        """Register a simple function as an action handler.
        
        Args:
            action_name: Name of the action
            func: Function to execute
            schema: Optional JSON schema for payload validation
        """
        class FunctionHandler(ActionHandler):
            def get_action_name(self) -> str:
                return action_name
            
            def get_schema(self) -> Dict[str, Any]:
                return schema or {}
            
            def execute(self, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> ActionResult:
                try:
                    result = func(payload)
                    return ActionResult(success=True, data=result)
                except Exception as e:
                    return ActionResult(success=False, error=str(e))
        
        self.register_handler(FunctionHandler(self))
    
    def validate_action(self, action_data: Dict[str, Any]) -> None:
        """Validate action against base schema.
        
        Args:
            action_data: The action data to validate
            
        Raises:
            ValueError: If validation fails
        """
        if HAS_JSONSCHEMA:
            try:
                validate(instance=action_data, schema=self.base_schema)
            except ValidationError as e:
                raise ValueError(f"Invalid action format: {e.message if hasattr(e, 'message') else str(e)}")
        else:
            # Basic validation without jsonschema
            if not isinstance(action_data, dict):
                raise ValueError("Action must be a dictionary")
            if "action" not in action_data:
                raise ValueError("Missing required field: action")
            if "version" not in action_data:
                raise ValueError("Missing required field: version")
        
        # Check version
        version = action_data.get("version", "1.0")
        if version != "1.0":
            raise ValueError(f"Unsupported version: {version}")
    
    def execute(self, action_data: Union[str, Dict[str, Any]]) -> ActionResult:
        """Execute an action.
        
        Args:
            action_data: JSON string or dictionary containing the action
            
        Returns:
            ActionResult with execution outcome
        """
        # Parse JSON if string
        if isinstance(action_data, str):
            try:
                action_data = json.loads(action_data)
            except json.JSONDecodeError as e:
                return ActionResult(
                    success=False,
                    error="Invalid JSON",
                    error_details={"parse_error": str(e)}
                )
        
        # Add metadata defaults
        metadata = action_data.get("metadata", {})
        if "request_id" not in metadata:
            metadata["request_id"] = str(uuid.uuid4())
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        try:
            # Validate base structure
            self.validate_action(action_data)
            
            # Get action name
            action_name = action_data["action"]
            
            # Check if handler exists
            if action_name not in self.handlers:
                return ActionResult(
                    success=False,
                    error=f"Unknown action: {action_name}",
                    error_details={"available_actions": list(self.handlers.keys())}
                )
            
            # Get handler
            handler = self.handlers[action_name]
            
            # Get payload
            payload = action_data.get("payload", {})
            
            # Validate payload
            handler.validate_payload(payload)
            
            # Check dry-run
            if metadata.get("dry_run", False):
                return ActionResult(
                    success=True,
                    data={"message": "Dry run - no changes made"},
                    metadata=metadata
                )
            
            # Execute action
            self.logger.info(f"Executing action: {action_name} (request_id: {metadata['request_id']})")
            result = handler.execute(payload, metadata)
            
            # Add metadata to result
            if not result.metadata:
                result.metadata = {}
            result.metadata.update({
                "action": action_name,
                "request_id": metadata["request_id"],
                "duration": (datetime.now(timezone.utc) - datetime.fromisoformat(metadata["timestamp"])).total_seconds()
            })
            
            return result
            
        except ValueError as e:
            return ActionResult(
                success=False,
                error=str(e),
                metadata=metadata
            )
        except Exception as e:
            self.logger.error(f"Unexpected error executing action: {e}", exc_info=True)
            return ActionResult(
                success=False,
                error="Internal error",
                error_details={"exception": str(e)},
                metadata=metadata
            )
    
    def execute_pipeline(self, pipeline_data: Dict[str, Any]) -> ActionResult:
        """Execute a pipeline of actions.
        
        Args:
            pipeline_data: Pipeline definition with actions list
            
        Returns:
            ActionResult with pipeline execution outcome
        """
        actions = pipeline_data.get("actions", [])
        stop_on_error = pipeline_data.get("stop_on_error", True)
        
        results = []
        
        for i, action in enumerate(actions):
            # Add pipeline context to metadata
            if "metadata" not in action:
                action["metadata"] = {}
            action["metadata"]["pipeline_index"] = i
            action["metadata"]["pipeline_id"] = pipeline_data.get("metadata", {}).get("request_id", str(uuid.uuid4()))
            
            result = self.execute(action)
            results.append({
                "action": action.get("action", "unknown"),
                "success": result.success,
                "error": result.error
            })
            
            if not result.success and stop_on_error:
                return ActionResult(
                    success=False,
                    error=f"Pipeline failed at action {i}: {action.get('action')}",
                    data={"results": results},
                    error_details={"failed_action": action, "error": result.error}
                )
        
        return ActionResult(
            success=all(r["success"] for r in results),
            data={"results": results}
        )
    
    def list_actions(self) -> Dict[str, Any]:
        """List all registered actions with their schemas."""
        actions = {}
        for name, handler in self.handlers.items():
            actions[name] = {
                "description": handler.__class__.__doc__ or "No description",
                "schema": handler.get_schema()
            }
        return actions