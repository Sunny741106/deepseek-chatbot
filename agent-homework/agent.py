"""
agent.py — GitHub 项目分析 Agent 主程序

这是整个项目的入口文件。
运行方式：python agent.py
"""

from tools import say_hello, AVAILABLE_TOOLS


class GitHubAnalystAgent:
    """GitHub 项目分析 Agent — 班级里的学习委员"""

    def __init__(self):
        # 登记它能使用哪些工具（从 tools.py 来）
        self.tools = AVAILABLE_TOOLS

    def greet(self):
        """打印问候语，证明我活着 😄"""
        print("=" * 50)
        print("  🤖 GitHub 项目分析 Agent 已启动")
        print("=" * 50)
        print(f"  {say_hello('Sunny')}")
        print()
        print(f"  目前我会用 {len(self.tools)} 个工具：")
        for t in self.tools:
            print(f"    • {t.__name__} — {t.__doc__}")
        print("=" * 50)

    def run(self):
        """主循环——接收用户输入、执行任务"""
        self.greet()

        while True:
            try:
                user_input = input("\n你好 Sunny，请说点什么吧（输入 quit 退出）：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "退出"):
                print("👋 再见！下次见～")
                break

            # 骨架阶段：还没接大模型，先演示调用工具
            if "你好" in user_input or "hello" in user_input.lower():
                print(f"💬 Agent 说：{say_hello('你')}")
            else:
                print("💬 Agent 说：骨架阶段还不会分析代码，先完成 Token 配置吧！")
                print("   配置好后我就能去 GitHub 查仓库啦～")


if __name__ == "__main__":
    agent = GitHubAnalystAgent()
    agent.run()
