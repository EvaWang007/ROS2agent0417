#include "my_astar_planner/my_astar_planner.hpp"
#include "pluginlib/class_list_macros.hpp" // 必须包含：用于动态加载插件的宏

namespace my_astar_namespace
{
// --- 1. 配置逻辑 ---
void MyAStarPlanner::configure(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  std::string name, std::shared_ptr<tf2_ros::Buffer> /*tf*/,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)
{
  name_ = name;
  // 从输入的 costmap_ros 对象中提取底层的 Costmap2D 原始数据
  // 这样我们才能用 getCost(x, y) 来读取地图障碍物
  costmap_ = costmap_ros->getCostmap();
}

// --- 2. 状态切换逻辑（目前保持为空即可） ---
void MyAStarPlanner::cleanup() {}
void MyAStarPlanner::activate() {}
void MyAStarPlanner::deactivate() {}


// 定义节点结构
struct Node {
  unsigned int index;
  float g;
  float h;
  unsigned int parent;
  float f() const { return g + h; }
};

// 比较器：用于优先级队列，f 值小的优先
struct CompareNodes {
  bool operator()(const Node& a, const Node& b) { return a.f() > b.f(); }
};


// --- 3. 路径搜索逻辑（A* 算法入口） ---
nav_msgs::msg::Path MyAStarPlanner::createPlan(
  const geometry_msgs::msg::PoseStamped & start,
  const geometry_msgs::msg::PoseStamped & goal)
{
  nav_msgs::msg::Path global_path;
  global_path.header.stamp = rclcpp::Clock().now();
  global_path.header.frame_id = start.header.frame_id;


  // 1. 坐标转换
  unsigned int mx_start, my_start, mx_goal, my_goal;
  if (!costmap_->worldToMap(start.pose.position.x, start.pose.position.y, mx_start, my_start) ||
      !costmap_->worldToMap(goal.pose.position.x, goal.pose.position.y, mx_goal, my_goal)) {
    return global_path;
  }

  // 2. 初始化数据结构
  unsigned int width = costmap_->getSizeInCellsX();
  unsigned int start_idx = costmap_->getIndex(mx_start, my_start);
  unsigned int goal_idx = costmap_->getIndex(mx_goal, my_goal);

  std::priority_queue<Node, std::vector<Node>, CompareNodes> open_list;
  std::unordered_map<unsigned int, Node> all_nodes; // 记录访问过的节点和代价

  // 放入起点
  open_list.push({start_idx, 0.0, 0.0, start_idx});
  all_nodes[start_idx] = {start_idx, 0.0, 0.0, start_idx};

  bool found_goal = false;

  // --- 调试专用的“转圈圈”逻辑 ---说明我的算法被正确调用了
    // 创建一个临时发布者，向 /cmd_vel 发送速度指令
    auto node = rclcpp::Node::make_shared("debug_spinner");
    auto pub = node->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);
    
    geometry_msgs::msg::Twist twist;
    twist.angular.z = 0.5; // 设置角速度，让机器人转起来
    
    RCLCPP_INFO(rclcpp::get_logger("MyAStarPlanner"), "A* 插件已激活，机器人开始转圈调试！！！");
    
    // 持续发布一秒钟的转圈指令
    rclcpp::Rate loop_rate(10);
    for(int i=0; i<10; ++i) {
        pub->publish(twist);
        loop_rate.sleep();
    }
    
    // 停止机器人
    twist.angular.z = 0.0;
    pub->publish(twist);
    // --- 调试逻辑结束 ---

  // 3. A* 主循环
  while (!open_list.empty()) {
    Node current = open_list.top();
    open_list.pop();

    if (current.index == goal_idx) {
      found_goal = true;
      break;
    }

    // 获取当前点的 2D 坐标
    unsigned int cur_x, cur_y;
    costmap_->indexToCells(current.index, cur_x, cur_y);

    // 检查 8 个相邻方向
    for (int dx = -1; dx <= 1; dx++) {
      for (int dy = -1; dy <= 1; dy++) {
        if (dx == 0 && dy == 0) continue;

        unsigned int nx = cur_x + dx;
        unsigned int ny = cur_y + dy;

        // 边界检查
        if (nx >= costmap_->getSizeInCellsX() || ny >= costmap_->getSizeInCellsY()) continue;

        // 障碍物检查
        unsigned char cost = costmap_->getCost(nx, ny);
        if (cost >= nav2_costmap_2d::LETHAL_OBSTACLE) continue; // 254 为障碍物

        unsigned int next_idx = costmap_->getIndex(nx, ny);
        float move_cost = std::sqrt(dx * dx + dy * dy); // 直线 1.0，斜角 1.414
        float new_g = current.g + move_cost + (cost / 255.0f); // 加入地图代价权重

        // 如果点没访问过，或者发现了更短的路径
        if (all_nodes.find(next_idx) == all_nodes.end() || new_g < all_nodes[next_idx].g) {
          float h = std::hypot((int)nx - (int)mx_goal, (int)ny - (int)my_goal); // 欧几里得启发式
          all_nodes[next_idx] = {next_idx, new_g, h, current.index};
          open_list.push(all_nodes[next_idx]);
        }
      }
    }
  }

  // 4. 回溯路径
  if (found_goal) {
    unsigned int curr = goal_idx;
    while (curr != start_idx) {
      unsigned int mx, my;
      costmap_->indexToCells(curr, mx, my);
      
      geometry_msgs::msg::PoseStamped pose;
      costmap_->mapToWorld(mx, my, pose.pose.position.x, pose.pose.position.y);
      pose.header = global_path.header;
      global_path.poses.push_back(pose);
      
      curr = all_nodes[curr].parent;
    }
    std::reverse(global_path.poses.begin(), global_path.poses.end());
  }

  return global_path;
}
} // namespace 关闭

// 极其重要的一行：向系统注册这个插件，这样 Nav2 才能通过名字找到它
PLUGINLIB_EXPORT_CLASS(my_astar_namespace::MyAStarPlanner, nav2_core::GlobalPlanner)