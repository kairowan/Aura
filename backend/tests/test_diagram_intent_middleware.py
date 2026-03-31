from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from aura.agents.middlewares.diagram_intent_middleware import DiagramIntentMiddleware
from aura.skills.types import Skill


def _drawio_skill() -> Skill:
    skill_dir = Path("/tmp/skills/public/drawio-diagrams")
    return Skill(
        name="drawio-diagrams",
        description="draw.io diagrams",
        license=None,
        skill_dir=skill_dir,
        skill_file=skill_dir / "SKILL.md",
        relative_path=Path("drawio-diagrams"),
        category="public",
        enabled=True,
    )


def test_diagram_intent_middleware_injects_hint_for_flowchart_request():
    middleware = DiagramIntentMiddleware()
    state = {
        "messages": [HumanMessage(content="帮我画一个用户注册流程图")],
    }

    with patch(
        "aura.agents.middlewares.diagram_intent_middleware.load_skills",
        return_value=[_drawio_skill()],
    ):
        update = middleware.before_agent(state, runtime=None)  # type: ignore[arg-type]

    assert update is not None
    injected = update["messages"][0]
    assert "drawio-diagrams/SKILL.md" in str(injected.content)
    assert ".drawio" in str(injected.content)


def test_diagram_intent_middleware_injects_hint_without_explicit_drawio_keyword():
    middleware = DiagramIntentMiddleware()
    state = {
        "messages": [HumanMessage(content="请生成一个订单审批架构图")],
    }

    with patch(
        "aura.agents.middlewares.diagram_intent_middleware.load_skills",
        return_value=[_drawio_skill()],
    ):
        update = middleware.before_agent(state, runtime=None)  # type: ignore[arg-type]

    assert update is not None
    assert "<diagram_intent>" in str(update["messages"][0].content)


def test_diagram_intent_middleware_skips_non_diagram_requests():
    middleware = DiagramIntentMiddleware()
    state = {
        "messages": [HumanMessage(content="帮我总结一下这个需求文档")],
    }

    with patch(
        "aura.agents.middlewares.diagram_intent_middleware.load_skills",
        return_value=[_drawio_skill()],
    ):
        assert middleware.before_agent(state, runtime=None) is None  # type: ignore[arg-type]
