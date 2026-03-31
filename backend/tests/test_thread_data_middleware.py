from pathlib import Path

import pytest
from langgraph.runtime import Runtime

from aura.agents.middlewares.thread_data_middleware import ThreadDataMiddleware


class TestThreadDataMiddleware:
    def test_before_agent_returns_paths_when_thread_id_present_in_context(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)

        result = middleware.before_agent(state={}, runtime=Runtime(context={"thread_id": "thread-123"}))

        assert result is not None
        assert result["thread_data"]["workspace_path"].endswith("threads/thread-123/user-data/workspace")
        assert result["thread_data"]["uploads_path"].endswith("threads/thread-123/user-data/uploads")
        assert result["thread_data"]["outputs_path"].endswith("threads/thread-123/user-data/outputs")

    def test_before_agent_uses_thread_id_from_configurable_when_context_is_none(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context=None)
        monkeypatch.setattr(
            "aura.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-from-config"}},
        )

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert result["thread_data"]["workspace_path"].endswith("threads/thread-from-config/user-data/workspace")
        assert runtime.context is None

    def test_before_agent_uses_thread_id_from_configurable_when_context_missing_thread_id(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context={})
        monkeypatch.setattr(
            "aura.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-from-config"}},
        )

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert result["thread_data"]["uploads_path"].endswith("threads/thread-from-config/user-data/uploads")
        assert runtime.context == {}

    def test_before_agent_raises_clear_error_when_thread_id_missing_everywhere(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        monkeypatch.setattr(
            "aura.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {}},
        )

        with pytest.raises(ValueError, match="Thread ID is required in runtime context or config.configurable"):
            middleware.before_agent(state={}, runtime=Runtime(context=None))

    def test_before_agent_binds_project_root_and_creates_mount(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        project_root = tmp_path / "repo with spaces"
        project_root.mkdir()

        result = middleware.before_agent(
            state={},
            runtime=Runtime(
                context={
                    "thread_id": "thread-123",
                    "project_root": str(project_root),
                }
            ),
        )

        assert result is not None
        thread_data = result["thread_data"]
        assert thread_data["project_root_path"] == str(project_root.resolve())
        assert thread_data["project_mount_path"] is not None
        assert Path(thread_data["project_mount_path"]).exists() or Path(thread_data["project_mount_path"]).is_symlink()

    def test_before_agent_clears_project_binding_when_context_sets_null(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        project_root = tmp_path / "repo"
        project_root.mkdir()

        first = middleware.before_agent(
            state={},
            runtime=Runtime(
                context={
                    "thread_id": "thread-123",
                    "project_root": str(project_root),
                }
            ),
        )

        cleared = middleware.before_agent(
            state=first or {},
            runtime=Runtime(
                context={
                    "thread_id": "thread-123",
                    "project_root": None,
                }
            ),
        )

        assert cleared is not None
        assert cleared["thread_data"]["project_root_path"] is None
        assert cleared["thread_data"]["project_mount_path"] is None
