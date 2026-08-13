import pytest

from turtlebot3_multimodal.adapters import gesture_to_payload, parse_llm_json
from turtlebot3_multimodal.commands import CommandValidationError, parse_command_payload


def test_valid_json_sequence_is_parsed() -> None:
    plan = parse_command_payload(
        {"source": "voice", "commands": [{"action": "forward", "value": 0.5}, {"action": "stop"}]}
    )
    assert [command.action for command in plan.commands] == ["forward", "stop"]


@pytest.mark.parametrize(
    "payload",
    [
        "self.forward(1)",
        "```python\nself.forward(1)\n```",
        '{"source":"llm","commands":[{"action":"forward","value":999}]}',
        '{"source":"llm","commands":[{"action":"shell","value":1}]}',
        '{"source":"llm","commands":[{"action":"stop","value":1}]}',
        '{"source":"llm","commands":[{"action":"forward","value":NaN}]}',
    ],
)
def test_code_and_invalid_commands_are_rejected(payload: str) -> None:
    with pytest.raises(CommandValidationError):
        parse_command_payload(payload)


def test_gesture_and_llm_adapters_use_same_protocol() -> None:
    assert parse_command_payload(gesture_to_payload("Victory")).commands[0].action == "stop"
    assert parse_llm_json(
        '{"source":"llm","commands":[{"action":"left","value":90}]}'
    ).commands[0].value == 90
