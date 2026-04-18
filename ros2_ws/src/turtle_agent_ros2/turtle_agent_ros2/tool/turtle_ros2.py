import time
import threading
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty
from turtlesim.msg import Pose
from turtlesim.srv import TeleportAbsolute
from langchain.agents import tool


class Runtime:
    def __init__(self):
        if not rclpy.ok():
            rclpy.init()
        self.node = Node("rosa_turtle_tools_runtime")
        self.executor = MultiThreadedExecutor(num_threads=2)
        self.executor.add_node(self.node)
        self.thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.thread.start()
        self.pubs: Dict[str, any] = {}

    def ensure_pub(self, name: str):
        name = name.replace("/", "")
        if name not in self.pubs:
            self.pubs[name] = self.node.create_publisher(Twist, f"/{name}/cmd_vel", 10)

    def call_service(self, service_name: str, srv_type, req, timeout_sec: float = 3.0):
        client = self.node.create_client(srv_type, service_name)
        if not client.wait_for_service(timeout_sec=timeout_sec):
            return False, f"Service not available: {service_name}"
        future = client.call_async(req)
        start = time.time()
        while not future.done():
            if time.time() - start > timeout_sec:
                return False, f"Service timeout: {service_name}"
            time.sleep(0.01)
        if future.result() is None:
            return False, f"Service failed: {service_name}"
        return True, future.result()

    def get_pose(self, name: str, timeout_sec: float = 2.0):
        topic = f"/{name}/pose"
        done = threading.Event()
        data = {}

        def cb(msg: Pose):
            data["x"] = msg.x
            data["y"] = msg.y
            data["theta"] = msg.theta
            done.set()

        sub = self.node.create_subscription(Pose, topic, cb, 10)
        ok = done.wait(timeout_sec)
        self.node.destroy_subscription(sub)
        if not ok:
            return False, f"Pose timeout: {topic}"
        return True, data


_runtime: Optional[Runtime] = None


def rt() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime


def within_bounds(x: float, y: float) -> bool:
    return 0.0 <= x <= 11.0 and 0.0 <= y <= 11.0


@tool
def get_turtle_pose(names: List[str]) -> dict:
    """Get pose information for one or more turtles"""
    out = {}
    for name in names:
        n = name.replace("/", "")
        ok, pose = rt().get_pose(n)
        out[n] = pose if ok else {"error": pose}
    return out


@tool
def teleport_absolute(name: str, x: float, y: float, theta: float) -> str:
    """Teleport turtle to an absolute pose (x,y,theta)"""
    if not within_bounds(x, y):
        return f"Out of bounds: ({x}, {y})"
    n = name.replace("/", "")
    req = TeleportAbsolute.Request()
    req.x = float(x)
    req.y = float(y)
    req.theta = float(theta)
    ok, res = rt().call_service(f"/{n}/teleport_absolute", TeleportAbsolute, req)
    if not ok:
        return res
    ok_pose, pose = rt().get_pose(n)
    return str(pose) if ok_pose else pose


@tool
def publish_twist_to_cmd_vel(name: str, velocity: float, angle: float = 0.0, steps: int = 1) -> str:
    """Publish Twist messages to /<name>/cmd_vel to move the turtle"""
    n = name.replace("/", "")
    rt().ensure_pub(n)
    msg = Twist()
    msg.linear.x = float(velocity)
    msg.angular.z = float(angle)
    for _ in range(max(1, int(steps))):
        rt().pubs[n].publish(msg)
        time.sleep(1.0)
    ok_pose, pose = rt().get_pose(n)
    return str(pose) if ok_pose else pose


@tool
def clear_turtlesim() -> str:
    """Clear all drawings in turtlesim (calls /clear service)"""
    req = Empty.Request()
    ok, res = rt().call_service("/clear", Empty, req)
    return "cleared" if ok else str(res)


@tool
def reset_turtlesim() -> str:
    """Reset turtlesim to initial state using the /reset service"""
    req = Empty.Request()
    ok, res = rt().call_service("/reset", Empty, req)
    return "reset done" if ok else str(res)
