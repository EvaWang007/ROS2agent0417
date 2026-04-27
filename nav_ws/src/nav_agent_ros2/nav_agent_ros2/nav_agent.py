import asyncio
import os

import pyinputplus as pyip
from rosa import ROSA

from .help import get_help
from .llm import get_llm
from .prompts import get_prompts
from .tool import nav_ros2


class NavAgentROS2(ROSA):
    def __init__(self, streaming: bool = False):
        super().__init__(
            ros_version=2,
            llm=get_llm(streaming=streaming),
            tool_packages=[nav_ros2],
            prompts=get_prompts(),
            streaming=streaming,
            verbose=False,
            accumulate_chat_history=True,
        )
        self.streaming = streaming
        self.examples = [
            "List ROS2 nodes/topics/services in current graph.",
            "Get one odom snapshot.",
            "Get one scan snapshot.",
            "Publish a tiny cmd_vel command for 0.5 seconds.",
            "Run ros2 doctor and summarize issues.",
        ]


def main():
    streaming = os.getenv("ROSA_STREAMING", "false").lower() == "true"
    agent = NavAgentROS2(streaming=streaming)

    while True:
        query = pyip.inputStr("> ", default="help")
        if query == "exit":
            break
        if query == "clear":
            agent.clear_chat()
            continue
        if query == "examples":
            print("\n".join(agent.examples))
            continue
        if query == "help":
            print(get_help(agent.examples))
            continue

        if streaming:
            async def run_stream():
                async for event in agent.astream(query):
                    if event["type"] == "token":
                        print(event["content"], end="", flush=True)
                    elif event["type"] == "final":
                        print()

            asyncio.run(run_stream())
        else:
            print(agent.invoke(query))
