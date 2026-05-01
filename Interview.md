# Interview
下面这版你可以直接当“项目原理讲稿”。

## 1. Agent 整体 SOP（标准作业流）
1. 用户输入 query  
2. `ROSA.invoke()` 生成 `query_id`，记录 `query_start`  
3. （可选）长期记忆检索 top-k，拼接到输入上下文  
4. `create_tool_calling_agent` 驱动 LLM 决策：是否调用工具、调用哪个工具、参数是什么  
5. `AgentExecutor` 执行工具链（可能多步）  
6. callback hook 捕获 `tool_start/tool_end/error`，记录耗时和状态  
7. 得到最终答案，记录 `query_end/query_error`  
8. （可选）把 summary/fact/episodic 写回长期记忆  
9. 更新短期 `chat_history`（本会话记忆）

---

## 2. LangChain `tool_calling + AgentExecutor` 架构应用
- `create_tool_calling_agent(...)`：负责“规划与决策”（LLM脑）
- `AgentExecutor(...)`：负责“执行与循环”（工具执行器）
- 关键运行机制：
  - LLM 产出 tool call（name + args）
  - Executor 调用对应 Python tool
  - 结果回填给 LLM，进入下一轮推理
  - 直到输出 final answer 或达到迭代上限
- 你项目里的核心参数意义：
  - `max_iterations`：防止死循环
  - `handle_parsing_errors=True`：工具参数格式错误时容错
  - `return_intermediate_steps`：可返回中间轨迹（调试用）

---

## 3. Blacklist 安全约束机制
- 入口在 `ROSA._get_tools(...)`：工具集合由 `ROSATools` 构造
- `blacklist` 用来在注册阶段排除高风险工具（而不是运行后拦截）
- 本质是“能力面收敛”：
  - 不把危险工具暴露给 LLM
  - LLM 就无法在推理时选择它
- 安全价值：
  - 减少误调用风险
  - 可按场景（仿真/实机）切换黑名单策略

---

## 4. Prompt Engineering 约束设计
- 你是“系统约束先行”：
  - Persona：导航助手身份
  - Critical instruction：先观测 ROS 图，再给控制建议
  - Guardrails：动作小步、说明假设、清晰报告失败
- 技术原理：
  - 通过 system prompt 影响策略优先级
  - 把“先诊断后执行”变成默认决策路径
- 结果：
  - 降低盲目控制
  - 输出更可解释、更安全

---

## 5. AgentLoop 闭环框架（概念映射到你项目）
你当前实现已具备闭环雏形：
- Observe：hook 收集 trace/log
- Analyze：日志可按 `query_id` 回放工具链与耗时
- Improve：发现慢点/错误后改 prompt、工具或参数
- Memorize：把高价值信息沉淀到长期 memory（Phase1）
- Reuse：后续检索回灌，提升下一轮效果

对齐 AgentLoop 思想就是：
“运行数据 -> 评估清洗 -> 记忆沉淀 -> 在线回灌 -> 再评估”。

---

## 6. Hook / 日志检查机制
- Hook 实现：`BaseCallbackHandler` 子类
  - `on_tool_start`
  - `on_tool_end`
  - `on_tool_error`
- 日志分层：
  - `rosa_session.jsonl`：query 级事件
  - `rosa_tools.jsonl`：tool 级事件
- 关联主键：
  - `query_id` 贯穿 session/tools
- 检查方法：
  - 看 `query_start -> tool_start/end -> query_end` 是否完整
  - 看 `latency_ms` 找瓶颈
  - 看 `query_error/tool_error` 查失败路径

---

## 7. Memory 长短期记忆反馈链路
- 短期记忆（STM）：
  - `chat_history`，仅当前会话有效
- 长期记忆（LTM）：
  - JSONL/DB 持久化，跨会话可复用
- 反馈链路：
  1. invoke 前：`retrieve_memories(query)` 召回 top-k  
  2. 注入上下文：memory 作为先验知识参与本轮推理  
  3. invoke 后：抽取 summary/fact（后续可加 episodic）  
  4. 去重写回：hash 防重复，形成经验积累  
- 价值：
  - 从“单轮智能”升级到“跨会话学习”

---


## 8. MCP机制和tool calling机制
> 面试版回答
Host 中的 Agent 接收用户命令，并维护和多个 MCP Server 的连接。每个 MCP Server 会暴露自己的 tools/resources/prompts，Host 通过 MCP Client 获取这些能力，并将部分工具的 name、description、parameters schema 暴露给 LLM。LLM 根据用户问题决定是否调用工具以及调用哪个工具，并生成结构化工具调用参数。Host 将这个工具调用转交给对应的 MCP Client，Client 通过 MCP 协议向 MCP Server 发起 tools/call。Server 执行具体动作，例如查询本地数据库、读取 ROS2 状态、访问网页或操作文件系统，然后返回结构化结果。Host 再把工具结果放回 Agent 上下文，由 LLM 组织成最终回答

LLM结合用户命令和tool calling来生成 tool call，***🥑 reminds you!!!LLM 看到的是 Host 暴露后的工具，不一定是全部 MCP 工具!!!***

Host把这个tool call 转交给这个tool对应的Client，

Client再将这个tool call转换为`JSON-RPC`风格的通信请求发送给Server，

Server处理执行并返回结果给Client,再由Client返回给Host，Host返回给LLM生成面对用户的回答。

***其中，MCP作用的地方在于Client和Server的通信，而tool calling机制作用的地方在于给LLM暴露工具和执行工具并反馈的闭环机制***

🐻精炼成下面这个分层：

```text
用户命令
  ↓
LLM 根据 tool schema 决定是否 tool call
  ↓
Host 接收 tool call
  ↓
Host 路由到对应 MCP Client
  ↓
MCP Client 转成 JSON-RPC 请求
  ↓
MCP Server 执行工具
  ↓
Server 返回结果
  ↓
Client → Host → LLM
  ↓
LLM 组织最终回答
```

**tool calling 机制主要发生在 Host ↔ LLM 之间，负责“工具如何暴露给模型、模型如何表达调用、结果如何回填给模型”。**
**MCP 主要发生在 Client ↔ Server 之间，负责“工具如何被标准化发现、调用和返回结果”。**


```text
Tool Calling：模型层接口
MCP：工具接入层协议
Host：中间调度层
Server：工具执行层
```


> 🥑 reminds:LLM 看到的是 Host 暴露后的工具，不一定是全部 MCP 工具
> 
不是 MCP 自动筛选，**通常需要 Host/Agent 框架自己实现筛选策略**。

MCP 主要负责：

```text
Server 暴露工具
Client 获取工具列表
Client 调用工具
Server 返回结果
```

但 MCP 不负责判断：

```text
这个用户问题该暴露哪些工具给 LLM
哪些工具危险
哪些工具无关
哪些工具应该隐藏
```

这些属于 **Host 的工具路由 / 工具筛选逻辑**。

---

## Host 常见筛选方式(🥑)

### 1. 全量暴露

最简单：

```text
MCP Server 有多少工具，就全部给 LLM
```

缺点：

```text
工具太多
token 成本高
模型容易选错
危险工具可能被误调用
```

适合工具很少的 demo。

---

### 2. 白名单 / 黑名单

例如：

```text
允许暴露：
ros2_topic_list
get_scan_snapshot
get_robot_pose

禁止暴露：
publish_cmd_vel
delete_file
reset_simulation
```

适合机器人、安全敏感场景。

---

### 3. 按任务关键词筛选

用户问：

```text
获取 scan 快照
```

Host 只暴露：

```text
ros2_topic_list
get_scan_snapshot
```

用户问：

```text
让机器人去厨房
```

Host 暴露：

```text
send_nav_goal
get_robot_pose
get_map
```

---

### 4. 向量检索 / 语义检索筛选

把所有工具的：

```text
name
description
parameters
```

做 embedding。

用户问题来了之后，检索最相关的 Top-K 工具。

例如：

```text
query = "获取一帧激光雷达数据"
```

检索结果：

```text
get_scan_snapshot
ros2_topic_list
ros2_topic_echo
```

然后只把这些工具给 LLM。

---

### 5. LLM 先做工具路由

可以先让 LLM 判断：

```text
这个任务属于 ROS / 文件 / 数据库 / 浏览器 / GitHub？
```

再暴露对应工具组。

例如：

```text
用户问机器人状态 → ROS 工具组
用户问代码文件 → Filesystem 工具组
用户问网页信息 → Browser/Search 工具组
```

---

***In Conclusion***

在本工程里“暴露哪些工具给 LLM”的筛选机制是你们在 Host 侧实现的，核心就是这两层：

ROSA._get_tools(...) 的组装逻辑
先创建 ROSATools(ros_version, blacklist=...)
再 add_tools(...) / add_packages(...)
最终 self.__tools.get_tools() 才会传给 LLM
文件：rosa.py
```
blacklist 机制
这是显式剔除工具的策略（不注册就不可见）
属于“注册前过滤”
```
然后这份工具清单在：

create_tool_calling_agent(... tools=...)
AgentExecutor(... tools=...)
里生效。

```text
MCP 负责“有哪些工具”
Host 负责“给 LLM 看哪些工具”
LLM 负责“从可见工具里选哪个”
```




















