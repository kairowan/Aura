"""Middleware to route diagram requests toward the draw.io skill."""

from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from aura.skills import load_skills

_DIAGRAM_HINT_MARKER = "<diagram_intent>"
_DIRECT_DIAGRAM_KEYWORDS = (
    "draw.io",
    "diagrams.net",
    "flowchart",
    "architecture diagram",
    "sequence diagram",
    "swimlane",
    "topology diagram",
    "uml",
    "er diagram",
    "流程图",
    "架构图",
    "系统图",
    "拓扑图",
    "时序图",
    "泳道图",
    "组织架构图",
    "业务流程图",
    "网络拓扑图",
    "er图",
    "er 图",
)
_DRAW_ACTION_KEYWORDS = ("画", "绘制", "生成", "输出", "做一个", "做一张", "draw", "generate", "create", "make")
_DIAGRAM_TOPIC_KEYWORDS = (
    "流程",
    "架构",
    "时序",
    "泳道",
    "拓扑",
    "组织结构",
    "系统设计",
    "业务流程",
    "流程步骤",
    "sequence",
    "architecture",
    "topology",
    "swimlane",
    "flow",
    "uml",
    "er",
)


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
        return "\n".join(text_parts)
    return ""


def _looks_like_diagram_request(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in _DIRECT_DIAGRAM_KEYWORDS):
        return True
    return any(action in lowered for action in _DRAW_ACTION_KEYWORDS) and any(
        topic in lowered for topic in _DIAGRAM_TOPIC_KEYWORDS
    )


def _get_drawio_skill_path() -> str | None:
    skills = load_skills(enabled_only=True)
    drawio_skill = next((skill for skill in skills if skill.name == "drawio-diagrams"), None)
    if drawio_skill is None:
        return None

    try:
        from aura.config import get_app_config

        container_base_path = get_app_config().skills.container_path
    except Exception:
        container_base_path = "/mnt/skills"

    return drawio_skill.get_container_file_path(container_base_path)


class DiagramIntentMiddleware(AgentMiddleware[AgentState]):
    """Prepend a draw.io-specific execution hint for diagram intents."""

    def _build_hint(self, skill_path: str) -> str:
        return "\n".join(
            [
                _DIAGRAM_HINT_MARKER,
                "Diagram request detected.",
                f"- Immediately read the draw.io skill at: {skill_path}",
                "- Produce a `.drawio` artifact, not Mermaid, unless the user explicitly asks for Mermaid.",
                "- For new diagrams, use the helper generator script from the skill instead of hand-writing raw XML.",
                "- Before presenting the file, validate the generated `.drawio` XML with the validator script from the skill.",
                "</diagram_intent>",
            ]
        )

    @override
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None

        skill_path = _get_drawio_skill_path()
        if not skill_path:
            return None

        last_index = len(messages) - 1
        last_message = messages[last_index]
        if not isinstance(last_message, HumanMessage):
            return None

        original_text = _extract_text(last_message.content)
        if not original_text or _DIAGRAM_HINT_MARKER in original_text:
            return None
        if not _looks_like_diagram_request(original_text):
            return None

        updated_content = f"{self._build_hint(skill_path)}\n\n{original_text}"
        messages[last_index] = HumanMessage(
            content=updated_content,
            id=last_message.id,
            additional_kwargs=last_message.additional_kwargs,
            name=last_message.name,
        )
        return {"messages": messages}
