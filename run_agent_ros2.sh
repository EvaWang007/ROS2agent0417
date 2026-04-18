#!/usr/bin/env bash
set -eo pipefail

ROOT="$HOME/Downloads/rosa-main"
WS="$ROOT/ros2_ws"
CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"
ROSA_PY="$HOME/miniconda3/envs/rosa/bin/python"
AGENT_BIN="$WS/install/turtle_agent_ros2/lib/turtle_agent_ros2/turtle_agent"
# avoid unbound var error when sourcing ROS setup with `set -u`
export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES:-}"

source /opt/ros/humble/setup.bash

# 1) activate conda env
source "$CONDA_SH"
conda activate rosa

# 2) source ROS
source /opt/ros/humble/setup.bash

# 3) build
cd "$WS"
colcon build --packages-select turtle_agent_ros2 --symlink-install

# 4) source workspace
source "$WS/install/setup.bash"

# 5) ensure ROSA package is importable
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

# optional: DeepSeek defaults
export LLM_PROVIDER="${LLM_PROVIDER:-deepseek}"

# cleanup on exit
cleanup() {
  echo "Stopping turtlesim..."
  if [[ -n "${TURTLESIM_PID:-}" ]]; then
    kill "$TURTLESIM_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# 6) start turtlesim (background)
ros2 run turtlesim turtlesim_node &
TURTLESIM_PID=$!
sleep 2

# 7) start agent (foreground)
exec "$ROSA_PY" "$AGENT_BIN"
