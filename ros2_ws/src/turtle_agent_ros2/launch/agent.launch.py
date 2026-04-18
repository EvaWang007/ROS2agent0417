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

    turtlesim_node = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name="turtlesim",
        output="screen",
    )

    agent_node = Node(
        package="turtle_agent_ros2",
        executable="turtle_agent",
        name="rosa_turtle_agent_ros2",
        output="screen",
        respawn=False,
        prefix="/home/evawang/miniconda3/envs/rosa/bin/python",
    )

    return LaunchDescription([
        streaming_arg,
        set_streaming_env,
        turtlesim_node,
        agent_node,
    ])
