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
