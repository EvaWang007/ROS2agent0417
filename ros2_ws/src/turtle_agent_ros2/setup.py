from setuptools import setup, find_packages

package_name = "turtle_agent_ros2"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/agent.launch.py"]),
    ],
    install_requires=[
        "setuptools",
        "python-dotenv",
        "langchain",
        "langchain-core",
        "langchain-community",
        "langchain-openai",
        "rich",
        "pyinputplus",
        "jpl-rosa",
    ],
    zip_safe=True,
    maintainer="you",
    maintainer_email="you@example.com",
    description="ROSA-based TurtleSim agent for ROS2",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "turtle_agent = turtle_agent_ros2.turtle_agent:main",
        ],
    },
)

