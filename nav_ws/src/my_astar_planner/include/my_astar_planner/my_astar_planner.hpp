#ifndef MY_ASTAR_PLANNER_HPP_
#define MY_ASTAR_PLANNER_HPP_

#include <string>
#include <vector>
#include "nav2_core/global_planner.hpp" // 核心库：所有全局规划器插件必须继承这个基类
#include "nav_msgs/msg/path.hpp"        // 消息类型：ROS 2 标准路径消息
#include "nav2_util/lifecycle_node.hpp" // 生命周期管理：Nav2 用来控制节点启动/停止

namespace my_astar_namespace
{
// 我们的类 MyAStarPlanner 继承自 nav2_core::GlobalPlanner
class MyAStarPlanner : public nav2_core::GlobalPlanner
{
public:
  // 1. 初始化函数：当 Nav2 启动时调用，传入地图、坐标变换 buffer 等参数
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;

  // 2. 清理函数：插件卸载时调用
  void cleanup() override;
  
  // 3. 激活函数：当机器人导航进入 Active 状态时调用
  void activate() override;
  
  // 4. 停用函数：导航挂起时调用
  void deactivate() override;

  // 5. 核心函数：输入起点和终点，输出计算出的 A* 路径
  nav_msgs::msg::Path createPlan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal) override;

private:
  // 定义一个指针，用来直接操作 Nav2 的代价地图（2D 网格数据）
  nav2_costmap_2d::Costmap2D * costmap_;
  std::string name_; // 插件名称
};
}
#endif