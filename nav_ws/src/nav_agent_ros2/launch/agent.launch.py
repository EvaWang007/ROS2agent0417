import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    streaming_arg = DeclareLaunchArgument("streaming", default_value="false")

    set_streaming_env = SetEnvironmentVariable(
        name="ROSA_STREAMING",
        value=LaunchConfiguration("streaming"),
    )

    agent_node = Node(
        package="nav_agent_ros2",
        executable="nav_agent",
        name="rosa_nav_agent_ros2",
        output="screen",
        respawn=False,
        prefix=os.getenv("ROSA_PYTHON", "/home/evawang/miniconda3/envs/rosa/bin/python"),
    )

    return LaunchDescription([
        streaming_arg,
        set_streaming_env,
        agent_node,
    ])
