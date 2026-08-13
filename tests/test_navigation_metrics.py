from math import isclose

import pytest

from turtlebot3_multimodal.navigation_metrics import PoseSample, path_length, summarize_navigation


def sample(time_s: float, x_m: float, y_m: float, speed: float = 0.0) -> PoseSample:
    return PoseSample(time_s, x_m, y_m, speed, speed / 2.0)


def test_path_length_accumulates_segments() -> None:
    assert path_length([sample(0, 0, 0), sample(1, 3, 4), sample(2, 3, 6)]) == 7.0


def test_summary_reports_endpoint_and_limits() -> None:
    metrics = summarize_navigation(
        [sample(0, -2.0, -0.5), sample(2, -1.3, -0.5, 0.22)],
        -1.2,
        -0.5,
        succeeded=True,
        recoveries=2,
    )
    assert metrics["status"] == "succeeded"
    assert isclose(metrics["final_position_error_m"], 0.1)
    assert metrics["max_linear_speed_mps"] == 0.22
    assert metrics["recoveries"] == 2


def test_summary_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize_navigation([], 0.0, 0.0, succeeded=False, recoveries=0)
