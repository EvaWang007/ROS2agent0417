#!/usr/bin/env bash
set -eo pipefail

ROOT="$HOME/Downloads/rosa-main"
WS="$ROOT/nav_ws"
CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"
ROSA_PY="$HOME/miniconda3/envs/rosa/bin/python"
AGENT_BIN="$WS/install/nav_agent_ros2/lib/nav_agent_ros2/nav_agent"

export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES:-}"

source "$CONDA_SH"
conda activate rosa
source /opt/ros/humble/setup.bash

cd "$WS"
colcon build --packages-select nav_agent_ros2 --symlink-install
source "$WS/install/setup.bash"

export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

exec "$ROSA_PY" "$AGENT_BIN"
