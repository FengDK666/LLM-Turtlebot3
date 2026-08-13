"""Safe adapters that convert perception or model output into command JSON."""

from __future__ import annotations

from turtlebot3_multimodal.commands import CommandPlan, command_payload, parse_command_payload

GESTURE_COMMANDS = {
    "Open_Palm": {"action": "forward", "value": 0.2},
    "Pointing_Up": {"action": "backward", "value": 0.2},
    "Closed_Fist": {"action": "left", "value": 45.0},
    "Thumb_Up": {"action": "right", "value": 45.0},
    "Victory": {"action": "stop"},
}


def gesture_to_payload(label: str) -> str:
    if label not in GESTURE_COMMANDS:
        raise ValueError(f"unsupported gesture: {label!r}")
    return command_payload("gesture", [GESTURE_COMMANDS[label]])


def parse_llm_json(text: str) -> CommandPlan:
    """Accept JSON only; Python, Markdown fences, and prose are rejected."""
    plan = parse_command_payload(text)
    if plan.source != "llm":
        raise ValueError("LLM payload must declare source='llm'")
    return plan


LLM_SYSTEM_PROMPT = """Return exactly one JSON object and no Markdown or prose.
Schema: {"source":"llm","commands":[{"action":"forward|backward|left|right","value":number}|{"action":"stop"}]}
Use metres for forward/backward and degrees for left/right. Maximum distance is 2.0 m,
maximum angle is 360 degrees, and maximum sequence length is 16. Never output code."""
