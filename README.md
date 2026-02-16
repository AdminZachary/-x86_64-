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

## 快速开始

```bash
# 1. 激活虚拟环境
source llm_lab/bin/activate

# 2. 一键启动
bash start.sh

# 或者直接运行
python3 main.py
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
