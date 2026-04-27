#!/usr/bin/env bash
set -eo pipefail

ROOT="/home/evawang/Downloads/rosa-main/nav_ws"

# Ensure build uses system Python/ROS env, not conda Python.
if command -v conda >/dev/null 2>&1; then
  conda deactivate 2>/dev/null || true
fi
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PROMPT_MODIFIER CONDA_SHLVL CONDA_EXE CONDA_PYTHON_EXE || true
export COLCON_PYTHON_EXECUTABLE=/usr/bin/python3
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
# Avoid unbound variable errors when sourcing ROS setup with `set -u`.
export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES:-}"
export AMENT_PYTHON_EXECUTABLE="${AMENT_PYTHON_EXECUTABLE:-/usr/bin/python3}"

cd "$ROOT"
source /opt/ros/humble/setup.bash

echo "[INFO] Cleaning workspace..."
rm -rf build install log

echo "[INFO] Building nav_ws with system python..."
colcon build --symlink-install

echo "[INFO] Build complete."
