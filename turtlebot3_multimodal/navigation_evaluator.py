"""Send a Nav2 goal, capture odometry, and write reproducible evaluation artifacts."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import rclpy
from action_msgs.msg import GoalStatus
from lifecycle_msgs.srv import GetState
from matplotlib.patches import Circle
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import SaveMap
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.action import ActionClient
from rclpy.node import Node

from .navigation_metrics import PoseSample, summarize_navigation


class NavigationEvaluator(Node):
    def __init__(self, goal_x: float, goal_y: float, timeout_s: float, output_dir: Path) -> None:
        super().__init__("navigation_evaluator")
        self.goal_x = goal_x
        self.goal_y = goal_y
        self.timeout_s = timeout_s
        self.output_dir = output_dir
        self.samples: list[PoseSample] = []
        self.recoveries = 0
        self.map_width = 0
        self.map_height = 0
        self.map_resolution_m = 0.0
        self.map_known_cells = 0
        self._start_monotonic = time.monotonic()
        self._action = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self._lifecycle = self.create_client(GetState, "/bt_navigator/get_state")
        self._map_saver = self.create_client(SaveMap, "/map_saver/save_map")
        self.create_subscription(Odometry, "/odom", self._on_odom, 50)
        self.create_subscription(OccupancyGrid, "/map", self._on_map, 10)

    def _on_odom(self, message: Odometry) -> None:
        self.samples.append(
            PoseSample(
                time_s=time.monotonic() - self._start_monotonic,
                x_m=message.pose.pose.position.x,
                y_m=message.pose.pose.position.y,
                linear_speed_mps=message.twist.twist.linear.x,
                angular_speed_radps=message.twist.twist.angular.z,
            )
        )

    def _on_map(self, message: OccupancyGrid) -> None:
        self.map_width = message.info.width
        self.map_height = message.info.height
        self.map_resolution_m = message.info.resolution
        self.map_known_cells = sum(value >= 0 for value in message.data)

    def run(self) -> bool:
        self.get_logger().info("waiting for odometry and active Nav2 lifecycle")
        if not self._wait_until_ready(60.0):
            self.get_logger().error("odometry or Nav2 lifecycle did not become ready")
            return False

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = self.goal_x
        goal.pose.pose.position.y = self.goal_y
        goal.pose.pose.orientation.w = 1.0
        send_future = self._action.send_goal_async(goal, feedback_callback=self._on_feedback)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        handle = send_future.result()
        if handle is None or not handle.accepted:
            self.get_logger().error("Nav2 rejected the goal")
            return False

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=self.timeout_s)
        if not result_future.done():
            self.get_logger().error("navigation timed out; requesting cancellation")
            handle.cancel_goal_async()
            return False
        wrapped_result = result_future.result()
        succeeded = wrapped_result is not None and wrapped_result.status == GoalStatus.STATUS_SUCCEEDED
        if succeeded:
            # Nav2 accepts the goal inside its position tolerance. Keep sampling
            # briefly so the final metrics reflect the robot settling to zero.
            settle_deadline = time.monotonic() + 2.0
            while rclpy.ok() and time.monotonic() < settle_deadline:
                rclpy.spin_once(self, timeout_sec=0.05)
            succeeded = self._save_map()
        return succeeded

    def _save_map(self) -> bool:
        if not self._map_saver.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("/map_saver/save_map did not become ready")
            return False
        self.output_dir.mkdir(parents=True, exist_ok=True)
        request = SaveMap.Request()
        request.map_topic = "/map"
        request.map_url = str(self.output_dir / "slam_map")
        request.image_format = "png"
        request.map_mode = "trinary"
        request.free_thresh = 0.25
        request.occupied_thresh = 0.65
        future = self._map_saver.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        response = future.result()
        if response is None or not response.result:
            self.get_logger().error("map saver failed")
            return False
        return True

    def _wait_until_ready(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            if (
                len(self.samples) < 5
                or self.map_known_cells == 0
                or not self._lifecycle.wait_for_service(timeout_sec=0.0)
            ):
                continue
            state_future = self._lifecycle.call_async(GetState.Request())
            rclpy.spin_until_future_complete(self, state_future, timeout_sec=1.0)
            state = state_future.result()
            if state is not None and state.current_state.label == "active":
                return self._action.wait_for_server(timeout_sec=5.0)
        return False

    def _on_feedback(self, message) -> None:
        self.recoveries = max(self.recoveries, int(message.feedback.number_of_recoveries))


def _write_results(
    output_dir: Path,
    samples: list[PoseSample],
    metrics: dict[str, float | int | str],
    goal_x: float,
    goal_y: float,
    goal_tolerance_m: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "navigation_trajectory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("time_s", "x_m", "y_m", "linear_speed_mps", "angular_speed_radps"))
        for sample in samples:
            writer.writerow(
                (
                    f"{sample.time_s:.6f}",
                    f"{sample.x_m:.6f}",
                    f"{sample.y_m:.6f}",
                    f"{sample.linear_speed_mps:.6f}",
                    f"{sample.angular_speed_radps:.6f}",
                )
            )
    with (output_dir / "navigation_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("metric", "value"))
        writer.writerows(metrics.items())

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    axis.plot([sample.x_m for sample in samples], [sample.y_m for sample in samples], label="odometry")
    axis.scatter(samples[0].x_m, samples[0].y_m, marker="o", label="start", zorder=3)
    axis.scatter(goal_x, goal_y, marker="*", s=150, label="goal", zorder=3)
    axis.add_patch(
        Circle(
            (goal_x, goal_y),
            goal_tolerance_m,
            fill=False,
            linestyle="--",
            color="tab:orange",
            label=f"{goal_tolerance_m:.2f} m tolerance",
        )
    )
    axis.scatter(samples[-1].x_m, samples[-1].y_m, marker="x", s=80, label="final", zorder=3)
    axis.set(title="Headless Gazebo + SLAM Toolbox + Nav2", xlabel="x (m)", ylabel="y (m)")
    axis.axis("equal")
    axis.grid(alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_dir / "navigation_trajectory.png", dpi=180)
    plt.close(figure)


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal-x", type=float, default=-1.2)
    parser.add_argument("--goal-y", type=float, default=-0.5)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--goal-tolerance", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, required=True)
    # ROS launch appends its own ``--ros-args`` block to executable arguments.
    arguments, _ros_arguments = parser.parse_known_args(argv)
    return arguments


def main(args: list[str] | None = None) -> None:
    arguments = _arguments(sys.argv[1:] if args is None else args)
    rclpy.init()
    evaluator = NavigationEvaluator(
        arguments.goal_x, arguments.goal_y, arguments.timeout, arguments.output_dir
    )
    try:
        succeeded = evaluator.run()
        if len(evaluator.samples) < 2:
            evaluator.get_logger().error("insufficient odometry samples")
            raise SystemExit(2)
        metrics = summarize_navigation(
            evaluator.samples,
            arguments.goal_x,
            arguments.goal_y,
            succeeded=succeeded,
            recoveries=evaluator.recoveries,
        )
        map_cells = evaluator.map_width * evaluator.map_height
        metrics.update(
            {
                "goal_tolerance_m": arguments.goal_tolerance,
                "goal_within_tolerance": (
                    float(metrics["final_position_error_m"]) <= arguments.goal_tolerance
                ),
                "map_resolution_m": evaluator.map_resolution_m,
                "map_width_cells": evaluator.map_width,
                "map_height_cells": evaluator.map_height,
                "map_known_cells": evaluator.map_known_cells,
                "map_known_fraction": evaluator.map_known_cells / map_cells if map_cells else 0.0,
            }
        )
        _write_results(
            arguments.output_dir,
            evaluator.samples,
            metrics,
            arguments.goal_x,
            arguments.goal_y,
            arguments.goal_tolerance,
        )
        evaluator.get_logger().info(f"navigation result: {metrics}")
        raise SystemExit(0 if succeeded else 1)
    finally:
        evaluator.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
