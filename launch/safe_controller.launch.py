from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("turtlebot3_multimodal"))
    return LaunchDescription(
        [
            Node(
                package="turtlebot3_multimodal",
                executable="safe_controller",
                name="safe_multimodal_controller",
                output="screen",
                parameters=[str(share / "config" / "safety.yaml")],
            )
        ]
    )
