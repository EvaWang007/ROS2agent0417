from setuptools import find_packages, setup

package_name = "nav_agent_ros2"

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
    maintainer="evawang",
    maintainer_email="1297991500@qq.com",
    description="ROSA-based Nav Agent for ROS2",
    license="Apache-2.0",
    extras_require={
        "test": ["pytest"],
    },
    entry_points={
        "console_scripts": [
            "nav_agent = nav_agent_ros2.nav_agent:main",
        ],
    },
)
