# 个人智能命令行助手

基于 LLM (大语言模型) 与 Linux 操作系统的综合实验项目。

## 项目简介

本项目构建了一个运行在 Linux (OpenEuler 24.03) 上的个人智能命令行助手。
它使用 [llama.cpp](https://github.com/ggerganov/llama.cpp) 作为 LLM 推理引擎，
加载 Qwen1.5-1.8B-Chat 模型，通过 Python 进行进程间通信 (IPC) 和交互式界面管理。

## 功能特性

- 💬 **自然语言对话**：与 AI 进行多轮中文对话
- 📊 **进程分析** (`!ps`)：查看系统进程，AI 自动分析最占资源的进程
- 📁 **目录浏览** (`!ls`)：列出目录内容，AI 解释文件结构
- 📄 **文件分析** (`!analyze <文件>`)：AI 读取并总结文件内容
- 💻 **代码解释** (`!explain <代码>`)：AI 解释代码功能
- ⚙️ **系统命令** (`@system <命令>`)：执行任意命令，AI 解释结果
- 💾 **对话记忆** (`!save` / `!load`)：保存和恢复对话历史

## 技术架构

```
┌─────────────────────┐
│   用户 (命令行)      │
├─────────────────────┤
│   main.py           │  ← 交互式前端 + 命令解析
│   (Python CLI)      │
├─────────────────────┤
│   llm_wrapper.py    │  ← LLM 封装层 (subprocess + HTTP)
│   (LLMWrapper 类)   │
├─────────────────────┤
│   llama-server      │  ← llama.cpp 推理引擎 (C++)
│   (HTTP API)        │
├─────────────────────┤
│   Qwen1.5-1.8B      │  ← GGUF 量化模型
│   (q4_k_m)          │
└─────────────────────┘
```

## 从零开始部署（完整指南）

> 适用于只安装了 Linux 系统的用户，以下步骤将从头搭建整个项目。

### 第一步：安装系统依赖

```bash
# === Ubuntu / Debian 系统 ===
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git python3 python3-pip python3-venv cmake

# === OpenEuler / CentOS / Fedora 系统 ===
sudo dnf update -y
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y git python3 python3-pip cmake
```

### 第二步：克隆项目仓库

```bash
cd ~
git clone https://github.com/AdminZachary/-x86_64-.git llm_assistant
cd llm_assistant
```

### 第三步：创建 Python 虚拟环境并安装依赖

```bash
python3 -m venv llm_lab
source llm_lab/bin/activate
pip install requests huggingface_hub
```

### 第四步：编译 llama.cpp 推理引擎

```bash
cd ~/llm_assistant
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build
cmake ..
cmake --build . --config Release -j$(nproc)
cd ~/llm_assistant
```

> 编译时间取决于 CPU 性能，一般需要 2~10 分钟。

### 第五步：下载 AI 模型

```bash
source ~/llm_assistant/llm_lab/bin/activate
mkdir -p ~/llm_assistant/models
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='Qwen/Qwen1.5-1.8B-Chat-GGUF',
    filename='qwen1_5-1_8b-chat-q4_k_m.gguf',
    local_dir='$HOME/llm_assistant/models'
)
print('✅ 模型下载完成！')
"
```

> 模型约 1GB，下载速度取决于网络环境。

### 第六步：启动助手

```bash
cd ~/llm_assistant
source llm_lab/bin/activate
bash start.sh
```

等待看到 `💬 你>` 提示符后，即可开始使用！

### 快速启动（已部署完成后）

```bash
cd ~/llm_assistant
source llm_lab/bin/activate
bash start.sh
```

## 文件结构

```
llm_assistant/
├── main.py           # 主程序入口（交互式CLI）
├── llm_wrapper.py    # LLM 封装类
├── start.sh          # 一键启动脚本
├── .gitignore        # Git 忽略规则
├── README.md         # 项目说明
├── models/           # 模型文件目录
│   └── qwen1_5-1_8b-chat-q4_k_m.gguf
├── llm_lab/          # Python 虚拟环境
└── llama.cpp/        # LLM 推理引擎源码 + 编译产物
    └── build/bin/llama-server
```

## 环境要求

- **系统**: OpenEuler 24.03 LTS (x86_64)
- **Python**: 3.x + requests 库
- **编译工具**: gcc, g++, cmake
- **模型**: Qwen1.5-1.8B-Chat GGUF (q4_k_m 量化)
