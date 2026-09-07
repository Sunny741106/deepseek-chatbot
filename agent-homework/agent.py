"""
agent.py — GitHub 项目分析 Agent（任务 2 版本）

核心升级：实现 Agent Loop 闭环
  模型决定调工具 → 执行 → 结果回传 → 模型回答

用法：
  python agent.py                # 正常对话
  python agent.py --trace        # 带执行轨迹
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

from tools import TOOL_SCHEMAS, TOOL_MAP

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class GitHubAnalystAgent:
    """带 Agent Loop 的 GitHub 项目分析 Agent"""

    def __init__(self, trace: bool = False):
        self.trace = trace
        self.history: list[dict] = []
        self.system_prompt = {
            "role": "system",
            "content": (
                "你是一个 GitHub 项目分析 Agent。"
                "你有可用的工具可以调用，请根据用户问题判断是否需要调用工具。"
                "回答要简洁、准确。"
            ),
        }
        self.max_loops = 5  # 防止无限循环

    # ---------- 调试输出 ----------

    def log(self, tag: str, msg: str):
        """只有 --trace 时才打印轨迹"""
        if self.trace:
            print(f"  🔍 [{tag}] {msg}")

    # ---------- 核心：带工具的 LLM 调用 ----------

    def chat_with_tools(self, messages: list[dict]) -> dict:
        """
        调 LLM，传入 tools 参数，返回完整的 response message。
        这个 message 可能包含 content，也可能包含 tool_calls。
        """
        if not API_KEY:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY")

        payload = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"API 错误 {resp.status_code}: {resp.text[:300]}")

        return resp.json()["choices"][0]["message"]

    def run_agent_loop(self, user_input: str) -> str:
        """
        Agent Loop 核心闭环：
        1. 把用户消息加进历史
        2. 调 LLM（带 tools）
        3. 检查有没有 tool_calls
           - 有：执行工具 → 把结果塞回 messages → 再调 LLM（循环）
           - 没有：拿到 content 作为最终回答
        4. 最多循环 max_loops 次，防止死循环
        """
        # Step 1：用户入队
        self.history.append({"role": "user", "content": user_input})
        messages = [self.system_prompt] + self.history

        for loop_idx in range(1, self.max_loops + 1):
            self.log(f"Loop {loop_idx}", f"调 LLM，messages 共 {len(messages)} 条")

            # Step 2：调 LLM
            assistant_msg = self.chat_with_tools(messages)
            self.log("LLM 返回", f"content={assistant_msg.get('content', '(空)')}")

            # Step 3：有工具调用吗？
            tool_calls = assistant_msg.get("tool_calls")

            if not tool_calls:
                # 没有工具调用 → 就是最终回答
                reply = assistant_msg["content"].strip()
                self.history.append(assistant_msg)
                self.log("最终回答", reply[:100] + ("..." if len(reply) > 100 else ""))
                return reply

            # 有工具调用 → 执行
            self.log("检测到 tool_calls", f"{len(tool_calls)} 个")

            # 把 assistant 的 tool_calls 也加进 messages（下次要带着）
            messages.append(assistant_msg)

            for tc in tool_calls:
                tc_id = tc["id"]
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"])  # JSON 字符串 → dict

                self.log("执行工具", f"{func_name}({func_args})")

                # 查函数 → 调用
                tool_fn = TOOL_MAP.get(func_name)
                if tool_fn is None:
                    tool_result = f"错误：找不到工具 {func_name}"
                else:
                    try:
                        tool_result = str(tool_fn(**func_args))
                    except Exception as e:
                        tool_result = f"工具执行出错：{e}"

                self.log("工具结果", tool_result[:150] + ("..." if len(tool_result) > 150 else ""))

                # 工具结果以 role="tool" 塞回 messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": func_name,
                    "content": tool_result,
                })

            # 继续下一轮循环（再调一次 LLM）

        # 超过最大循环次数
        return "⚠️  工具调用太多轮了，停止执行。"

    # ---------- CLI 入口 ----------

    def greet(self):
        print("=" * 55)
        print("  🤖 GitHub 项目分析 Agent (Agent Loop 版)")
        print("=" * 55)
        print(f"  🧠 模型：{MODEL} {'(✅ 已连接)' if API_KEY else '(❌ 未配置)'}")
        print(f"  🛠️  可用工具：{', '.join(TOOL_MAP.keys())}")
        print(f"  📜 执行轨迹：{'开启' if self.trace else '关闭'}")
        print("=" * 55)

    def run(self):
        self.greet()
        print("\n💡 试试问：'现在几点了？' 或 '帮我查一下 psf/requests 仓库'")

        while True:
            try:
                user_input = input("\n🙋 你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "退出"):
                print("👋 再见！下次见～")
                break

            print("🤖 Agent：思考中...")
            try:
                reply = self.run_agent_loop(user_input)
                print(f"🤖 Agent：{reply}")
            except RuntimeError as e:
                print(f"❌ 出错：{e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Agent")
    parser.add_argument("--trace", action="store_true", help="输出执行轨迹")
    args = parser.parse_args()

    agent = GitHubAnalystAgent(trace=args.trace)
    agent.run()
