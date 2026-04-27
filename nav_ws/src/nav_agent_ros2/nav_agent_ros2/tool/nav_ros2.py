import threading
import time
from typing import Dict, Optional

import rclpy
from geometry_msgs.msg import Twist
from langchain.agents import tool
from nav_msgs.msg import Odometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class Runtime:
    def __init__(self):
        if not rclpy.ok():
            rclpy.init()
        self.node = Node("rosa_nav_tools_runtime")
        self.executor = MultiThreadedExecutor(num_threads=2)
        self.executor.add_node(self.node)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()
        self.pubs: Dict[str, object] = {}

    def ensure_pub(self, topic: str):
        if topic not in self.pubs:
            self.pubs[topic] = self.node.create_publisher(Twist, topic, 10)


_runtime: Optional[Runtime] = None


def rt() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime


@tool
def get_odom_snapshot(topic: str = "/odom", timeout_sec: float = 2.0) -> dict:
    """Get a one-shot odometry snapshot from a topic (default: /odom)."""
    done = threading.Event()
    data = {}

    def cb(msg: Odometry):
        data["frame_id"] = msg.header.frame_id
        data["child_frame_id"] = msg.child_frame_id
        data["position"] = {
            "x": msg.pose.pose.position.x,
            "y": msg.pose.pose.position.y,
            "z": msg.pose.pose.position.z,
        }
        data["orientation"] = {
            "x": msg.pose.pose.orientation.x,
            "y": msg.pose.pose.orientation.y,
            "z": msg.pose.pose.orientation.z,
            "w": msg.pose.pose.orientation.w,
        }
        data["linear_velocity"] = {
            "x": msg.twist.twist.linear.x,
            "y": msg.twist.twist.linear.y,
            "z": msg.twist.twist.linear.z,
        }
        data["angular_velocity"] = {
            "x": msg.twist.twist.angular.x,
            "y": msg.twist.twist.angular.y,
            "z": msg.twist.twist.angular.z,
        }
        done.set()

    sub = rt().node.create_subscription(Odometry, topic, cb, 10)
    ok = done.wait(timeout_sec)
    rt().node.destroy_subscription(sub)
    if not ok:
        return {"error": f"No odometry message received on {topic} within {timeout_sec}s."}
    return data


@tool
def get_scan_snapshot(topic: str = "/scan", timeout_sec: float = 2.0, samples: int = 10) -> dict:
    """Get a one-shot laser scan snapshot and return up to N sample ranges."""
    done = threading.Event()
    data = {}

    def cb(msg: LaserScan):
        sample_count = max(1, min(int(samples), len(msg.ranges)))
        data["frame_id"] = msg.header.frame_id
        data["angle_min"] = msg.angle_min
        data["angle_max"] = msg.angle_max
        data["range_min"] = msg.range_min
        data["range_max"] = msg.range_max
        data["sample_ranges"] = [float(v) for v in msg.ranges[:sample_count]]
        done.set()

    sub = rt().node.create_subscription(LaserScan, topic, cb, 10)
    ok = done.wait(timeout_sec)
    rt().node.destroy_subscription(sub)
    if not ok:
        return {"error": f"No scan message received on {topic} within {timeout_sec}s."}
    return data


@tool
def publish_cmd_vel(
    linear_x: float = 0.05,
    angular_z: float = 0.0,
    duration_sec: float = 0.5,
    topic: str = "/cmd_vel",
) -> dict:
    """Publish a small cmd_vel command for a short duration (default topic: /cmd_vel)."""
    duration = max(0.1, min(float(duration_sec), 3.0))

    rt().ensure_pub(topic)
    msg = Twist()
    msg.linear.x = float(linear_x)
    msg.angular.z = float(angular_z)

    start = time.time()
    while time.time() - start < duration:
        rt().pubs[topic].publish(msg)
        time.sleep(0.1)

    stop = Twist()
    rt().pubs[topic].publish(stop)

    return {
        "status": "published",
        "topic": topic,
        "linear_x": float(linear_x),
        "angular_z": float(angular_z),
        "duration_sec": duration,
    }
