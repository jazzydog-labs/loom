"""Tests for JSON Action Router."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import uuid

from src.app.json_action_router import JsonActionRouter, ActionHandler, ActionResult
from src.app.action_handlers import (
    FreezeCreateHandler, FreezeRestoreHandler, FreezeListHandler,
    BulkExecuteHandler,
    StashSaveHandler, StashRestoreHandler, StashListHandler,
    RepoStatusHandler, RepoHealthHandler,
    JustRunHandler
)


class TestActionResult:
    """Test ActionResult data class."""
    
    def test_success_result(self):
        """Test successful action result."""
        result = ActionResult(success=True, data={"test": "data"})
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
        
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["data"] == {"test": "data"}
        assert "timestamp" in result_dict
    
    def test_error_result(self):
        """Test error action result."""
        result = ActionResult(
            success=False,
            error="Test error",
            error_details={"code": 404}
        )
        assert result.success is False
        assert result.error == "Test error"
        assert result.error_details == {"code": 404}
        
        result_dict = result.to_dict()
        assert result_dict["success"] is False
        assert result_dict["error"] == "Test error"
        assert result_dict["error_details"] == {"code": 404}
    
    def test_with_metadata(self):
        """Test result with metadata."""
        result = ActionResult(
            success=True,
            data={"test": "data"},
            metadata={"request_id": "123"}
        )
        
        result_dict = result.to_dict()
        assert result_dict["metadata"] == {"request_id": "123"}


class TestActionHandler:
    """Test ActionHandler base class."""
    
    def test_abstract_methods(self):
        """Test that abstract methods must be implemented."""
        router = Mock()
        
        class IncompleteHandler(ActionHandler):
            pass
        
        with pytest.raises(TypeError):
            IncompleteHandler(router)
    
    def test_validate_payload(self):
        """Test payload validation."""
        router = Mock()
        
        class TestHandler(ActionHandler):
            def get_action_name(self):
                return "test.action"
            
            def get_schema(self):
                return {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            
            def execute(self, payload, metadata=None):
                return ActionResult(success=True)
        
        handler = TestHandler(router)
        
        # Valid payload
        handler.validate_payload({"name": "test"})
        
        # Invalid payload - only raises if jsonschema is available
        try:
            import jsonschema
            with pytest.raises(ValueError, match="Invalid payload"):
                handler.validate_payload({"invalid": "field"})
        except ImportError:
            # Skip validation test if jsonschema not available
            pass


class TestJsonActionRouter:
    """Test JsonActionRouter."""
    
    @pytest.fixture
    def router(self, tmp_path):
        """Create a router instance."""
        return JsonActionRouter(schema_dir=tmp_path)
    
    def test_init(self, router):
        """Test router initialization."""
        assert router.handlers == {}
        assert router.base_schema is not None
    
    def test_register_handler(self, router):
        """Test registering handlers."""
        handler = Mock(spec=ActionHandler)
        handler.get_action_name.return_value = "test.action"
        
        router.register_handler(handler)
        assert "test.action" in router.handlers
        assert router.handlers["test.action"] == handler
        
        # Test duplicate registration
        with pytest.raises(ValueError, match="already registered"):
            router.register_handler(handler)
    
    def test_register_function(self, router):
        """Test registering simple functions."""
        def test_func(payload):
            return {"result": payload.get("value", 0) * 2}
        
        router.register_function("test.double", test_func)
        assert "test.double" in router.handlers
        
        # Execute the function
        result = router.execute({
            "action": "test.double",
            "version": "1.0",
            "payload": {"value": 5}
        })
        
        assert result.success is True
        assert result.data == {"result": 10}
    
    def test_validate_action(self, router):
        """Test action validation."""
        # Valid action
        router.validate_action({
            "action": "test.action",
            "version": "1.0"
        })
        
        # Missing required fields
        with pytest.raises(ValueError, match="Missing required field"):
            router.validate_action({
                "action": "test.action"
            })
        
        # Wrong version
        with pytest.raises(ValueError, match="Unsupported version"):
            router.validate_action({
                "action": "test.action",
                "version": "2.0"
            })
    
    def test_execute_unknown_action(self, router):
        """Test executing unknown action."""
        result = router.execute({
            "action": "unknown.action",
            "version": "1.0"
        })
        
        assert result.success is False
        assert "Unknown action" in result.error
        assert "available_actions" in result.error_details
    
    def test_execute_json_string(self, router):
        """Test executing action from JSON string."""
        router.register_function("test.echo", lambda p: p)
        
        result = router.execute('{"action": "test.echo", "version": "1.0", "payload": {"msg": "hello"}}')
        
        assert result.success is True
        assert result.data == {"msg": "hello"}
    
    def test_execute_invalid_json(self, router):
        """Test executing invalid JSON."""
        result = router.execute("invalid json")
        
        assert result.success is False
        assert "Invalid JSON" in result.error
    
    def test_execute_with_metadata(self, router):
        """Test executing with metadata."""
        router.register_function("test.echo", lambda p: p)
        
        result = router.execute({
            "action": "test.echo",
            "version": "1.0",
            "payload": {"msg": "hello"},
            "metadata": {
                "request_id": "custom-id",
                "source": "test"
            }
        })
        
        assert result.success is True
        assert result.metadata["request_id"] == "custom-id"
        assert "duration" in result.metadata
    
    def test_execute_dry_run(self, router):
        """Test dry run execution."""
        mock_handler = Mock(spec=ActionHandler)
        mock_handler.get_action_name.return_value = "test.action"
        mock_handler.validate_payload.return_value = None
        mock_handler.execute.return_value = ActionResult(success=True)
        
        router.register_handler(mock_handler)
        
        result = router.execute({
            "action": "test.action",
            "version": "1.0",
            "metadata": {"dry_run": True}
        })
        
        assert result.success is True
        assert result.data["message"] == "Dry run - no changes made"
        # Handler should not be called in dry run
        mock_handler.execute.assert_not_called()
    
    def test_execute_pipeline(self, router):
        """Test pipeline execution."""
        router.register_function("step1", lambda p: {"step": 1})
        router.register_function("step2", lambda p: {"step": 2})
        
        result = router.execute_pipeline({
            "actions": [
                {"action": "step1", "version": "1.0"},
                {"action": "step2", "version": "1.0"}
            ]
        })
        
        assert result.success is True
        assert len(result.data["results"]) == 2
        assert all(r["success"] for r in result.data["results"])
    
    def test_execute_pipeline_stop_on_error(self, router):
        """Test pipeline stops on error."""
        router.register_function("step1", lambda p: {"step": 1})
        router.register_function("fail", lambda p: 1/0)  # Will raise exception
        router.register_function("step3", lambda p: {"step": 3})
        
        result = router.execute_pipeline({
            "actions": [
                {"action": "step1", "version": "1.0"},
                {"action": "fail", "version": "1.0"},
                {"action": "step3", "version": "1.0"}
            ],
            "stop_on_error": True
        })
        
        assert result.success is False
        assert "Pipeline failed at action 1" in result.error
        assert len(result.data["results"]) == 2  # Only first two executed
    
    def test_list_actions(self, router):
        """Test listing registered actions."""
        router.register_function("test.func", lambda p: p, {"type": "object"})
        
        actions = router.list_actions()
        assert "test.func" in actions
        assert "schema" in actions["test.func"]


class TestFreezeHandlers:
    """Test freeze action handlers."""
    
    @pytest.fixture
    def router(self):
        return Mock(spec=JsonActionRouter)
    
    @patch('src.app.action_handlers.freeze_handlers.resolve_repos')
    @patch('src.app.action_handlers.freeze_handlers.FreezeSvc')
    def test_freeze_create_handler(self, mock_freeze_svc, mock_resolve_repos, router):
        """Test freeze create handler."""
        # Setup mocks
        mock_resolve_repos.return_value = [
            Mock(name="repo1", path="/path/repo1"),
            Mock(name="repo2", path="/path/repo2")
        ]
        
        mock_freeze_instance = Mock()
        mock_freeze_svc.return_value = mock_freeze_instance
        mock_snapshot = Mock(bom_hash="abc123", repos=["repo1", "repo2"])
        mock_freeze_instance.create_freeze.return_value = mock_snapshot
        
        # Create handler
        handler = FreezeCreateHandler(router)
        assert handler.get_action_name() == "freeze.create"
        
        # Execute
        result = handler.execute({
            "name": "test-freeze",
            "repos": ["repo1", "repo2"],
            "message": "Test message"
        })
        
        assert result.success is True
        assert result.data["name"] == "test-freeze"
        assert result.data["bom_hash"] == "abc123"
        assert result.data["repo_count"] == 2
    
    @patch('src.app.action_handlers.freeze_handlers.FreezeSvc')
    def test_freeze_restore_handler(self, mock_freeze_svc, router):
        """Test freeze restore handler."""
        # Setup mocks
        mock_freeze_instance = Mock()
        mock_freeze_svc.return_value = mock_freeze_instance
        mock_freeze_instance.restore_freeze.return_value = {
            "restored_count": 2,
            "repos": ["repo1", "repo2"]
        }
        
        # Create handler
        handler = FreezeRestoreHandler(router)
        assert handler.get_action_name() == "freeze.restore"
        
        # Execute
        result = handler.execute({
            "name": "test-freeze"
        })
        
        assert result.success is True
        assert result.data["restored_count"] == 2
    
    @patch('src.app.action_handlers.freeze_handlers.FreezeSvc')
    def test_freeze_list_handler(self, mock_freeze_svc, router):
        """Test freeze list handler."""
        # Setup mocks
        mock_freeze_instance = Mock()
        mock_freeze_svc.return_value = mock_freeze_instance
        mock_freeze_instance.list_freezes.return_value = [
            {"name": "freeze1", "created": "2024-01-01"},
            {"name": "freeze2", "created": "2024-01-02"}
        ]
        
        # Create handler
        handler = FreezeListHandler(router)
        assert handler.get_action_name() == "freeze.list"
        
        # Execute
        result = handler.execute({})
        
        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["freezes"]) == 2


class TestBulkHandler:
    """Test bulk execution handler."""
    
    @pytest.fixture
    def router(self):
        return Mock(spec=JsonActionRouter)
    
    @patch('src.app.action_handlers.bulk_handlers.resolve_repos')
    @patch('src.app.action_handlers.bulk_handlers.BulkExecSvc')
    def test_bulk_execute_handler(self, mock_bulk_svc, mock_resolve_repos, router):
        """Test bulk execute handler."""
        # Setup mocks
        mock_repos = [
            Mock(name="repo1"),
            Mock(name="repo2")
        ]
        mock_resolve_repos.return_value = mock_repos
        
        mock_bulk_instance = Mock()
        mock_bulk_svc.return_value = mock_bulk_instance
        
        # Mock command results
        mock_result1 = Mock(return_code=0, stdout="output1", stderr="", duration=0.1)
        mock_result2 = Mock(return_code=1, stdout="", stderr="error2", duration=0.2)
        mock_bulk_instance.run.return_value = {
            mock_repos[0]: mock_result1,
            mock_repos[1]: mock_result2
        }
        
        # Create handler
        handler = BulkExecuteHandler(router)
        assert handler.get_action_name() == "bulk.execute"
        
        # Execute
        result = handler.execute({
            "command": "echo test",
            "repos": ["*"],
            "continue_on_error": True
        })
        
        assert result.success is True  # continue_on_error allows partial success
        assert result.data["summary"]["total"] == 2
        assert result.data["summary"]["success"] == 1
        assert result.data["summary"]["failed"] == 1


class TestStashHandlers:
    """Test stash action handlers."""
    
    @pytest.fixture
    def router(self):
        return Mock(spec=JsonActionRouter)
    
    @patch('src.app.action_handlers.stash_handlers.resolve_repos')
    @patch('src.app.action_handlers.stash_handlers.StashCoordinator')
    def test_stash_save_handler(self, mock_stash_coord, mock_resolve_repos, router):
        """Test stash save handler."""
        # Setup mocks
        mock_resolve_repos.return_value = [
            Mock(name="repo1"),
            Mock(name="repo2")
        ]
        
        mock_stash_instance = Mock()
        mock_stash_coord.return_value = mock_stash_instance
        mock_stash_instance.stash_all.return_value = {
            "stashed": ["repo1", "repo2"],
            "failed": []
        }
        
        # Create handler
        handler = StashSaveHandler(router)
        assert handler.get_action_name() == "stash.save"
        
        # Execute
        result = handler.execute({
            "repos": ["*"],
            "message": "Test stash"
        })
        
        assert result.success is True
        assert result.data["summary"]["stashed"] == 2
        assert result.data["summary"]["failed"] == 0