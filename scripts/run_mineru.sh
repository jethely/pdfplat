#!/bin/bash
# run_mineru.sh - MinerU 生产环境启动器

# ✅ 1. 显式声明核心环境变量（替代 conda activate 的钩子）
export MAGIC_PDF_CONFIG_PATH="/mount/nvme1/mineru/magic-pdf.json"
export MODELSCOPE_CACHE="/mount/nvme1/mineru/models"
export CUDA_VISIBLE_DEVICES="0"

# ✅ 2. 构造隔离的 PATH（仅包含 Conda 环境和必要系统路径）
export PATH="/mount/nvme1/mineru/envs/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"

# ✅ 3. 清除可能残留的 venv 污染
unset VIRTUAL_ENV
unset PYTHONPATH

# ✅ 4. 使用绝对路径执行
exec /mount/nvme1/mineru/envs/bin/python "$@"
