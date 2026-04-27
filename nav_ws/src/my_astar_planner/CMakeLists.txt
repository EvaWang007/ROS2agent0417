cmake_minimum_required(VERSION 3.8)
project(my_astar_planner)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++17)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_util REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)



# 2. 【新增】定义编译目标：将你的源文件编译成一个动态库 (.so)
# 这里的 src/my_astar_planner.cpp 必须和你实际的文件名一致
add_library(my_astar_planner_lib SHARED
  src/my_astar_planner.cpp
)


# 3. 【新增】指定头文件目录
target_include_directories(my_astar_planner_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# 4. 【新增】将你的库与 Nav2 等依赖库链接起来
# 这步解决了你看到的 #include 报错问题
ament_target_dependencies(my_astar_planner_lib
  nav2_core
  nav2_util
  nav_msgs
  pluginlib
  rclcpp
  geometry_msgs
)


#5. 【新增】导出插件描述文件 (plugins.xml)
pluginlib_export_plugin_description_file(nav2_core plugins.xml)

# 6. 【新增】安装规则（确保 colcon build 后文件能被放到正确位置）
install(TARGETS my_astar_planner_lib
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
  DESTINATION lib
)

install(DIRECTORY include/
  DESTINATION include
)









if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
