## Step1
终端1：cd进入nav_ws
      
      运行仿真 `./start_sim.sh`
## Step2
终端2： 运行agent开始提问`./run_nav_agent_ros2.sh`

## Step3
终端3： 运行日志阅读`./show_last_session.sh`

## 日志阅读脚本运行原理

核心思路：**用 `query_id` 做关联键**。

你可以这样回答面试官：

1. 脚本先读取 `session` 日志最后一行  
- 用 `tail -n 1 rosa_session.jsonl` 拿到最新事件。  
- 这行里包含最新会话的 `query_id`。

2. 从最后一行里提取 `query_id`  
- 用 `sed` 正则提取 `"query_id": "..."`。  
- 这个 `query_id` 是一次会话的唯一标识。

3. 用同一个 `query_id` 去两份日志里过滤  
- 在 `rosa_session.jsonl` 里 grep：拿到这次会话的 `query_start/query_end/query_error`。  
- 在 `rosa_tools.jsonl` 里 grep：拿到这次会话触发的全部 `tool_start/tool_end/tool_error`。  
- 这样就实现了“只看最新一次会话的问题和工具调用”。

4. 为什么可靠  
- 因为 session 日志和 tools 日志都写入同一个 `query_id`，形成跨文件可追踪链路。  
- 即使文件里混有历史会话，也不会串，因为过滤条件是唯一 ID，不是时间窗口猜测。

你可以补一句工程化亮点：  
“这相当于实现了一个轻量级 trace 机制，`query_id` 是 trace id，能够把用户请求与工具调用全链路关联起来，便于调试和审计。”
