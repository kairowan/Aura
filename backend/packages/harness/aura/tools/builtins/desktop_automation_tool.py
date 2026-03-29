import base64
import csv
import ctypes
import io
import mimetypes
import os
import shutil
import subprocess
import time
from ctypes import util
from pathlib import Path
from typing import Annotated, Literal

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from aura.agents.thread_state import ThreadState
from aura.config.paths import VIRTUAL_PATH_PREFIX
from aura.sandbox.tools import get_thread_data, replace_virtual_path

OUTPUTS_VIRTUAL_PREFIX = f"{VIRTUAL_PATH_PREFIX}/outputs"
APPLE_ROLE_MAP = {
    "button": "AXButton",
    "checkbox": "AXCheckBox",
    "menu_item": "AXMenuItem",
    "radio_button": "AXRadioButton",
    "text_field": "AXTextField",
    "group": "AXGroup",
    "any": "",
}
SPECIAL_KEY_CODES = {
    "return": 36,
    "enter": 36,
    "tab": 48,
    "space": 49,
    "delete": 51,
    "backspace": 51,
    "escape": 53,
    "esc": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
}
MODIFIER_NAMES = {"command", "shift", "option", "control", "fn"}
LEFT_MOUSE_BUTTON = 0
RIGHT_MOUSE_BUTTON = 1
OTHER_MOUSE_BUTTON = 2
KCG_HID_EVENT_TAP = 0
KCG_EVENT_LEFT_MOUSE_DOWN = 1
KCG_EVENT_LEFT_MOUSE_UP = 2
KCG_EVENT_RIGHT_MOUSE_DOWN = 3
KCG_EVENT_RIGHT_MOUSE_UP = 4
KCG_EVENT_MOUSE_MOVED = 5
KCG_EVENT_LEFT_MOUSE_DRAGGED = 6
KCG_EVENT_RIGHT_MOUSE_DRAGGED = 7
KCG_EVENT_SCROLL_WHEEL = 22
KCG_SCROLL_EVENT_UNIT_LINE = 1


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


_APPLICATION_SERVICES = None
_CORE_FOUNDATION = None


def _desktop_automation_supported() -> bool:
    return os.getenv("AURA_DESKTOP_AUTOMATION_ENABLED", "").lower() in {"1", "true", "yes"}


def _ensure_supported() -> None:
    if os.sys.platform != "darwin":
        raise RuntimeError("Desktop automation currently only supports macOS.")
    if not _desktop_automation_supported():
        raise RuntimeError("Desktop automation is disabled in the current Aura runtime.")


def _load_frameworks() -> tuple[ctypes.CDLL, ctypes.CDLL]:
    global _APPLICATION_SERVICES, _CORE_FOUNDATION
    if _APPLICATION_SERVICES is None:
        app_services_path = util.find_library("ApplicationServices")
        core_foundation_path = util.find_library("CoreFoundation")
        if not app_services_path or not core_foundation_path:
            raise RuntimeError("Failed to load macOS desktop automation frameworks.")
        _APPLICATION_SERVICES = ctypes.cdll.LoadLibrary(app_services_path)
        _CORE_FOUNDATION = ctypes.cdll.LoadLibrary(core_foundation_path)

        _APPLICATION_SERVICES.CGEventCreateMouseEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            CGPoint,
            ctypes.c_uint32,
        ]
        _APPLICATION_SERVICES.CGEventCreateMouseEvent.restype = ctypes.c_void_p
        _APPLICATION_SERVICES.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        _APPLICATION_SERVICES.CGEventPost.restype = None
        _APPLICATION_SERVICES.CGEventCreateScrollWheelEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_int32,
            ctypes.c_int32,
        ]
        _APPLICATION_SERVICES.CGEventCreateScrollWheelEvent.restype = ctypes.c_void_p
        _APPLICATION_SERVICES.CGWarpMouseCursorPosition.argtypes = [CGPoint]
        _APPLICATION_SERVICES.CGWarpMouseCursorPosition.restype = ctypes.c_int32
        _CORE_FOUNDATION.CFRelease.argtypes = [ctypes.c_void_p]
        _CORE_FOUNDATION.CFRelease.restype = None

    return _APPLICATION_SERVICES, _CORE_FOUNDATION


def _escape_apple_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_process(args: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown error").strip()
        if args and args[0] == "osascript":
            lowered = detail.lower()
            if "-1719" in detail or "assistive access" in lowered:
                raise RuntimeError(
                    "Accessibility permission is required. Enable Aura in macOS System Settings > Privacy & Security > Accessibility."
                )
            if "-1743" in detail or "not authorized to send apple events" in lowered:
                raise RuntimeError(
                    "Automation permission is required. Allow Aura to control System Events in macOS System Settings > Privacy & Security > Automation."
                )
            if "-10827" in detail:
                raise RuntimeError(
                    "Desktop automation requires Aura to run inside an active macOS desktop session."
                )
        raise RuntimeError(detail)
    return (result.stdout or "").strip()


def _run_applescript(*lines: str) -> str:
    args = ["osascript"]
    for line in lines:
        args.extend(["-e", line])
    return _run_process(args)


def _post_mouse_event(
    event_type: int,
    x: float,
    y: float,
    button: int,
) -> None:
    app_services, core_foundation = _load_frameworks()
    event = app_services.CGEventCreateMouseEvent(None, event_type, CGPoint(float(x), float(y)), button)
    if not event:
        raise RuntimeError("Failed to create mouse event.")
    try:
        app_services.CGEventPost(KCG_HID_EVENT_TAP, event)
    finally:
        core_foundation.CFRelease(event)


def _move_mouse(x: float, y: float) -> None:
    app_services, _ = _load_frameworks()
    status = app_services.CGWarpMouseCursorPosition(CGPoint(float(x), float(y)))
    if status != 0:
        raise RuntimeError(f"Failed to move mouse cursor (status={status}).")


def _scroll_mouse(delta_y: int, delta_x: int = 0) -> None:
    app_services, core_foundation = _load_frameworks()
    event = app_services.CGEventCreateScrollWheelEvent(
        None,
        KCG_SCROLL_EVENT_UNIT_LINE,
        2,
        int(delta_y),
        int(delta_x),
    )
    if not event:
        raise RuntimeError("Failed to create scroll event.")
    try:
        app_services.CGEventPost(KCG_HID_EVENT_TAP, event)
    finally:
        core_foundation.CFRelease(event)


def _get_frontmost_app_name() -> str:
    return _run_applescript(
        'tell application "System Events"',
        'set frontApp to name of first application process whose frontmost is true',
        "return frontApp",
        "end tell",
    )


def _get_frontmost_window_info(app_name: str | None = None) -> dict[str, str]:
    target_app = _escape_apple_string(app_name or "")
    output = _run_applescript(
        f'set targetApp to "{target_app}"',
        'tell application "System Events"',
        'if targetApp is "" then',
        'set targetProcess to first application process whose frontmost is true',
        "else",
        'set targetProcess to application process targetApp',
        "end if",
        'if not (exists targetProcess) then error "Target application is not running."',
        'tell targetProcess',
        'if (count of windows) is 0 then error "Target application has no visible window."',
        'set targetWindow to front window',
        'set windowTitle to name of targetWindow as text',
        'set {posX, posY} to position of targetWindow',
        'set {winW, winH} to size of targetWindow',
        'return windowTitle & tab & posX & tab & posY & tab & winW & tab & winH',
        "end tell",
        "end tell",
    )
    title, pos_x, pos_y, width, height = (output.split("\t") + ["", "0", "0", "0", "0"])[:5]
    return {
        "title": title,
        "x": pos_x,
        "y": pos_y,
        "width": width,
        "height": height,
    }


def _serialize_modifiers(modifiers: list[str]) -> str:
    normalized = []
    for modifier in modifiers:
        lowered = modifier.strip().lower()
        if lowered not in MODIFIER_NAMES:
            raise RuntimeError(f"Unsupported modifier: {modifier}")
        normalized.append(f"{lowered} down")
    return ", ".join(normalized)


def _build_keypress_lines(key: str, modifiers: list[str], app_name: str | None = None) -> list[str]:
    lines: list[str] = []
    if app_name:
        escaped_app = _escape_apple_string(app_name)
        lines.extend(
            [
                f'tell application "{escaped_app}" to activate',
                "delay 0.2",
            ]
        )

    using_clause = ""
    if modifiers:
        using_clause = f" using {{{_serialize_modifiers(modifiers)}}}"

    lowered_key = key.strip().lower()
    lines.append('tell application "System Events"')
    if lowered_key in SPECIAL_KEY_CODES:
        key_code = SPECIAL_KEY_CODES[lowered_key]
        lines.append(f"key code {key_code}{using_clause}")
    else:
        escaped_key = _escape_apple_string(key)
        lines.append(f'keystroke "{escaped_key}"{using_clause}')
    lines.append("end tell")
    return lines


def _build_typing_lines(text: str, app_name: str | None = None, press_enter_after: bool = False) -> list[str]:
    lines: list[str] = []
    if app_name:
        escaped_app = _escape_apple_string(app_name)
        lines.extend(
            [
                f'tell application "{escaped_app}" to activate',
                "delay 0.2",
            ]
        )

    lines.append('tell application "System Events"')
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    segments = normalized_text.split("\n")
    for index, segment in enumerate(segments):
        if segment:
            escaped_segment = _escape_apple_string(segment)
            lines.append(f'keystroke "{escaped_segment}"')
        if index < len(segments) - 1:
            lines.append("key code 36")
    if press_enter_after:
        lines.append("key code 36")
    lines.append("end tell")
    return lines


def _build_ui_enumeration_lines(
    app_name: str | None,
    role: str,
    query: str | None,
    max_results: int,
) -> list[str]:
    target_app = _escape_apple_string(app_name or "")
    target_query = _escape_apple_string((query or "").strip())
    target_role = _escape_apple_string(APPLE_ROLE_MAP.get(role, ""))
    return [
        f'set targetApp to "{target_app}"',
        f'set targetQuery to "{target_query}"',
        f'set targetRole to "{target_role}"',
        f"set maxResults to {max_results}",
        'tell application "System Events"',
        'if targetApp is "" then',
        'set targetProcess to first application process whose frontmost is true',
        "else",
        'set targetProcess to application process targetApp',
        "end if",
        'if not (exists targetProcess) then error "Target application is not running."',
        'tell targetProcess',
        'if (count of windows) is 0 then error "Target application has no visible window."',
        "set outputLines to {}",
        "set matchIndex to 0",
        "repeat with el in entire contents of front window",
        "if (count of outputLines) >= maxResults then exit repeat",
        "try",
        'set elRole to role of el as text',
        'set elName to ""',
        'try',
        'set elName to name of el as text',
        "end try",
        'set elDesc to ""',
        'try',
        'set elDesc to description of el as text',
        "end try",
        'set searchable to (elName & " " & elDesc) as text',
        "set roleMatches to true",
        'if targetRole is not "" then set roleMatches to (elRole is targetRole)',
        "set queryMatches to true",
        'if targetQuery is not "" then set queryMatches to (searchable contains targetQuery)',
        'if roleMatches and queryMatches and searchable is not " " then',
        "set matchIndex to matchIndex + 1",
        'set posX to ""',
        'set posY to ""',
        'set sizeW to ""',
        'set sizeH to ""',
        'try',
        'set {posX, posY} to position of el',
        "end try",
        'try',
        'set {sizeW, sizeH} to size of el',
        "end try",
        'set end of outputLines to (matchIndex & tab & elRole & tab & elName & tab & elDesc & tab & posX & tab & posY & tab & sizeW & tab & sizeH)',
        "end if",
        "end try",
        "end repeat",
        'set AppleScript\'s text item delimiters to linefeed',
        "return outputLines as text",
        "end tell",
        "end tell",
    ]


def _build_ui_click_lines(
    title: str,
    role: str,
    app_name: str | None,
    partial_match: bool,
) -> list[str]:
    target_app = _escape_apple_string(app_name or "")
    target_title = _escape_apple_string(title)
    target_role = _escape_apple_string(APPLE_ROLE_MAP.get(role, ""))
    match_operator = "contains" if partial_match else "is"
    return [
        f'set targetApp to "{target_app}"',
        f'set targetTitle to "{target_title}"',
        f'set targetRole to "{target_role}"',
        'tell application "System Events"',
        'if targetApp is "" then',
        'set targetProcess to first application process whose frontmost is true',
        "else",
        'set targetProcess to application process targetApp',
        "end if",
        'if not (exists targetProcess) then error "Target application is not running."',
        'tell targetProcess',
        'if (count of windows) is 0 then error "Target application has no visible window."',
        "set matchedLabel to missing value",
        "set matchedElement to missing value",
        "repeat with el in entire contents of front window",
        "try",
        'set elRole to role of el as text',
        'set elName to ""',
        'try',
        'set elName to name of el as text',
        "end try",
        'set elDesc to ""',
        'try',
        'set elDesc to description of el as text',
        "end try",
        "set roleMatches to true",
        'if targetRole is not "" then set roleMatches to (elRole is targetRole)',
        "set textMatches to false",
        f'if elName is not "" and elName {match_operator} targetTitle then set textMatches to true',
        f'if textMatches is false and elDesc is not "" and elDesc {match_operator} targetTitle then set textMatches to true',
        "if roleMatches and textMatches then",
        "set matchedElement to el",
        'set matchedLabel to (elRole & " / " & elName & " / " & elDesc) as text',
        "exit repeat",
        "end if",
        "end try",
        "end repeat",
        "if matchedElement is missing value then error \"No matching UI element was found.\"",
        'perform action "AXPress" of matchedElement',
        "return matchedLabel",
        "end tell",
        "end tell",
    ]


def _build_ui_click_by_index_lines(
    index: int,
    app_name: str | None,
    role: str,
    query: str | None,
) -> list[str]:
    target_app = _escape_apple_string(app_name or "")
    target_query = _escape_apple_string((query or "").strip())
    target_role = _escape_apple_string(APPLE_ROLE_MAP.get(role, ""))
    return [
        f'set targetIndex to {index}',
        f'set targetApp to "{target_app}"',
        f'set targetQuery to "{target_query}"',
        f'set targetRole to "{target_role}"',
        'tell application "System Events"',
        'if targetApp is "" then',
        'set targetProcess to first application process whose frontmost is true',
        "else",
        'set targetProcess to application process targetApp',
        "end if",
        'if not (exists targetProcess) then error "Target application is not running."',
        'tell targetProcess',
        'if (count of windows) is 0 then error "Target application has no visible window."',
        "set matchIndex to 0",
        "set matchedLabel to missing value",
        "repeat with el in entire contents of front window",
        "try",
        'set elRole to role of el as text',
        'set elName to ""',
        'try',
        'set elName to name of el as text',
        "end try",
        'set elDesc to ""',
        'try',
        'set elDesc to description of el as text',
        "end try",
        'set searchable to (elName & " " & elDesc) as text',
        "set roleMatches to true",
        'if targetRole is not "" then set roleMatches to (elRole is targetRole)',
        "set queryMatches to true",
        'if targetQuery is not "" then set queryMatches to (searchable contains targetQuery)',
        'if roleMatches and queryMatches and searchable is not " " then',
        "set matchIndex to matchIndex + 1",
        "if matchIndex is targetIndex then",
        'perform action "AXPress" of el',
        'set matchedLabel to (elRole & " / " & elName & " / " & elDesc) as text',
        "exit repeat",
        "end if",
        "end if",
        "end try",
        "end repeat",
        'if matchedLabel is missing value then error "No matching UI element index was found."',
        "return matchedLabel",
        "end tell",
        "end tell",
    ]


def _mouse_button_constants(button: str) -> tuple[int, int, int]:
    normalized = button.strip().lower()
    if normalized == "left":
        return LEFT_MOUSE_BUTTON, KCG_EVENT_LEFT_MOUSE_DOWN, KCG_EVENT_LEFT_MOUSE_UP
    if normalized == "right":
        return RIGHT_MOUSE_BUTTON, KCG_EVENT_RIGHT_MOUSE_DOWN, KCG_EVENT_RIGHT_MOUSE_UP
    if normalized == "other":
        return OTHER_MOUSE_BUTTON, KCG_EVENT_LEFT_MOUSE_DOWN, KCG_EVENT_LEFT_MOUSE_UP
    raise RuntimeError(f"Unsupported mouse button: {button}")


def _thread_output_context(
    runtime: ToolRuntime[ContextT, ThreadState],
    filename: str,
) -> tuple[Path, str]:
    thread_data = get_thread_data(runtime)
    if not thread_data:
        raise RuntimeError("Thread data is not available for screenshot capture.")

    outputs_path = thread_data.get("outputs_path")
    if not outputs_path:
        raise RuntimeError("Thread outputs directory is not available.")

    host_path = Path(outputs_path).resolve()
    host_path.mkdir(parents=True, exist_ok=True)
    actual_path = host_path / filename
    virtual_path = f"{OUTPUTS_VIRTUAL_PREFIX}/{filename}"
    return actual_path, virtual_path


def _capture_thread_screenshot(
    runtime: ToolRuntime[ContextT, ThreadState],
    filename: str | None = None,
    *,
    prefix: str = "desktop-screenshot",
) -> tuple[Path, str]:
    safe_name = (filename or f"{prefix}-{int(time.time())}.png").strip()
    if not safe_name.lower().endswith(".png"):
        safe_name = f"{safe_name}.png"
    actual_path, virtual_path = _thread_output_context(runtime, safe_name)
    _run_process(["screencapture", "-x", "-t", "png", str(actual_path)])
    return actual_path, virtual_path


def _resolve_thread_output_file(
    runtime: ToolRuntime[ContextT, ThreadState],
    image_path: str,
) -> tuple[Path, str]:
    thread_data = get_thread_data(runtime)
    if not thread_data:
        raise RuntimeError("Thread data is not available.")

    outputs_path = thread_data.get("outputs_path")
    if not outputs_path:
        raise RuntimeError("Thread outputs directory is not available.")

    candidate = image_path.strip()
    if not candidate:
        raise RuntimeError("image_path is required.")

    if candidate.startswith(f"{OUTPUTS_VIRTUAL_PREFIX}/"):
        candidate = candidate[len(OUTPUTS_VIRTUAL_PREFIX) + 1 :]
    elif candidate.startswith(OUTPUTS_VIRTUAL_PREFIX):
        candidate = candidate[len(OUTPUTS_VIRTUAL_PREFIX) :].lstrip("/")
    else:
        candidate = replace_virtual_path(candidate, thread_data)
        resolved = Path(candidate).expanduser().resolve()
        outputs_root = Path(outputs_path).resolve()
        if not resolved.is_relative_to(outputs_root):
            raise RuntimeError("Only files inside the current thread outputs directory are supported.")
        relative = resolved.relative_to(outputs_root).as_posix()
        virtual_path = f"{OUTPUTS_VIRTUAL_PREFIX}/{relative}"
        if not resolved.exists() or not resolved.is_file():
            raise RuntimeError(f"Screenshot file not found: {virtual_path}")
        return resolved, virtual_path

    actual_path = (Path(outputs_path).resolve() / candidate).resolve()
    outputs_root = Path(outputs_path).resolve()
    if not actual_path.is_relative_to(outputs_root):
        raise RuntimeError("image_path must stay inside the current thread outputs directory.")
    virtual_path = f"{OUTPUTS_VIRTUAL_PREFIX}/{candidate.replace(os.sep, '/')}"
    if not actual_path.exists() or not actual_path.is_file():
        raise RuntimeError(f"Screenshot file not found: {virtual_path}")
    return actual_path, virtual_path


def _image_payload(virtual_path: str, actual_path: Path) -> dict[str, dict[str, str]]:
    mime_type, _ = mimetypes.guess_type(actual_path.name)
    mime_type = mime_type or "image/png"
    image_data = base64.b64encode(actual_path.read_bytes()).decode("utf-8")
    return {virtual_path: {"base64": image_data, "mime_type": mime_type}}


def _run_screen_ocr(image_path: Path) -> dict:
    tesseract = os.getenv("AURA_TESSERACT_BINARY") or shutil.which("tesseract")
    if not tesseract or not Path(tesseract).exists():
        raise RuntimeError("Tesseract OCR is unavailable on this machine.")

    tessdata_dir = os.getenv("AURA_TESSDATA_DIR")
    languages = os.getenv("AURA_TESSERACT_LANGS")
    page_segmentation_mode = os.getenv("AURA_TESSERACT_PSM", "11")
    if not languages:
        if tessdata_dir and Path(tessdata_dir, "chi_sim.traineddata").exists():
            languages = "chi_sim+eng"
        else:
            languages = "eng"

    command = [tesseract]
    if tessdata_dir and Path(tessdata_dir).exists():
        command.extend(["--tessdata-dir", tessdata_dir])
    if languages:
        command.extend(["-l", languages])
    if page_segmentation_mode:
        command.extend(["--psm", page_segmentation_mode])
    command.extend([str(image_path), "stdout", "tsv"])

    runtime_env = None
    library_path = os.getenv("AURA_TESSERACT_LIBRARY_PATH")
    if library_path and Path(library_path).exists():
        runtime_env = os.environ.copy()
        existing = runtime_env.get("DYLD_LIBRARY_PATH", "")
        runtime_env["DYLD_LIBRARY_PATH"] = (
            f"{library_path}{os.pathsep}{existing}" if existing else library_path
        )

    output = _run_process(command, env=runtime_env)
    lines = [line for line in output.splitlines() if line.count("\t") >= 11]
    if not lines:
        return {"image": {}, "observations": []}

    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t")
    grouped_lines: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for row in reader:
        if row.get("level") != "5":
            continue

        text = (row.get("text") or "").strip()
        if not text:
            continue

        key = (
            row.get("page_num", ""),
            row.get("block_num", ""),
            row.get("par_num", ""),
            row.get("line_num", ""),
        )
        left = float(row.get("left") or 0.0)
        top = float(row.get("top") or 0.0)
        width = float(row.get("width") or 0.0)
        height = float(row.get("height") or 0.0)
        confidence = float(row.get("conf") or -1.0)

        entry = grouped_lines.setdefault(
            key,
            {
                "words": [],
                "x": left,
                "y": top,
                "right": left + width,
                "bottom": top + height,
                "confidences": [],
            },
        )
        entry["words"].append((left, text))
        entry["x"] = min(float(entry["x"]), left)
        entry["y"] = min(float(entry["y"]), top)
        entry["right"] = max(float(entry["right"]), left + width)
        entry["bottom"] = max(float(entry["bottom"]), top + height)
        if confidence >= 0:
            entry["confidences"].append(confidence)

    observations: list[dict[str, float | str]] = []
    for entry in grouped_lines.values():
        words = sorted(entry["words"], key=lambda item: item[0])
        line_text = " ".join(text for _, text in words).strip()
        if not line_text:
            continue
        left = float(entry["x"])
        top = float(entry["y"])
        right = float(entry["right"])
        bottom = float(entry["bottom"])
        confidences: list[float] = entry["confidences"]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        observations.append(
            {
                "text": line_text,
                "confidence": avg_confidence,
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
                "center_x": left + ((right - left) / 2),
                "center_y": top + ((bottom - top) / 2),
            }
        )

    observations.sort(key=lambda item: (float(item["y"]), float(item["x"])))
    return {"image": {}, "observations": observations}


def _normalize_ocr_text_for_match(value: str) -> str:
    return "".join(value.split())


def _find_ocr_matches(
    observations: list[dict[str, float | str]],
    query: str,
    *,
    partial_match: bool,
    case_sensitive: bool,
) -> list[dict[str, float | str]]:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise RuntimeError("query is required.")

    normalized_query = cleaned_query if case_sensitive else cleaned_query.casefold()
    normalized_query = _normalize_ocr_text_for_match(normalized_query)
    matches: list[dict[str, float | str]] = []
    for item in observations:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized_text = text if case_sensitive else text.casefold()
        normalized_text = _normalize_ocr_text_for_match(normalized_text)
        is_match = normalized_query in normalized_text if partial_match else normalized_text == normalized_query
        if is_match:
            matches.append(item)
    return matches


def _format_ocr_matches(
    target_image: str,
    query: str,
    matches: list[dict[str, float | str]],
    *,
    max_results: int,
) -> str:
    if not matches:
        return f'No OCR text matching "{query}" was found in {target_image}.'

    limited_matches = matches[:max_results]
    lines = [f'OCR matches for "{query}" in {target_image}:']
    for index, item in enumerate(limited_matches, start=1):
        lines.append(
            "- "
            f"occurrence={index} text={item['text']} "
            f"x={float(item['x']):.1f} y={float(item['y']):.1f} "
            f"width={float(item['width']):.1f} height={float(item['height']):.1f} "
            f"center_x={float(item['center_x']):.1f} center_y={float(item['center_y']):.1f} "
            f"confidence={float(item['confidence']):.2f}"
        )
    if len(matches) > max_results:
        lines.append(f"- ... {len(matches) - max_results} more match(es) omitted")
    return "\n".join(lines)


def _perform_click_at(x: float, y: float, button: str, click_count: int) -> int:
    mouse_button, down_event, up_event = _mouse_button_constants(button)
    repetitions = max(1, min(int(click_count), 5))
    _move_mouse(x, y)
    for _ in range(repetitions):
        _post_mouse_event(down_event, x, y, mouse_button)
        _post_mouse_event(up_event, x, y, mouse_button)
        time.sleep(0.04)
    return repetitions


@tool("desktop_capture_screenshot", parse_docstring=True)
def desktop_capture_screenshot(
    runtime: ToolRuntime[ContextT, ThreadState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    filename: str | None = None,
) -> Command:
    """Capture the current macOS desktop and attach it to the current Aura thread.

    Use this tool before desktop operations when you need to inspect the current UI state.
    The screenshot is saved to the current thread outputs and shown to the user.

    Notes:
    - Only works in the macOS desktop runtime.
    - Requires screen recording permission for Aura on some macOS versions.

    Args:
        filename: Optional PNG filename. If omitted, Aura generates one automatically.
    """
    try:
        _ensure_supported()
        actual_path, virtual_path = _capture_thread_screenshot(runtime, filename)
        return Command(
            update={
                "artifacts": [virtual_path],
                "viewed_images": _image_payload(virtual_path, actual_path),
                "messages": [
                    ToolMessage(
                        f"Captured desktop screenshot: {virtual_path}",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
    except Exception as exc:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"Failed to capture desktop screenshot: {exc}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )


@tool("desktop_find_text_on_screen", parse_docstring=True)
def desktop_find_text_on_screen(
    runtime: ToolRuntime[ContextT, ThreadState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    query: str,
    image_path: str | None = None,
    partial_match: bool = True,
    case_sensitive: bool = False,
    max_results: int = 10,
) -> Command:
    """Find visible screen text from a screenshot using macOS OCR.

    Use this when a target control is easier to identify by its visible text than by
    accessibility metadata. If no screenshot path is provided, Aura captures a fresh
    screenshot first and attaches it to the current thread.

    Args:
        query: Text to search for on screen.
        image_path: Optional screenshot file from the current thread outputs.
        partial_match: Whether substring matches are allowed.
        case_sensitive: Whether text matching should preserve letter case.
        max_results: Maximum number of matches to include in the tool output.
    """
    try:
        _ensure_supported()
        captured_new_image = image_path is None
        if captured_new_image:
            actual_path, virtual_path = _capture_thread_screenshot(runtime, prefix="desktop-ocr")
        else:
            actual_path, virtual_path = _resolve_thread_output_file(runtime, image_path or "")

        payload = _run_screen_ocr(actual_path)
        matches = _find_ocr_matches(
            payload["observations"],
            query,
            partial_match=partial_match,
            case_sensitive=case_sensitive,
        )

        update: dict[str, object] = {
            "viewed_images": _image_payload(virtual_path, actual_path),
            "messages": [
                ToolMessage(
                    _format_ocr_matches(virtual_path, query, matches, max_results=max(1, min(max_results, 25))),
                    tool_call_id=tool_call_id,
                )
            ],
        }
        if captured_new_image:
            update["artifacts"] = [virtual_path]
        return Command(update=update)
    except Exception as exc:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"Failed to find text on screen: {exc}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )


@tool("desktop_click_text_on_screen", parse_docstring=True)
def desktop_click_text_on_screen(
    runtime: ToolRuntime[ContextT, ThreadState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    query: str,
    image_path: str | None = None,
    occurrence: int = 1,
    partial_match: bool = True,
    case_sensitive: bool = False,
    button: Literal["left", "right", "other"] = "left",
    click_count: int = 1,
) -> Command:
    """Find visible screen text with OCR and click the matching region.

    Use this when the visible label is easier to target than the accessibility tree.
    If no screenshot path is provided, Aura captures a fresh screenshot first so the
    click is based on the latest screen state.

    Args:
        query: Text to search for before clicking.
        image_path: Optional screenshot file from the current thread outputs.
        occurrence: Which matching text occurrence to click after sorting top-to-bottom, left-to-right.
        partial_match: Whether substring matches are allowed.
        case_sensitive: Whether text matching should preserve letter case.
        button: Mouse button to use.
        click_count: Number of clicks to perform.
    """
    try:
        _ensure_supported()
        if occurrence < 1:
            raise RuntimeError("occurrence must be greater than or equal to 1.")

        captured_new_image = image_path is None
        if captured_new_image:
            actual_path, virtual_path = _capture_thread_screenshot(runtime, prefix="desktop-ocr-click")
        else:
            actual_path, virtual_path = _resolve_thread_output_file(runtime, image_path or "")

        payload = _run_screen_ocr(actual_path)
        matches = _find_ocr_matches(
            payload["observations"],
            query,
            partial_match=partial_match,
            case_sensitive=case_sensitive,
        )
        if not matches:
            raise RuntimeError(f'No OCR text matching "{query}" was found.')
        if occurrence > len(matches):
            raise RuntimeError(f"Only {len(matches)} match(es) were found, so occurrence {occurrence} is unavailable.")

        selected = matches[occurrence - 1]
        repetitions = _perform_click_at(float(selected["center_x"]), float(selected["center_y"]), button, click_count)
        update: dict[str, object] = {
            "viewed_images": _image_payload(virtual_path, actual_path),
            "messages": [
                ToolMessage(
                    (
                        f'Clicked OCR text occurrence {occurrence} for "{query}" in {virtual_path}: '
                        f'text={selected["text"]} '
                        f'center_x={float(selected["center_x"]):.1f} center_y={float(selected["center_y"]):.1f} '
                        f'button={button} click_count={repetitions}'
                    ),
                    tool_call_id=tool_call_id,
                )
            ],
        }
        if captured_new_image:
            update["artifacts"] = [virtual_path]
        return Command(update=update)
    except Exception as exc:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"Failed to click text on screen: {exc}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )


@tool("desktop_list_applications", parse_docstring=True)
def desktop_list_applications() -> str:
    """List visible macOS applications so the agent can decide what to control next.

    Use this tool before activation, typing, or UI inspection when the current
    target application is unknown.
    """
    _ensure_supported()
    output = _run_applescript(
        'tell application "System Events"',
        'set frontApp to name of first application process whose frontmost is true',
        'set appNames to name of every application process whose background only is false',
        'set AppleScript\'s text item delimiters to linefeed',
        'return frontApp & linefeed & (appNames as text)',
        "end tell",
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "No visible applications were found."
    frontmost, *apps = lines
    unique_apps = []
    seen = set()
    for app in apps:
        if app not in seen:
            seen.add(app)
            unique_apps.append(app)
    items = "\n".join(f"- {app}" for app in unique_apps) if unique_apps else "- none"
    return f"Frontmost application: {frontmost}\nVisible applications:\n{items}"


@tool("desktop_open_application", parse_docstring=True)
def desktop_open_application(app_name: str) -> str:
    """Open a macOS application and bring it to the foreground.

    Use this tool when a workflow needs a specific native application window.

    Args:
        app_name: The macOS application name, for example "Finder" or "Safari".
    """
    _ensure_supported()
    cleaned = app_name.strip()
    if not cleaned:
        raise RuntimeError("app_name is required.")
    _run_process(["open", "-a", cleaned])
    _run_applescript(f'tell application "{_escape_apple_string(cleaned)}" to activate')
    return f'Opened and activated "{cleaned}".'


@tool("desktop_activate_application", parse_docstring=True)
def desktop_activate_application(app_name: str) -> str:
    """Bring an already running macOS application to the foreground.

    Use this tool before typing text or pressing shortcuts in a target application.

    Args:
        app_name: The macOS application name to activate.
    """
    _ensure_supported()
    cleaned = app_name.strip()
    if not cleaned:
        raise RuntimeError("app_name is required.")
    _run_applescript(f'tell application "{_escape_apple_string(cleaned)}" to activate')
    return f'Activated "{cleaned}".'


@tool("desktop_type_text", parse_docstring=True)
def desktop_type_text(
    text: str,
    app_name: str | None = None,
    press_enter_after: bool = False,
) -> str:
    """Type text into the currently focused macOS application.

    Use this tool after activating a target application or focusing a text field.
    For long or sensitive actions, capture a screenshot first so the model can verify focus.

    Args:
        text: The text to type.
        app_name: Optional application name to activate before typing.
        press_enter_after: Whether to press Enter after the text is typed.
    """
    _ensure_supported()
    if not text:
        raise RuntimeError("text is required.")
    _run_applescript(*_build_typing_lines(text, app_name=app_name, press_enter_after=press_enter_after))
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    return f'Typed text into "{target}".'


@tool("desktop_press_keys", parse_docstring=True)
def desktop_press_keys(
    key: str,
    modifiers: list[Literal["command", "shift", "option", "control", "fn"]] | None = None,
    app_name: str | None = None,
) -> str:
    """Send a keyboard key or shortcut to a macOS application.

    Use this tool for shortcuts like Command+L, Command+V, Escape, or arrow keys.

    Args:
        key: The main key to press. Supports normal characters and special keys like "return", "tab", "escape", "up", "down", "left", and "right".
        modifiers: Optional modifier keys such as ["command"] or ["command", "shift"].
        app_name: Optional application name to activate before sending the keypress.
    """
    _ensure_supported()
    cleaned_key = key.strip()
    if not cleaned_key:
        raise RuntimeError("key is required.")
    _run_applescript(*_build_keypress_lines(cleaned_key, modifiers or [], app_name=app_name))
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    combo = "+".join([*(modifiers or []), cleaned_key])
    return f'Sent "{combo}" to "{target}".'


@tool("desktop_list_ui_elements", parse_docstring=True)
def desktop_list_ui_elements(
    app_name: str | None = None,
    role: Literal["button", "checkbox", "menu_item", "radio_button", "text_field", "group", "any"] = "button",
    query: str | None = None,
    max_results: int = 25,
) -> str:
    """Inspect visible UI elements in the front window of a macOS application.

    Use this tool before clicking so the model can see which accessible controls are available.
    Accessibility permission is required.

    Args:
        app_name: Optional application name. If omitted, Aura inspects the frontmost app.
        role: Optional accessibility role filter to narrow the results.
        query: Optional text filter matched against element names and descriptions.
        max_results: Maximum number of elements to return.
    """
    _ensure_supported()
    result = _run_applescript(*_build_ui_enumeration_lines(app_name, role, query, max(1, min(max_results, 100))))
    lines = [line for line in result.splitlines() if line.strip()]
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    if not lines:
        return f'No matching UI elements were found in "{target}".'
    formatted = []
    for line in lines:
        index_value, role_value, name_value, desc_value, pos_x, pos_y, width, height = (
            line.split("\t") + ["", "", "", "", "", "", "", ""]
        )[:8]
        bounds = ""
        if pos_x or pos_y or width or height:
            bounds = f" x={pos_x or '?'} y={pos_y or '?'} width={width or '?'} height={height or '?'}"
        formatted.append(
            f"- index={index_value or '?'} role={role_value or 'unknown'} name={name_value or '-'} description={desc_value or '-'}{bounds}"
        )
    return f'UI elements in "{target}":\n' + "\n".join(formatted)


@tool("desktop_click_ui_element", parse_docstring=True)
def desktop_click_ui_element(
    title: str,
    app_name: str | None = None,
    role: Literal["button", "checkbox", "menu_item", "radio_button", "text_field", "group", "any"] = "button",
    partial_match: bool = True,
) -> str:
    """Click an accessible UI element in the front window of a macOS application.

    Use this tool after inspecting the current UI with a screenshot or `desktop_list_ui_elements`.
    Accessibility permission is required.

    Args:
        title: The visible element name or description to match.
        app_name: Optional application name. If omitted, Aura targets the frontmost app.
        role: Accessibility role to search for.
        partial_match: Whether the title may be a substring instead of an exact match.
    """
    _ensure_supported()
    cleaned_title = title.strip()
    if not cleaned_title:
        raise RuntimeError("title is required.")
    matched = _run_applescript(*_build_ui_click_lines(cleaned_title, role, app_name, partial_match))
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    return f'Clicked a UI element in "{target}": {matched}'


@tool("desktop_click_ui_element_at_index", parse_docstring=True)
def desktop_click_ui_element_at_index(
    index: int,
    app_name: str | None = None,
    role: Literal["button", "checkbox", "menu_item", "radio_button", "text_field", "group", "any"] = "any",
    query: str | None = None,
) -> str:
    """Click a visible UI element by its index from `desktop_list_ui_elements`.

    Use this when multiple controls have similar text and the indexed list is more reliable.

    Args:
        index: The element index reported by `desktop_list_ui_elements`.
        app_name: Optional application name. If omitted, Aura targets the frontmost app.
        role: Optional role filter to keep the indexing stable.
        query: Optional text filter to keep the indexing stable.
    """
    _ensure_supported()
    if index < 1:
        raise RuntimeError("index must be greater than or equal to 1.")
    matched = _run_applescript(*_build_ui_click_by_index_lines(index, app_name, role, query))
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    return f'Clicked UI element #{index} in "{target}": {matched}'


@tool("desktop_get_frontmost_window", parse_docstring=True)
def desktop_get_frontmost_window(app_name: str | None = None) -> str:
    """Get the title and bounds of the front window for a macOS application.

    Use this tool before coordinate-based clicks or drags so the model can reason
    about where an element likely sits inside the current window.

    Args:
        app_name: Optional application name. If omitted, Aura inspects the frontmost app.
    """
    _ensure_supported()
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    window = _get_frontmost_window_info(app_name)
    return (
        f'Front window for "{target}": '
        f'title="{window["title"]}" x={window["x"]} y={window["y"]} '
        f'width={window["width"]} height={window["height"]}'
    )


def _resolve_window_relative_point(
    relative_x: float,
    relative_y: float,
    app_name: str | None = None,
) -> tuple[float, float, str]:
    if relative_x < 0 or relative_x > 1 or relative_y < 0 or relative_y > 1:
        raise RuntimeError("relative_x and relative_y must be between 0 and 1.")
    target = app_name.strip() if app_name else _get_frontmost_app_name()
    window = _get_frontmost_window_info(app_name)
    origin_x = float(window["x"])
    origin_y = float(window["y"])
    width = float(window["width"])
    height = float(window["height"])
    return origin_x + (width * relative_x), origin_y + (height * relative_y), target


@tool("desktop_click_at", parse_docstring=True)
def desktop_click_at(
    x: float,
    y: float,
    button: Literal["left", "right", "other"] = "left",
    click_count: int = 1,
) -> str:
    """Click a coordinate on the macOS desktop.

    Use this tool when an action cannot be targeted reliably by accessibility labels.
    A screenshot or front-window inspection should usually precede coordinate clicks.

    Args:
        x: Global screen X coordinate.
        y: Global screen Y coordinate.
        button: Mouse button to use.
        click_count: Number of clicks to perform.
    """
    _ensure_supported()
    repetitions = _perform_click_at(x, y, button, click_count)
    return f"Clicked at ({x}, {y}) with {button} button x{repetitions}."


@tool("desktop_click_in_window", parse_docstring=True)
def desktop_click_in_window(
    relative_x: float,
    relative_y: float,
    app_name: str | None = None,
    button: Literal["left", "right", "other"] = "left",
    click_count: int = 1,
) -> str:
    """Click inside the front window using relative coordinates.

    Use this when you know the target is, for example, around the center or bottom-right
    of the current window but do not want to hard-code absolute screen coordinates.

    Args:
        relative_x: Horizontal position from 0.0 to 1.0 across the window.
        relative_y: Vertical position from 0.0 to 1.0 across the window.
        app_name: Optional application name. If omitted, Aura targets the frontmost app.
        button: Mouse button to use.
        click_count: Number of clicks to perform.
    """
    _ensure_supported()
    absolute_x, absolute_y, target = _resolve_window_relative_point(relative_x, relative_y, app_name)
    repetitions = _perform_click_at(absolute_x, absolute_y, button, click_count)
    return (
        f'Clicked inside "{target}" at relative ({relative_x:.3f}, {relative_y:.3f}) '
        f'=> absolute ({absolute_x:.1f}, {absolute_y:.1f}) with {button} button x{repetitions}.'
    )


@tool("desktop_drag_mouse", parse_docstring=True)
def desktop_drag_mouse(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    button: Literal["left", "right"] = "left",
    duration_seconds: float = 0.4,
    steps: int = 18,
) -> str:
    """Drag the mouse between two screen coordinates on macOS.

    Use this tool for slider movement, selection boxes, or drag-and-drop flows.

    Args:
        start_x: Start X coordinate.
        start_y: Start Y coordinate.
        end_x: End X coordinate.
        end_y: End Y coordinate.
        button: Mouse button used for the drag.
        duration_seconds: Approximate drag duration.
        steps: Number of intermediate drag events.
    """
    _ensure_supported()
    mouse_button, down_event, up_event = _mouse_button_constants(button)
    drag_event = KCG_EVENT_LEFT_MOUSE_DRAGGED if button == "left" else KCG_EVENT_RIGHT_MOUSE_DRAGGED
    total_steps = max(2, min(int(steps), 120))
    pause = max(float(duration_seconds), 0.01) / total_steps

    _move_mouse(start_x, start_y)
    _post_mouse_event(down_event, start_x, start_y, mouse_button)
    for index in range(1, total_steps + 1):
        progress = index / total_steps
        current_x = start_x + ((end_x - start_x) * progress)
        current_y = start_y + ((end_y - start_y) * progress)
        _post_mouse_event(drag_event, current_x, current_y, mouse_button)
        time.sleep(pause)
    _post_mouse_event(up_event, end_x, end_y, mouse_button)
    return f"Dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y}) with {button} button."


@tool("desktop_drag_in_window", parse_docstring=True)
def desktop_drag_in_window(
    start_relative_x: float,
    start_relative_y: float,
    end_relative_x: float,
    end_relative_y: float,
    app_name: str | None = None,
    button: Literal["left", "right"] = "left",
    duration_seconds: float = 0.4,
    steps: int = 18,
) -> str:
    """Drag between two relative points inside the front window.

    Use this for sliders or selection gestures when absolute screen coordinates are unstable.

    Args:
        start_relative_x: Start horizontal position from 0.0 to 1.0 across the window.
        start_relative_y: Start vertical position from 0.0 to 1.0 across the window.
        end_relative_x: End horizontal position from 0.0 to 1.0 across the window.
        end_relative_y: End vertical position from 0.0 to 1.0 across the window.
        app_name: Optional application name. If omitted, Aura targets the frontmost app.
        button: Mouse button used for the drag.
        duration_seconds: Approximate drag duration.
        steps: Number of intermediate drag events.
    """
    _ensure_supported()
    start_x, start_y, target = _resolve_window_relative_point(start_relative_x, start_relative_y, app_name)
    end_x, end_y, _ = _resolve_window_relative_point(end_relative_x, end_relative_y, app_name)
    mouse_button, down_event, up_event = _mouse_button_constants(button)
    drag_event = KCG_EVENT_LEFT_MOUSE_DRAGGED if button == "left" else KCG_EVENT_RIGHT_MOUSE_DRAGGED
    total_steps = max(2, min(int(steps), 120))
    pause = max(float(duration_seconds), 0.01) / total_steps

    _move_mouse(start_x, start_y)
    _post_mouse_event(down_event, start_x, start_y, mouse_button)
    for index in range(1, total_steps + 1):
        progress = index / total_steps
        current_x = start_x + ((end_x - start_x) * progress)
        current_y = start_y + ((end_y - start_y) * progress)
        _post_mouse_event(drag_event, current_x, current_y, mouse_button)
        time.sleep(pause)
    _post_mouse_event(up_event, end_x, end_y, mouse_button)
    return (
        f'Dragged inside "{target}" from relative ({start_relative_x:.3f}, {start_relative_y:.3f}) '
        f'to ({end_relative_x:.3f}, {end_relative_y:.3f}).'
    )


@tool("desktop_scroll", parse_docstring=True)
def desktop_scroll(
    delta_y: int,
    delta_x: int = 0,
    x: float | None = None,
    y: float | None = None,
) -> str:
    """Scroll the mouse wheel on macOS.

    Use this tool after focusing the right window or moving the cursor to a scrollable region.

    Args:
        delta_y: Vertical scroll amount. Positive values scroll up, negative values scroll down.
        delta_x: Horizontal scroll amount.
        x: Optional X coordinate to move the cursor before scrolling.
        y: Optional Y coordinate to move the cursor before scrolling.
    """
    _ensure_supported()
    if x is not None and y is not None:
        _move_mouse(x, y)
        time.sleep(0.03)
    _scroll_mouse(int(delta_y), int(delta_x))
    target = f" at ({x}, {y})" if x is not None and y is not None else ""
    return f"Scrolled with delta_y={delta_y}, delta_x={delta_x}{target}."
