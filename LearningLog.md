## 功能实现
1. 启动脚本`./run_agent_ros2.sh`
2. 出现 `>`输入文本可以与agent进行交互，控制🐢的移动等
3. 输入exit退出交互

## 环境问题处理
***1. ROS2环境和rosa环境不匹配*** 

ROS2的运行环境是在系统`/usr/bin/python3`下，我的turtle_agent_ros2个入口脚本是构建时也是 ROS2/colcon 生成的。

当前这套 ROS2 工具链用的是系统 Python，所以 ***shebang 🥑explains later***固定成 #!/usr/bin/python3

所以即使你激活了 conda，它也不会自动改这个 shebang

Solution:

在 agent.launch.py 给 agent 节点加 prefix
把 agent 节点改成这样：
```
agent_node = Node(
    package="turtle_agent_ros2",
    executable="turtle_agent",
    name="rosa_turtle_agent_ros2",
    output="screen",
    prefix="/home/evawang/miniconda3/envs/rosa/bin/python",
)
``` 
这样 launch 时会用你的 rosa 环境 Python 执行脚本。


🥑 tells you what is ***shebang** and ***prefix***

shebang是脚本文件的第一行字符串比如:`#!usr/bin/python3`，目的是告诉操作系统不要用默认方式而是用这个字符串所提供的绝对路径解释器运行

prefix 的作用是：在启动节点命令前加一个“前缀命令”。

```
默认 ros2 launch 启动 turtle_agent 时会走脚本 shebang（/usr/bin/python3）。
这会导致用系统 Python 跑，找不到你 conda rosa 里的依赖。
所以我让你加 prefix="/home/.../envs/rosa/bin/python"，相当于强制变成：
rosa环境python + turtle_agent脚本
结果就是节点运行时用的是 rosa 环境，langchain、你的包依赖都能被找到。
```
## tools函数设置问题
用 @tool 装饰的函数（先是 get_turtle_pose）必须有 docstring，以下是标准的tools模板
```
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.# 这里就是docstring

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```
来自Langchain文档：By default, ***the function’s docstring*** becomes the tool’s description that helps the model understand when to use it:





