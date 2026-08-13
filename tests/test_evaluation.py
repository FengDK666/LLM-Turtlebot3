from pathlib import Path

from turtlebot3_multimodal.evaluation import run_evaluation


def test_evaluation_exports_reproducible_artifacts(tmp_path: Path) -> None:
    outputs = run_evaluation(tmp_path)
    assert set(outputs) == {"trajectory", "metrics", "figure"}
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
    metrics = outputs["metrics"].read_text(encoding="utf-8")
    assert "adversarial_payloads_rejected,6" in metrics
    assert "final_speed_mps,0.0" in metrics
