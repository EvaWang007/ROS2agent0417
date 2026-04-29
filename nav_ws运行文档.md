1.进入nav_ws文件夹

2. 先按你原流程启动 nav_ws 仿真/导航图
```
   ./start_sim.sh
```

4. 新开终端运行：
```
cd /home/evawang/Downloads/rosa-main
./run_nav_agent_ros2.sh
```
4.对LLM进行简单测试
```
先测这些问题：
List ROS2 nodes/topics/services in current graph.
Get one odom snapshot.
Get one scan snapshot.
```

***这些操作都是在rosa环境下***
可不可以理解为在BaseCallbackHandler中def的典型事件在Agent被执行到的时候Langchain框架会自动调用这个BaseCallbackHandler里面的函数把日志内容写入log_json
9:00 PM


对，完全可以这样理解。

更准确一点是：

你在 BaseCallbackHandler 子类里实现的 on_tool_start/on_tool_end/... 这些函数，是“事件回调”。
Agent 运行到对应阶段时，LangChain 会自动触发这些回调。
你在回调函数里调用 log_json(...)，就把当下上下文（工具名、输入、输出、耗时等）写进日志。
所以链路就是：
Agent执行事件 -> LangChain触发回调 -> 你的回调函数执行 -> log_json落盘。
