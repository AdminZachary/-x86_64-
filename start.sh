#!/bin/bash
# ============================================================
# 智能命令行助手 —— 一键启动脚本
# 使用方法: bash start.sh
# ============================================================

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 虚拟环境路径
VENV_DIR="$SCRIPT_DIR/llm_lab"

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 虚拟环境不存在，正在创建..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install requests
else
    source "$VENV_DIR/bin/activate"
fi

echo "✅ 虚拟环境已激活: $VENV_DIR"

# 检查模型文件是否存在
MODEL_FILE="$SCRIPT_DIR/models/qwen1_5-1_8b-chat-q4_k_m.gguf"
if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ 模型文件不存在: $MODEL_FILE"
    echo "请先下载模型文件到 models/ 目录"
    exit 1
fi

# 检查 llama-server 是否已编译
SERVER_BIN="$SCRIPT_DIR/llama.cpp/build/bin/llama-server"
if [ ! -f "$SERVER_BIN" ]; then
    echo "❌ llama-server 未编译: $SERVER_BIN"
    echo "请先编译 llama.cpp（参考 README）"
    exit 1
fi

echo "🚀 启动智能命令行助手..."
echo ""

# 启动主程序
python3 "$SCRIPT_DIR/main.py"
