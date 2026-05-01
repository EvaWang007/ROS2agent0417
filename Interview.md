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
