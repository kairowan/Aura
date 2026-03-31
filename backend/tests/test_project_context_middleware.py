from langchain_core.messages import HumanMessage

from aura.agents.middlewares.project_context_middleware import ProjectContextMiddleware


def test_project_context_middleware_injects_bound_project_details():
    middleware = ProjectContextMiddleware()
    state = {
        "messages": [HumanMessage(content="请帮我检查这个项目的入口文件")],
        "thread_data": {
            "project_root_path": "/Users/haonan/Desktop/python/aura",
            "project_mount_path": "/tmp/aura/threads/t1/project",
        },
    }

    update = middleware.before_agent(state, runtime=None)  # type: ignore[arg-type]

    assert update is not None
    injected = update["messages"][0]
    assert isinstance(injected, HumanMessage)
    assert "<project_context>" in str(injected.content)
    assert "/mnt/project" in str(injected.content)


def test_project_context_middleware_skips_when_no_project_bound():
    middleware = ProjectContextMiddleware()
    state = {
        "messages": [HumanMessage(content="hello")],
        "thread_data": {},
    }

    assert middleware.before_agent(state, runtime=None) is None  # type: ignore[arg-type]
