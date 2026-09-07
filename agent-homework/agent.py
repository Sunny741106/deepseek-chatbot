"""
agent.py — GitHub 项目分析 Agent 主程序

这是整个项目的入口文件。
运行方式：python agent.py

功能：接入 DeepSeek 大模型，CLI 能真对话 + 可调用 GitHub 工具
"""

import os
import requests
from dotenv import load_dotenv

from tools import say_hello, get_github_repo_info, AVAILABLE_TOOLS

# 加载 .env 配置
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class GitHubAnalystAgent:
    """GitHub 项目分析 Agent — 能调用大模型 + 工具箱"""

    def __init__(self):
        self.tools = AVAILABLE_TOOLS
        # 对话历史（让大模型记住上下文）
        self.history: list[dict] = []
        # 系统提示词（告诉大模型你是谁、能做什么）
        self.system_prompt = {
            "role": "system",
            "content": (
                "你是一个 GitHub 项目分析 Agent。"
                "你可以调用工具来查询 GitHub 仓库信息。"
                "如果用户问关于 GitHub 仓库的问题，先想想要不要用工具，"
                "还是直接回答就行。"
            ),
        }

    def call_llm(self, user_message: str) -> str:
        """调用 DeepSeek 大模型，返回 AI 回复"""
        if not API_KEY:
            return "❌ 没配置 DEEPSEEK_API_KEY，去 .env 里填一下吧！"

        # 把用户消息加进历史
        self.history.append({"role": "user", "content": user_message})

        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [self.system_prompt] + self.history,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                timeout=30,
            )
            if resp.status_code >= 400:
                return f"❌ API 报错了：{resp.status_code} {resp.text[:200]}"

            result = resp.json()
            reply = result["choices"][0]["message"]["content"].strip()
            # 把 AI 回复也存进历史
            self.history.append({"role": "assistant", "content": reply})
            return reply

        except requests.Timeout:
            return "❌ 请求超时了，大模型可能在忙碌，再试试？"
        except requests.RequestException as e:
            return f"❌ 网络请求出错：{e}"

    def greet(self):
        """启动时的问候"""
        print("=" * 50)
        print("  🤖 GitHub 项目分析 Agent 已启动")
        print("=" * 50)
        print(f"  {say_hello('Sunny')}")
        print()
        print(f"  🧠 大模型：{MODEL} ({'✅ 已连接' if API_KEY else '❌ 未配置'})")
        print(f"  🛠️  可用工具 {len(self.tools)} 个：")
        for t in self.tools:
            print(f"    • {t.__name__}")
        print("=" * 50)

    def run(self):
        """主循环"""
        self.greet()

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

            # 演示工具调用：用户说"分析 psf/requests"就调 GitHub API
            if "分析" in user_input and "/" in user_input:
                parts = user_input.replace("分析", "").strip().split("/")
                if len(parts) == 2:
                    owner, repo = parts[0].strip(), parts[1].strip()
                    print(f"🔧 [调用工具] get_github_repo_info({owner}, {repo})")
                    info = get_github_repo_info(owner, repo)
                    if info:
                        print(f"📦 仓库：{info['full_name']}")
                        print(f"⭐ Stars：{info['stargazers_count']}")
                        print(f"🍴 Forks：{info['forks_count']}")
                        print(f"📝 简介：{info['description']}")
                    else:
                        print("❌ 获取仓库信息失败")
                    continue

            # 正常走大模型对话
            print("🤖 Agent：思考中...")
            reply = self.call_llm(user_input)
            print(f"🤖 Agent：{reply}")


if __name__ == "__main__":
    agent = GitHubAnalystAgent()
    agent.run()
