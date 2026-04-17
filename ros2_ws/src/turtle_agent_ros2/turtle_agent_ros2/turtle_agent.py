import asyncio
import os
import pyinputplus as pyip

from rosa import ROSA
from .llm import get_llm
from .prompts import get_prompts
from .help import get_help
from .tools import turtle_ros2


class TurtleAgentROS2(ROSA):
    def __init__(self, streaming: bool = False):
        super().__init__(
            ros_version=2,
            llm=get_llm(streaming=streaming),
            tool_packages=[turtle_ros2],
            prompts=get_prompts(),
            streaming=streaming,
            verbose=False,
            accumulate_chat_history=True,
        )
        self.streaming = streaming
        self.examples = [
            "List ROS2 topics.",
            "Get pose of turtle1.",
            "Teleport turtle1 to x=3 y=3 theta=1.57.",
            "Move turtle1 forward 2 steps.",
            "Reset turtlesim.",
        ]


def main():
    streaming = os.getenv("ROSA_STREAMING", "false").lower() == "true"
    agent = TurtleAgentROS2(streaming=streaming)

    while True:
        q = pyip.inputStr("> ", default="help")
        if q == "exit":
            break
        if q == "clear":
            agent.clear_chat()
            continue
        if q == "examples":
            print("\n".join(agent.examples))
            continue
        if q == "help":
            print(get_help(agent.examples))
            continue

        if streaming:
            async def run():
                async for event in agent.astream(q):
                    if event["type"] == "token":
                        print(event["content"], end="", flush=True)
                    elif event["type"] == "final":
                        print()
            asyncio.run(run())
        else:
            print(agent.invoke(q))
