"""Pure-Python metrics for odometry-based navigation evaluations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from math import hypot


@dataclass(frozen=True)
class PoseSample:
    time_s: float
    x_m: float
    y_m: float
    linear_speed_mps: float
    angular_speed_radps: float


def path_length(samples: Iterable[PoseSample]) -> float:
    points = list(samples)
    return sum(
        hypot(current.x_m - previous.x_m, current.y_m - previous.y_m)
        for previous, current in pairwise(points)
    )


def summarize_navigation(
    samples: Iterable[PoseSample],
    goal_x_m: float,
    goal_y_m: float,
    *,
    succeeded: bool,
    recoveries: int,
) -> dict[str, float | int | str]:
    points = list(samples)
    if not points:
        raise ValueError("at least one odometry sample is required")
    duration_s = max(0.0, points[-1].time_s - points[0].time_s)
    final = points[-1]
    return {
        "status": "succeeded" if succeeded else "failed",
        "duration_s": duration_s,
        "samples": len(points),
        "path_length_m": path_length(points),
        "final_position_error_m": hypot(final.x_m - goal_x_m, final.y_m - goal_y_m),
        "max_linear_speed_mps": max(abs(point.linear_speed_mps) for point in points),
        "max_angular_speed_radps": max(abs(point.angular_speed_radps) for point in points),
        "final_linear_speed_mps": abs(final.linear_speed_mps),
        "final_angular_speed_radps": abs(final.angular_speed_radps),
        "recoveries": recoveries,
    }
