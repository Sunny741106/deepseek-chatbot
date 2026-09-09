"""
agent.py — GitHub 项目分析 Agent（任务 2 版本）

核心升级：实现 Agent Loop 闭环
  模型决定调工具 → 执行 → 结果回传 → 模型回答

用法：
  python agent.py                # 正常对话
  python agent.py --trace        # 打印轨迹 + 写入 agent_trace.json
"""

import os
import sys
import json
import argparse
import datetime
import requests
from dotenv import load_dotenv

from tools import TOOL_SCHEMAS, TOOL_MAP

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
TRACE_FILE = "agent_trace.json"


class GitHubAnalystAgent:
    """带 Agent Loop 的 GitHub 项目分析 Agent"""

    def __init__(self, trace: bool = False):
        self.trace = trace
        self.history: list[dict] = []
        # trace 记录列表（写入 agent_trace.json）
        self.trace_log: list[dict] = []
        self.system_prompt = {
            "role": "system",
            "content": (
                "你是一个 GitHub 项目分析 Agent。"
                "你有可用的工具可以调用，请根据用户问题判断是否需要调用工具。"
                "回答要简洁、准确。"
            ),
        }
        self.max_loops = 5

    # ---------- 调试输出 ----------

    def log(self, tag: str, msg: str):
        """同时：控制台 print + 追加到 trace_log"""
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "tag": tag,
            "msg": msg,
        }
        self.trace_log.append(entry)
        if self.trace:
            print(f"  🔍 [{tag}] {msg}")

    def save_trace(self):
        """把 trace_log 写到 agent_trace.json"""
        with open(TRACE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.trace_log, f, ensure_ascii=False, indent=2)
        if self.trace:
            print(f"\n📄 执行轨迹已写入 {TRACE_FILE}（{len(self.trace_log)} 条）")

    # ---------- 核心：带工具的 LLM 调用 ----------

    def chat_with_tools(self, messages: list[dict]) -> dict:
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
        1. 用户入队 → 调 LLM
        2. 有 tool_calls → 执行 → 以 role="tool" + tool_call_id 回传
        3. 再调 LLM → 直到没有 tool_calls → 拿 content 当最终回答
        """
        self.history.append({"role": "user", "content": user_input})
        messages = [self.system_prompt] + self.history

        self.log("用户输入", user_input)

        for loop_idx in range(1, self.max_loops + 1):
            self.log(f"Loop {loop_idx}", f"调 LLM，messages 共 {len(messages)} 条")

            assistant_msg = self.chat_with_tools(messages)
            self.log("LLM 返回", f"content={assistant_msg.get('content', '(空)')}")

            tool_calls = assistant_msg.get("tool_calls")

            if not tool_calls:
                reply = assistant_msg["content"].strip()
                self.history.append(assistant_msg)
                self.log("最终回答", reply[:200] + ("..." if len(reply) > 200 else ""))
                return reply

            self.log("检测到 tool_calls", f"{len(tool_calls)} 个")

            # assistant 的 tool_calls 加进 messages
            messages.append(assistant_msg)

            for tc in tool_calls:
                tc_id = tc["id"]
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"])

                self.log("执行工具", f"{func_name}({func_args})")

                tool_fn = TOOL_MAP.get(func_name)
                if tool_fn is None:
                    tool_result = f"错误：找不到工具 {func_name}"
                else:
                    try:
                        tool_result = str(tool_fn(**func_args))
                    except Exception as e:
                        tool_result = f"工具执行出错：{e}"

                self.log("工具结果", tool_result[:200] + ("..." if len(tool_result) > 200 else ""))

                # ⭐ 关键：工具结果以 role="tool" + tool_call_id 回传
                # 验收官要求：必须有 role="tool" 和对应的 tool_call_id
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": func_name,
                    "content": tool_result,
                })
                self.log("回传", f"role=tool, tool_call_id={tc_id}")

        return "⚠️  工具调用太多轮了，停止执行。"

    # ---------- CLI ----------

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

        try:
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
        finally:
            # 无论正常退出还是 Ctrl+C，都写 trace 文件
            self.save_trace()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Agent")
    parser.add_argument("--trace", action="store_true", help="打印执行轨迹 + 写入 agent_trace.json")
    args = parser.parse_args()

    agent = GitHubAnalystAgent(trace=args.trace)
    agent.run()
