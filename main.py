#!/usr/bin/env python3
"""
智能命令行助手 —— 主程序入口
集成 LLM 对话、系统命令执行、文件分析等功能。

功能列表：
  - 普通对话：直接输入文本与 LLM 交互
  - !ps        ：查看并分析最占 CPU 的进程
  - !ls [路径]  ：列出目录内容并让 LLM 解释
  - !analyze <文件> ：让 LLM 分析文件内容
  - !explain <代码> ：让 LLM 解释一段代码
  - !history    ：查看对话历史
  - !save       ：保存对话历史到文件
  - !load       ：从文件加载对话历史
  - !clear      ：清空对话历史
  - !help       ：显示帮助信息
  - !quit / !exit：退出程序

"""

import subprocess
import sys
import os
import json
import datetime

# 将当前目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_wrapper import LLMWrapper, logger

# ==================== 配置 ====================
# 项目根目录（自动检测）
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_DIR, "models", "qwen1_5-1_8b-chat-q4_k_m.gguf")
HISTORY_FILE = os.path.join(PROJECT_DIR, "chat_history.json")


# ==================== 系统命令处理 ====================

def execute_system_command(cmd: str) -> str:
    """
    在本地 Linux 系统上执行命令并捕获输出。

    参数：
        cmd: 要执行的 shell 命令

    返回：
        str: 命令的标准输出内容，出错时返回错误信息
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 最多等待 30 秒
        )
        output = result.stdout
        if result.stderr:
            output += "\n[标准错误输出]:\n" + result.stderr
        return output.strip() if output.strip() else "(命令无输出)"
    except subprocess.TimeoutExpired:
        return "❌ 命令执行超时（超过 30 秒）"
    except Exception as e:
        return f"❌ 命令执行失败: {e}"


def handle_ps_command(llm: LLMWrapper) -> str:
    """
    处理 !ps 命令：执行 ps aux 并让 LLM 分析结果。
    """
    print("📊 正在获取进程信息...")
    output = execute_system_command("ps aux --sort=-%cpu | head -n 15")
    print(f"\n--- ps aux 输出 ---\n{output}\n-------------------\n")

    prompt = (
        f"以下是 Linux 系统 `ps aux --sort=-%cpu` 命令的输出（按 CPU 使用率排序）：\n\n"
        f"```\n{output}\n```\n\n"
        f"请用中文帮我分析：\n"
        f"1. 最占 CPU 的进程是什么？它在做什么？\n"
        f"2. 有没有异常或可疑的进程？\n"
        f"3. 简要总结系统当前的资源使用情况。"
    )
    print("🤖 正在分析...\n")
    return llm.send_prompt(prompt)


def handle_ls_command(llm: LLMWrapper, path: str = ".") -> str:
    """
    处理 !ls 命令：列出目录并让 LLM 解释。
    """
    print(f"📁 正在列出目录: {path}")
    output = execute_system_command(f"ls -la {path}")
    print(f"\n--- ls -la {path} ---\n{output}\n---------------------\n")

    prompt = (
        f"以下是 `ls -la {path}` 命令的输出：\n\n"
        f"```\n{output}\n```\n\n"
        f"请用中文简要解释这个目录中有什么内容，包括文件类型和权限。"
    )
    print("🤖 正在分析...\n")
    return llm.send_prompt(prompt)


def handle_analyze_command(llm: LLMWrapper, filename: str) -> str:
    """
    处理 !analyze 命令：读取文件内容并让 LLM 总结分析。
    """
    # 检查文件是否存在
    if not os.path.isfile(filename):
        print(f"❌ 文件不存在: {filename}")
        return ""

    # 读取文件内容（限制大小，防止超出上下文窗口）
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(4096)  # 最多读取 4KB
        if len(content) >= 4096:
            content += "\n\n... (文件内容过长，已截断)"
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return ""

    print(f"📄 已读取文件: {filename} ({len(content)} 字符)")

    prompt = (
        f"以下是文件 `{os.path.basename(filename)}` 的内容：\n\n"
        f"```\n{content}\n```\n\n"
        f"请用中文：\n"
        f"1. 总结这个文件的主要内容和用途\n"
        f"2. 指出关键部分或潜在问题\n"
        f"3. 如果是代码，解释其功能逻辑"
    )
    print("🤖 正在分析...\n")
    return llm.send_prompt(prompt)


def handle_explain_command(llm: LLMWrapper, code_snippet: str) -> str:
    """
    处理 !explain 命令：让 LLM 解释一段代码。
    """
    prompt = (
        f"请用中文解释以下代码的功能：\n\n"
        f"```\n{code_snippet}\n```\n\n"
        f"包括：\n"
        f"1. 代码的整体功能\n"
        f"2. 关键步骤的逐行解释\n"
        f"3. 使用了哪些重要的编程概念或库"
    )
    print("🤖 正在解释...\n")
    return llm.send_prompt(prompt)


def handle_system_exec(llm: LLMWrapper, cmd: str) -> str:
    """
    处理 @system 命令：执行任意系统命令并让 LLM 解释结果。
    """
    print(f"⚙️ 正在执行: {cmd}")
    output = execute_system_command(cmd)
    print(f"\n--- 命令输出 ---\n{output}\n----------------\n")

    prompt = (
        f"以下是 Linux 命令 `{cmd}` 的执行结果：\n\n"
        f"```\n{output}\n```\n\n"
        f"请用中文解释这个命令的输出含义。"
    )
    print("🤖 正在分析...\n")
    return llm.send_prompt(prompt)


# ==================== 对话历史管理 ====================

def save_history(llm: LLMWrapper, filepath: str = None):
    """保存对话历史到 JSON 文件。"""
    filepath = filepath or HISTORY_FILE
    data = {
        "saved_at": datetime.datetime.now().isoformat(),
        "messages": llm.conversation_history
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 对话历史已保存到: {filepath}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


def load_history(llm: LLMWrapper, filepath: str = None):
    """从 JSON 文件加载对话历史。"""
    filepath = filepath or HISTORY_FILE
    if not os.path.isfile(filepath):
        print(f"❌ 历史文件不存在: {filepath}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        llm.conversation_history = data.get("messages", [])
        saved_at = data.get("saved_at", "未知")
        count = len(llm.conversation_history)
        print(f"📂 已加载 {count} 条对话记录（保存于 {saved_at}）")
    except Exception as e:
        print(f"❌ 加载失败: {e}")


def show_history(llm: LLMWrapper):
    """显示当前对话历史摘要。"""
    if not llm.conversation_history:
        print("📭 对话历史为空")
        return

    print(f"\n📋 当前对话历史（共 {len(llm.conversation_history)} 条）：")
    print("-" * 50)
    for i, msg in enumerate(llm.conversation_history, 1):
        role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
        # 只显示前 80 个字符
        content = msg["content"][:80]
        if len(msg["content"]) > 80:
            content += "..."
        print(f"  {i}. {role}: {content}")
    print("-" * 50)


# ==================== 帮助信息 ====================

def show_help():
    """显示帮助信息。"""
    help_text = """
╔══════════════════════════════════════════════════════╗
║          🤖 智能命令行助手 - 使用帮助               ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  💬 普通对话：直接输入文字即可与 AI 对话             ║
║                                                      ║
║  📌 系统命令（以 ! 开头）：                          ║
║    !ps             查看并分析系统进程                 ║
║    !ls [路径]      列出并分析目录内容                 ║
║    !analyze <文件> 分析文件内容                       ║
║    !explain <代码> 解释代码片段                       ║
║    @system <命令>  执行任意命令并分析结果             ║
║                                                      ║
║  📁 对话管理：                                       ║
║    !history        查看对话历史                       ║
║    !save           保存对话历史                       ║
║    !load           加载对话历史                       ║
║    !clear          清空对话历史                       ║
║                                                      ║
║  🔧 其他：                                           ║
║    !help           显示此帮助                         ║
║    !quit / !exit   退出程序                           ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""
    print(help_text)


# ==================== 欢迎信息 ====================

def show_banner():
    """显示启动横幅。"""
    banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║    🤖  个人智能命令行助手  v1.0                      ║
║    基于 llama.cpp + Qwen1.5-1.8B-Chat                ║
║    运行环境: OpenEuler 24.03 LTS                     ║
║                                                      ║
║    输入 !help 查看所有可用命令                        ║
║    输入 !quit 退出程序                                ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)


# ==================== 主循环 ====================

def main():
    """程序主入口：启动 LLM 并进入交互式循环。"""

    show_banner()

    # 创建 LLM 封装器
    llm = LLMWrapper(model_path=MODEL_PATH)

    # 启动 LLM 服务器
    if not llm.start():
        print("❌ 无法启动 LLM 服务器，请检查模型文件路径和 llama.cpp 编译状态。")
        sys.exit(1)

    # 尝试加载历史对话记录（实现"记忆"功能）
    if os.path.isfile(HISTORY_FILE):
        load_history(llm)

    try:
        while True:
            try:
                # 获取用户输入
                user_input = input("\n💬 你> ").strip()

                # 忽略空输入
                if not user_input:
                    continue

                # ========== 处理特殊命令 ==========

                # 退出命令
                if user_input.lower() in ("!quit", "!exit", "quit", "exit"):
                    print("\n👋 再见！正在保存对话历史...")
                    save_history(llm)
                    break

                # 帮助
                elif user_input.lower() == "!help":
                    show_help()

                # 进程分析
                elif user_input.lower() == "!ps":
                    handle_ps_command(llm)

                # 目录列表
                elif user_input.lower().startswith("!ls"):
                    parts = user_input.split(maxsplit=1)
                    path = parts[1] if len(parts) > 1 else "."
                    handle_ls_command(llm, path)

                # 文件分析
                elif user_input.lower().startswith("!analyze"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print("用法: !analyze <文件路径>")
                    else:
                        handle_analyze_command(llm, parts[1])

                # 代码解释
                elif user_input.lower().startswith("!explain"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print("用法: !explain <代码片段>")
                    else:
                        handle_explain_command(llm, parts[1])

                # 任意系统命令
                elif user_input.startswith("@system"):
                    cmd = user_input[7:].strip()
                    if not cmd:
                        print("用法: @system <命令>")
                    else:
                        handle_system_exec(llm, cmd)

                # 对话历史
                elif user_input.lower() == "!history":
                    show_history(llm)

                elif user_input.lower() == "!save":
                    save_history(llm)

                elif user_input.lower() == "!load":
                    load_history(llm)

                elif user_input.lower() == "!clear":
                    llm.clear_history()
                    print("🗑️ 对话历史已清空")

                # ========== 普通对话 ==========
                else:
                    print("\n🤖 助手:\n")
                    llm.send_prompt(user_input)

            except KeyboardInterrupt:
                print("\n\n⚠️ 检测到 Ctrl+C，输入 !quit 退出程序")
                continue

    finally:
        # 确保服务器被关闭
        llm.close()
        print("✅ 程序已退出")


if __name__ == "__main__":
    main()
