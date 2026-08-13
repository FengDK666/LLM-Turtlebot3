"""Offline safety and trajectory evaluation for the command core."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from turtlebot3_multimodal.commands import CommandValidationError, parse_command_payload
from turtlebot3_multimodal.executor import MotionExecutor


def simulate(payload: dict, dt: float = 0.05) -> list[dict]:
    executor = MotionExecutor()
    executor.submit(parse_command_payload(payload))
    rows = []
    time_s = x = y = yaw = 0.0
    while not executor.idle and time_s < 120.0:
        velocity = executor.tick(time_s)
        x += velocity.linear_x * math.cos(yaw) * dt
        y += velocity.linear_x * math.sin(yaw) * dt
        yaw += velocity.angular_z * dt
        rows.append(
            {
                "time_s": round(time_s, 6),
                "x_m": x,
                "y_m": y,
                "yaw_rad": yaw,
                "linear_x": velocity.linear_x,
                "angular_z": velocity.angular_z,
            }
        )
        time_s += dt
    rows.append(
        {
            "time_s": round(time_s, 6),
            "x_m": x,
            "y_m": y,
            "yaw_rad": yaw,
            "linear_x": 0.0,
            "angular_z": 0.0,
        }
    )
    return rows


def run_evaluation(output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    square = {
        "source": "test",
        "commands": [
            item
            for _ in range(4)
            for item in (
                {"action": "forward", "value": 0.5},
                {"action": "left", "value": 90.0},
            )
        ]
        + [{"action": "stop"}],
    }
    trajectory = simulate(square)
    attacks = [
        "__import__('os').system('id')",
        '{"source":"llm","commands":[{"action":"forward","value":999}]}',
        '{"source":"llm","commands":[{"action":"shell","value":1}]}',
        '{"source":"llm","commands":[{"action":"stop","value":1}]}',
        '{"source":"unknown","commands":[{"action":"stop"}]}',
        "```python\nself.forward(1)\n```",
    ]
    rejected = 0
    for payload in attacks:
        try:
            parse_command_payload(payload)
        except CommandValidationError:
            rejected += 1
    final = trajectory[-1]
    metrics = [
        {"metric": "adversarial_payloads", "value": len(attacks)},
        {"metric": "adversarial_payloads_rejected", "value": rejected},
        {"metric": "max_linear_mps", "value": max(abs(row["linear_x"]) for row in trajectory)},
        {"metric": "max_angular_rps", "value": max(abs(row["angular_z"]) for row in trajectory)},
        {"metric": "square_closure_error_m", "value": math.hypot(final["x_m"], final["y_m"])},
        {"metric": "final_speed_mps", "value": abs(final["linear_x"])},
    ]
    trajectory_path = output / "offline_trajectory.csv"
    metrics_path = output / "safety_metrics.csv"
    figure_path = figure_dir / "offline_square_trajectory.png"
    for rows, path in ((trajectory, trajectory_path), (metrics, metrics_path)):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    fig, axis = plt.subplots(figsize=(6.2, 5.4))
    axis.plot(
        [row["x_m"] for row in trajectory],
        [row["y_m"] for row in trajectory],
        color="#2563eb",
        linewidth=2,
    )
    axis.scatter([0], [0], color="#16a34a", label="start")
    axis.scatter([final["x_m"]], [final["y_m"]], color="#dc2626", label="finish")
    axis.set(
        title="Safe command core - offline square replay",
        xlabel="x (m)",
        ylabel="y (m)",
        aspect="equal",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(figure_path, dpi=170)
    plt.close(fig)
    return {"trajectory": trajectory_path, "metrics": metrics_path, "figure": figure_path}
