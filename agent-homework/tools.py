"""
tools.py — Agent 的工具箱

这里定义 Agent 可以调用的各种工具函数。
将来会扩展：查 GitHub 仓库、读文件、分析代码...
现在先搭骨架。
"""

import os
import requests
from dotenv import load_dotenv

# 加载 .env 文件里的环境变量（比如 GITHUB_TOKEN）
load_dotenv()

# 从 .env 读取 Token，没有就为空
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def say_hello(name: str = "世界") -> str:
    """最简单的工具：跟人打招呼。"""
    return f"你好，{name}！这是 Agent 的第一个工具函数 🎉"


def get_github_repo_info(owner: str, repo: str) -> dict | None:
    """
    用 GitHub API 获取仓库信息。
    参数：owner（仓库主人的用户名）、repo（仓库名字）
    返回：仓库信息字典，或者失败时返回 None
    """
    if not GITHUB_TOKEN or GITHUB_TOKEN == "在这里填你的Token":
        print("⚠️  还没配置 GitHub Token，跳过 API 调用。")
        print("   去 https://github.com/settings/tokens 申请，然后填进 .env 文件。")
        return None

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"❌ 请求失败：{resp.status_code} — {resp.reason}")
            return None
    except Exception as e:
        print(f"❌ 请求出错：{e}")
        return None


# 这个列表用来登记"有哪些工具可以用"，将来 Agent 会读它
AVAILABLE_TOOLS = [
    say_hello,
    get_github_repo_info,
]


if __name__ == "__main__":
    # 直接运行这个文件时的小测试
    print("=== 测试 tools.py ===")
    print(say_hello("Sunny"))
