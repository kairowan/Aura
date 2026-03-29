from types import SimpleNamespace

from pathlib import Path

from aura.tools.builtins.desktop_automation_tool import _find_ocr_matches, _format_ocr_matches, _run_screen_ocr
from aura.tools.tools import get_available_tools


def test_get_available_tools_includes_desktop_tools_when_enabled(monkeypatch):
    dummy_config = SimpleNamespace(
        tools=[],
        models=[],
        tool_search=SimpleNamespace(enabled=False),
        get_model_config=lambda _name: None,
    )

    monkeypatch.setattr("aura.tools.tools.get_app_config", lambda: dummy_config)
    monkeypatch.setenv("AURA_DESKTOP_AUTOMATION_ENABLED", "true")

    tools = get_available_tools(include_mcp=False, subagent_enabled=False)
    names = {tool.name for tool in tools}

    assert "desktop_capture_screenshot" in names
    assert "desktop_get_frontmost_window" in names
    assert "desktop_click_at" in names
    assert "desktop_click_in_window" in names
    assert "desktop_drag_mouse" in names
    assert "desktop_drag_in_window" in names
    assert "desktop_scroll" in names
    assert "desktop_click_ui_element_at_index" in names
    assert "desktop_find_text_on_screen" in names
    assert "desktop_click_text_on_screen" in names


def test_find_ocr_matches_supports_partial_and_casefold():
    observations = [
        {"text": "Send Message", "x": 10.0, "y": 20.0, "width": 80.0, "height": 20.0, "center_x": 50.0, "center_y": 30.0, "confidence": 0.9},
        {"text": "Cancel", "x": 20.0, "y": 60.0, "width": 60.0, "height": 20.0, "center_x": 50.0, "center_y": 70.0, "confidence": 0.8},
    ]

    partial_matches = _find_ocr_matches(observations, "send", partial_match=True, case_sensitive=False)
    exact_matches = _find_ocr_matches(observations, "Cancel", partial_match=False, case_sensitive=True)

    assert [item["text"] for item in partial_matches] == ["Send Message"]
    assert [item["text"] for item in exact_matches] == ["Cancel"]


def test_format_ocr_matches_reports_occurrences():
    matches = [
        {"text": "Send", "x": 12.0, "y": 24.0, "width": 40.0, "height": 12.0, "center_x": 32.0, "center_y": 30.0, "confidence": 0.91},
        {"text": "Send later", "x": 14.0, "y": 54.0, "width": 64.0, "height": 12.0, "center_x": 46.0, "center_y": 60.0, "confidence": 0.84},
    ]

    formatted = _format_ocr_matches("/mnt/user-data/outputs/desktop.png", "Send", matches, max_results=5)

    assert 'OCR matches for "Send"' in formatted
    assert "occurrence=1 text=Send" in formatted
    assert "occurrence=2 text=Send later" in formatted


def test_run_screen_ocr_groups_tesseract_words_into_lines(monkeypatch):
    tsv_output = "\n".join(
        [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t100\t40\t50\t20\t91\tSend",
            "5\t1\t1\t1\t1\t2\t160\t40\t80\t20\t93\tMessage",
            "5\t1\t1\t1\t2\t1\t100\t80\t60\t18\t89\tCancel",
        ]
    )

    monkeypatch.setattr("aura.tools.builtins.desktop_automation_tool.shutil.which", lambda _name: "/opt/homebrew/bin/tesseract")
    monkeypatch.setattr("aura.tools.builtins.desktop_automation_tool._run_process", lambda _args, env=None: tsv_output)

    payload = _run_screen_ocr(Path("/tmp/fake.png"))

    assert [item["text"] for item in payload["observations"]] == ["Send Message", "Cancel"]
    assert payload["observations"][0]["center_x"] == 170.0


def test_run_screen_ocr_uses_bundled_runtime_env(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "ocr-runtime"
    bin_dir = runtime_dir / "bin"
    lib_dir = runtime_dir / "lib"
    tessdata_dir = runtime_dir / "share" / "tessdata"
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)
    tessdata_dir.mkdir(parents=True)

    binary_path = bin_dir / "tesseract"
    binary_path.write_text("")
    library_stub = lib_dir / "libtesseract.5.dylib"
    library_stub.write_text("")
    (tessdata_dir / "chi_sim.traineddata").write_text("")

    monkeypatch.setenv("AURA_TESSERACT_BINARY", str(binary_path))
    monkeypatch.setenv("AURA_TESSDATA_DIR", str(tessdata_dir))
    monkeypatch.setenv("AURA_TESSERACT_LIBRARY_PATH", str(lib_dir))

    tsv_output = "\n".join(
        [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t20\t10\t30\t12\t88\tSend",
        ]
    )
    captured = {}

    def fake_run_process(args, env=None):
        captured["args"] = args
        captured["env"] = env
        return tsv_output

    monkeypatch.setattr("aura.tools.builtins.desktop_automation_tool._run_process", fake_run_process)

    payload = _run_screen_ocr(Path("/tmp/fake.png"))

    assert payload["observations"][0]["text"] == "Send"
    assert captured["args"][:5] == [
        str(binary_path),
        "--tessdata-dir",
        str(tessdata_dir),
        "-l",
        "chi_sim+eng",
    ]
    assert "--psm" in captured["args"]
    assert captured["args"][-3:] == ["/tmp/fake.png", "stdout", "tsv"]
    assert captured["env"]["DYLD_LIBRARY_PATH"].startswith(str(lib_dir))
