#!/usr/bin/env bash
set -eo pipefail

ROOT="/home/evawang/Downloads/rosa-main/nav_ws"

# Ensure this script always runs with system Python/ROS env, not conda Python.
if command -v conda >/dev/null 2>&1; then
  conda deactivate 2>/dev/null || true
fi
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PROMPT_MODIFIER CONDA_SHLVL CONDA_EXE CONDA_PYTHON_EXE || true
export COLCON_PYTHON_EXECUTABLE=/usr/bin/python3
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
# Avoid unbound variable errors when sourcing ROS setup with `set -u`.
export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES:-}"
export AMENT_PYTHON_EXECUTABLE="${AMENT_PYTHON_EXECUTABLE:-/usr/bin/python3}"

cleanup() {
  echo -e "\n[INFO] 检测到中断信号，正在关闭所有 ROS 节点..."
  kill $(jobs -p) 2>/dev/null || true
  echo "[INFO] 所有任务已停止，退出脚本。"
  exit 0
}
trap cleanup SIGINT SIGTERM

cd "$ROOT"

echo "[INFO] Sourcing ROS environments..."
source /opt/ros/humble/setup.bash
source "$ROOT/install/setup.bash"

echo "[INFO] 清理上次的仿真残余..."
killall -9 gzserver gzclient static_transform_publisher 2>/dev/null || true

echo "[INFO] Gazebo model setup..."
TARGET_DIR="$HOME/.gazebo/models/robot_description"
mkdir -p "$TARGET_DIR"
cp -r src/robot_description/meshes "$TARGET_DIR/" 2>/dev/null || true

cd "$TARGET_DIR"
# Keep meshes directory only; remove other stale files/directories.
find . -mindepth 1 -maxdepth 1 ! -name meshes -exec rm -rf {} + 2>/dev/null || true
cd "$ROOT"

echo "[INFO] Launching house_sim..."
ros2 launch robot_simulation house_sim.launch.py use_sim_time:=True &
sleep 5

echo "[INFO] Launching navigation..."
ros2 launch robot_simulation autonomous_navigation.launch.py use_sim_time:=True &
sleep 2

echo "[INFO] Running robot patrol..."
ros2 run robot_patrol robot_patrol use_sim_time:=True
