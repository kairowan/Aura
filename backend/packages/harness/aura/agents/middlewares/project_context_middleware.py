"""Middleware to inject the thread-bound project root into the latest user message."""

from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from aura.agents.thread_state import ThreadDataState

_PROJECT_CONTEXT_MARKER = "<project_context>"


class ProjectContextMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    thread_data: NotRequired[ThreadDataState | None]


class ProjectContextMiddleware(AgentMiddleware[ProjectContextMiddlewareState]):
    """Inject project binding details into the latest human message for the agent."""

    state_schema = ProjectContextMiddlewareState

    def _build_project_context(self, project_root: str) -> str:
        return "\n".join(
            [
                _PROJECT_CONTEXT_MARKER,
                "A local project directory is bound to this thread.",
                f"- Host path: {project_root}",
                "- Sandbox path: /mnt/project",
                "- Treat /mnt/project as the primary codebase for this conversation.",
                "- Read, search, and edit project files via /mnt/project instead of asking the user to upload the repo.",
                "</project_context>",
            ]
        )

    @override
    def before_agent(self, state: ProjectContextMiddlewareState, runtime: Runtime) -> dict | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None

        thread_data = state.get("thread_data") or {}
        project_root = thread_data.get("project_root_path")
        if not project_root:
            return None

        last_index = len(messages) - 1
        last_message = messages[last_index]
        if not isinstance(last_message, HumanMessage):
            return None

        original_content = last_message.content
        if isinstance(original_content, str):
            if _PROJECT_CONTEXT_MARKER in original_content:
                return None
            updated_content = f"{self._build_project_context(project_root)}\n\n{original_content}"
        elif isinstance(original_content, list):
            text_parts: list[str] = []
            for block in original_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
            joined = "\n".join(text_parts)
            if _PROJECT_CONTEXT_MARKER in joined:
                return None
            updated_content = f"{self._build_project_context(project_root)}\n\n{joined}"
        else:
            updated_content = self._build_project_context(project_root)

        messages[last_index] = HumanMessage(
            content=updated_content,
            id=last_message.id,
            additional_kwargs=last_message.additional_kwargs,
            name=last_message.name,
        )

        return {"messages": messages}
