from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from aura.agents.middlewares.view_image_middleware import ViewImageMiddleware


def test_view_image_middleware_injects_after_desktop_screenshot_tool():
    middleware = ViewImageMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="Capturing the screen.",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "desktop_capture_screenshot",
                        "args": {},
                    }
                ],
            ),
            ToolMessage(content="ok", tool_call_id="tool-1"),
        ],
        "viewed_images": {
            "/mnt/user-data/outputs/desktop.png": {
                "base64": "ZmFrZQ==",
                "mime_type": "image/png",
            }
        },
    }

    update = middleware.before_model(state, runtime=None)  # type: ignore[arg-type]

    assert update is not None
    assert "messages" in update
    injected = update["messages"][0]
    assert isinstance(injected, HumanMessage)
    assert "Here are the images you've viewed" in str(injected.content)
