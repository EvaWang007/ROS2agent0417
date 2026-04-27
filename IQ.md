## Blacklist机制
> 原理
`blacklist` 一般叫 **黑名单**。

它的核心含义是：

**把某些“不允许通过”的对象列出来，命中后就拒绝。**

---

最直观的理解

你可以把它理解成一个“禁止名单”。

比如有一个列表：

```text
["topic_a", "topic_b", "private_node"]
```

意思就是：

* 如果请求里出现 `topic_a`
* 或者出现 `topic_b`
* 或者出现 `private_node`

那系统就不允许访问、执行或返回这些内容。

---

> 在程序里它通常起什么作用

1. 限制访问

比如：

* 不允许访问某些文件
* 不允许调用某些接口
* 不允许读取某些 ROS topic / node

2. 做安全控制

比如：

* 防止用户操作敏感资源
* 防止 agent 调用高风险工具
* 防止访问私有数据

3. 过滤输出

比如：

* 返回结果里如果包含黑名单项，就隐藏掉
* 工具调用前如果参数命中黑名单，就直接拒绝

---

> 一个简单例子

假设你有个工具：

```python
def read_topic(topic_name):
    ...
```

你希望某些 topic 不允许读取：

```python
blacklist = ["/camera/raw", "/private/debug"]
```

那逻辑可以是：

```python
if topic_name in blacklist:
    raise ValueError("不允许访问该 topic")
```

意思就是：

* 普通 topic 可以读
* 黑名单里的 topic 不可以读

---

> 在 ROSA 里的 blacklist 起到什么作用


***限制 agent 不要访问某些敏感 ROS 资源。***


> 1. 结论

在 `tools/__init__.py` 里，ROSA 收集工具时会检查：

* 这个对象是不是 LangChain Tool
* 这个 tool 对应的函数签名里**有没有 `blacklist` 参数**

如果有，就会通过 `inject_blacklist(...)` 包一层，把初始化时传进来的黑名单自动塞进去。
如果没有，就原样加入工具池。

所以区别是：

***有 `blacklist` 的工具***

* 会被自动注入黑名单
* 工具内部可以根据自己写的blacklist=[]覆盖拒绝访问某些资源
* 属于“带安全限制的工具”

***没有 `blacklist` 的工具***

* 不会被注入黑名单
* 工具内部没有这层统一限制
* 属于“普通工具”

---

> 2. LLM 调用时有什么区别

这里最容易误解。



LLM 并不会显式地想：

* “这个工具有 blacklist”
* “那个工具没有 blacklist”

LLM 看到的主要还是：

* 工具名称
* 工具描述
* 工具参数 schema

它还是正常决定：

* 要不要调用这个工具
* 传什么业务参数进去

也就是说：

 **LLM 的“选择动作”基本不变。**

---

从实际执行视角看

真正的区别发生在 **工具执行阶段**。

对没有 `blacklist` 的工具

LLM 调什么，它就直接执行什么。

***对有 `blacklist` 的工具***

LLM 虽然还是只传业务参数，比如 `topic_name="/camera/raw"`，
但 ROSA 会在后台自动把 blacklist 一起传进去，比如：

```python id="hzgjo6"
tool_func(topic_name="/camera/raw", blacklist=["/camera/raw", "/private/debug"])
```

然后工具函数内部自己判断：

* 如果命中黑名单，就拒绝
* 如果没命中，就继续执行

所以：

**LLM 的调用方式表面上差不多，但带 `blacklist` 的工具在执行时多了一层自动安全过滤。**

---


> 4. 举一个更贴近 ROS 场景的🌰

---

***工具 1：列出 topic 列表***

```python id="f7qmht"
@tool
def ros2_topic_list() -> list[str]:
    """Return all ROS2 topics."""
    return ["/scan", "/odom", "/camera/raw", "/private/debug"]
```

特点

* 没有 blacklist 参数
* ROSA 不会给它注入黑名单
* LLM 调用它时，就直接返回全部 topic

所以结果可能包含：

* `/camera/raw`
* `/private/debug`

---

***工具 2：读取某个 topic 的详细内容***

```python id="wi0l8c"
@tool
def ros2_topic_echo(topic_name: str, blacklist: list[str] = None) -> str:
    """Read one message from a ROS2 topic."""
    if blacklist and topic_name in blacklist:
        return f"Access denied: {topic_name}"
    return f"message from {topic_name}"
```

特点

* 有 blacklist 参数
* ROSA 会自动注入 blacklist
* LLM 如果想读黑名单 topic，会被拦住

---

***运行时会发生什么***

假设 blacklist 是：

```python id="xixgbv"
["/camera/raw", "/private/debug"]
```

第一步：LLM 调 `ros2_topic_list()`

结果：

```text id="n7n1jf"
["/scan", "/odom", "/camera/raw", "/private/debug"]
```

这里不会自动过滤，因为这个工具没写 blacklist 逻辑。

第二步：LLM 看到 `/camera/raw`，又去调 `ros2_topic_echo("/camera/raw")`

表面上它只传了 `topic_name="/camera/raw"`。

但实际执行时 ROSA 自动补成：

```python id="c3rexy"
ros2_topic_echo("/camera/raw", blacklist=["/camera/raw", "/private/debug"])
```

于是工具返回：

```text id="ck3o2z"
Access denied: /camera/raw
```
说明两点：
```
第一

**blacklist 是否生效，不取决于 LLM 会不会“记住规则”，而取决于工具本身是否支持 blacklist 参数。**

第二

**同一个黑名单，对不同工具是否生效，要看工具有没有按 ROSA 的约定接入 blacklist。**

这就是工程上很重要的地方：

```
* 不是“全局自动拦所有工具”
* 而是“只拦那些显式支持 blacklist 的工具”
```text
```
>🪄In Conclusion:
> 使用blacklist注入机制的tools在被LLM调用的时候，被blacklist覆盖的参数是无法被LLM访问的，该机制的主要目的带 blacklist 的工具在执行时会自动附加黑名单约束，从而阻止 agent 访问某些敏感或不允许暴露的资源






## nav_ws和ROSA_MAIN的python3运行环境不同的问题解决

> ***“环境隔离 + 脚本固化”解决的，核心做法有 4 点：***

1. 明确根因  
- `nav_ws` 构建时被 `rosa` conda 环境污染，`ament/cmake` 走了 conda Python。  
- 这会触发 `catkin_pkg` 等模块缺失或行为差异，导致构建/启动异常。

2. 强制 `nav_ws` 使用系统 Python  
- 在脚本里固定：
  - `COLCON_PYTHON_EXECUTABLE=/usr/bin/python3`
  - `AMENT_PYTHON_EXECUTABLE=/usr/bin/python3`
  - `source /opt/ros/humble/setup.bash`
- 并清理 conda 影响（`conda deactivate` + `unset CONDA_*`）。

3. 拆成两套脚本，避免混用  
- [build_nav.sh](/home/evawang/Downloads/rosa-main/nav_ws/build_nav.sh)：专门清理并编译 `nav_ws`（系统 Python）。  
- [start_sim.sh](/home/evawang/Downloads/rosa-main/nav_ws/start_sim.sh)：专门启动仿真与导航（系统 Python）。  
- 这样 `nav_ws` 生命周期都在一致环境里运行。

4. 处理 ROS setup 脚本兼容性  
- 发现 `set -u` 会让 ROS/colcon 的 `setup.bash` 因未定义变量报错（`AMENT_TRACE_SETUP_FILES`、`AMENT_PYTHON_EXECUTABLE`、`COLCON_TRACE`）。  
- 最终改为 `set -eo pipefail`，并补默认变量，保证稳定启动。

最终效果：
1. `nav_ws` 可以干净重编译并成功运行。  
2. `ROSA_MAIN` 的 `rosa` 环境保留给 Agent/LLM 运行，不再干扰 `nav_ws` 的 ROS 构建与仿真。  
3. 两个项目在同机并存，职责清晰、可重复执行。












