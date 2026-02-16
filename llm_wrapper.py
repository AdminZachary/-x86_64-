#!/usr/bin/env python3
"""
LLM 封装器 —— 通过 subprocess 管理 llama.cpp 推理进程
使用 llama-server (HTTP API) 模式，比直接操作 stdin/stdout 更稳定可靠。

作者：学生实验项目
"""

import subprocess
import requests
import time
import threading
import logging
import json
import os
import signal

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("LLMWrapper")


class LLMWrapper:
    """
    LLM 封装类：负责启动、管理和与 llama.cpp 推理引擎通信。

    架构说明：
    - 使用 llama-server 作为后端（HTTP API 模式）
    - 通过 subprocess.Popen 启动服务器子进程
    - 通过 HTTP POST 请求发送提示词，获取流式回复
    - 支持对话历史管理和系统提示词设置
    """

    def __init__(self, model_path: str, server_path: str = None,
                 host: str = "127.0.0.1", port: int = 8080,
                 n_ctx: int = 2048, n_gpu_layers: int = 0):
        """
        初始化 LLM 封装器。

        参数：
            model_path: GGUF 模型文件的路径
            server_path: llama-server 可执行文件路径（默认自动检测）
            host: 服务器监听地址
            port: 服务器监听端口
            n_ctx: 上下文窗口大小（token 数）
            n_gpu_layers: GPU 加速层数（0=纯 CPU）
        """
        self.model_path = model_path
        self.host = host
        self.port = port
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.process = None         # 服务器子进程
        self.is_running = False     # 服务器运行状态标志
        self._log_thread = None    # 日志监控线程

        # 自动检测 llama-server 路径
        if server_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.server_path = os.path.join(
                base_dir, "llama.cpp", "build", "bin", "llama-server"
            )
        else:
            self.server_path = server_path

        # 对话历史（用于实现记忆功能）
        self.conversation_history = []

        # 系统提示词
        self.system_prompt = (
            "你是一个智能命令行助手，运行在 Linux 系统上。"
            "你可以帮助用户理解系统命令的输出、分析文件内容、解释代码。"
            "请用中文回答。回答要简洁明了。"
        )

    def start(self) -> bool:
        """
        启动 llama-server 子进程。

        返回：
            bool: 启动成功返回 True，失败返回 False
        """
        if self.is_running:
            logger.warning("服务器已在运行中，无需重复启动")
            return True

        # 检查可执行文件是否存在
        if not os.path.isfile(self.server_path):
            logger.error(f"找不到 llama-server: {self.server_path}")
            return False

        # 检查模型文件是否存在
        if not os.path.isfile(self.model_path):
            logger.error(f"找不到模型文件: {self.model_path}")
            return False

        # 构造启动命令
        cmd = [
            self.server_path,
            "-m", self.model_path,
            "--host", self.host,
            "--port", str(self.port),
            "-c", str(self.n_ctx),
            "-ngl", str(self.n_gpu_layers),
        ]

        logger.info(f"正在启动 LLM 服务器...")
        logger.info(f"模型: {os.path.basename(self.model_path)}")
        logger.info(f"地址: http://{self.host}:{self.port}")

        try:
            # 使用 subprocess.Popen 启动子进程
            # 重定向 stdin/stdout/stderr 到管道
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新的进程组，方便后续清理
            )

            # 启动日志监控线程（读取 stderr 避免管道阻塞）
            self._log_thread = threading.Thread(
                target=self._monitor_logs,
                daemon=True
            )
            self._log_thread.start()

            # 等待服务器就绪
            if self._wait_for_ready(timeout=60):
                self.is_running = True
                logger.info("✅ LLM 服务器启动成功！")
                return True
            else:
                logger.error("❌ 服务器启动超时")
                self.close()
                return False

        except FileNotFoundError:
            logger.error(f"❌ 无法执行: {self.server_path}")
            return False
        except Exception as e:
            logger.error(f"❌ 启动失败: {e}")
            self.close()
            return False

    def _monitor_logs(self):
        """
        监控服务器的 stderr 输出（日志）。
        在单独的线程中运行，避免管道缓冲区满导致进程阻塞。
        """
        try:
            for line in self.process.stderr:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    logger.debug(f"[llama-server] {decoded}")
        except Exception:
            pass

    def _wait_for_ready(self, timeout: int = 60) -> bool:
        """
        等待服务器健康检查通过。

        参数：
            timeout: 最大等待时间（秒）

        返回：
            bool: 服务器就绪返回 True
        """
        url = f"http://{self.host}:{self.port}/health"
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(url, timeout=2)
                if resp.status_code == 200:
                    return True
            except requests.ConnectionError:
                pass
            except Exception:
                pass
            time.sleep(1)

        return False

    def send_prompt(self, user_input: str, stream: bool = True) -> str:
        """
        向 LLM 发送提示词并获取回复。

        参数：
            user_input: 用户输入的文本
            stream: 是否使用流式输出（逐字显示）

        返回：
            str: LLM 的完整回复文本
        """
        if not self.is_running:
            return "❌ 错误：LLM 服务器未运行，请先调用 start() 启动"

        # 将用户输入追加到对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # 构造请求数据（OpenAI 兼容格式）
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history)

        payload = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": stream
        }

        url = f"http://{self.host}:{self.port}/v1/chat/completions"

        try:
            if stream:
                return self._stream_response(url, payload)
            else:
                return self._batch_response(url, payload)
        except requests.ConnectionError:
            logger.error("连接失败：服务器可能已崩溃")
            self.is_running = False
            return "❌ 错误：与 LLM 服务器的连接断开"
        except Exception as e:
            logger.error(f"请求失败: {e}")
            return f"❌ 错误：{e}"

    def _stream_response(self, url: str, payload: dict) -> str:
        """
        流式读取 LLM 回复（逐 token 打印）。

        参数：
            url: API 端点地址
            payload: 请求体

        返回：
            str: 完整回复文本
        """
        full_response = ""

        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            full_response += content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        print()  # 换行
        # 将助手回复追加到对话历史
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
        return full_response

    def _batch_response(self, url: str, payload: dict) -> str:
        """
        一次性获取 LLM 的完整回复（非流式）。
        """
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        self.conversation_history.append({
            "role": "assistant",
            "content": content
        })
        return content

    def read_response(self) -> str:
        """
        读取最后一次 LLM 回复（从对话历史中获取）。

        返回：
            str: 最后的助手回复，若无则返回空字符串
        """
        for msg in reversed(self.conversation_history):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""

    def clear_history(self):
        """清空对话历史。"""
        self.conversation_history.clear()
        logger.info("对话历史已清空")

    def close(self):
        """
        安全关闭 LLM 服务器子进程。
        使用进程组信号确保所有子进程都被清理。
        """
        if self.process is not None:
            logger.info("正在关闭 LLM 服务器...")
            try:
                # 先尝试优雅关闭
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 强制杀死
                logger.warning("服务器未响应 SIGTERM，强制终止...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
            except Exception as e:
                logger.error(f"关闭时出错: {e}")
                try:
                    self.process.kill()
                    self.process.wait()
                except Exception:
                    pass
            finally:
                self.process = None
                self.is_running = False
                logger.info("LLM 服务器已关闭")

    def __enter__(self):
        """支持 with 语句。"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 语句时自动关闭。"""
        self.close()

    def __del__(self):
        """析构时确保进程被清理。"""
        self.close()
