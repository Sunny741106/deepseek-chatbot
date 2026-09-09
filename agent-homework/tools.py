"""
tools.py — Agent 的工具箱

每个工具函数 + 对应的 JSON Schema（告诉大模型怎么用）
GitHub 相关工具通过 github_client.GitHubClient 调用
"""

import json
import datetime

from github_client import GitHubClient

# 全局客户端实例（自动从 .env 读 Token）
_gh = GitHubClient()


# ========== 工具 1：获取当前时间（内置，不需要网络） ==========

def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前日期和时间"""
    now = datetime.datetime.now()
    return f"当前时间是：{now.strftime('%Y-%m-%d %H:%M:%S')}，时区 {timezone}"


GET_CURRENT_TIME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前的日期和时间，包括年、月、日、时、分、秒",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区标识，例如 Asia/Shanghai、UTC、America/New_York",
                }
            },
        },
    },
}


# ========== 工具 2：GitHub 仓库信息（用 GitHubClient） ==========

def get_github_repo_info(owner: str, repo: str) -> str:
    """
    用 GitHubClient 查询仓库信息。
    自动处理 Token / 401 / 404 / 限流重试。
    返回：结构化的 JSON 字符串（成功）或带错误类型的提示（失败）
    """
    result = _gh.get_repo(owner, repo)

    # 成功 → 返回整理好的 JSON
    if result["ok"]:
        info = result["data"]
        return json.dumps({
            "full_name": info["full_name"],
            "stars": info["stargazers_count"],
            "forks": info["forks_count"],
            "language": info.get("language"),
            "description": info["description"],
        }, ensure_ascii=False)

    # 失败 → 按 code 返回不同的人类可读提示
    code = result["code"]
    msg = result["error"]
    if code == 401:
        return f"【认证错误】{msg}"
    elif code == 404:
        return f"【仓库不存在】{msg}。请检查用户名和仓库名是否拼写正确（区分大小写）。"
    elif code == 403:
        return f"【限流/禁止】{msg}。请稍后再试。"
    elif code is None:
        return f"【网络错误】{msg}"
    else:
        return f"【GitHub API 错误 {code}】{msg}"


GET_GITHUB_REPO_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_github_repo_info",
        "description": "查询 GitHub 上某个仓库的详细信息，包括 Stars、Forks、语言、简介等",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "仓库主人的用户名，例如 psf",
                },
                "repo": {
                    "type": "string",
                    "description": "仓库名称，例如 requests",
                },
            },
            "required": ["owner", "repo"],
        },
    },
}


# ========== 注册表 ==========

AVAILABLE_TOOLS = [
    get_current_time,
    get_github_repo_info,
]

TOOL_SCHEMAS = [
    GET_CURRENT_TIME_SCHEMA,
    GET_GITHUB_REPO_INFO_SCHEMA,
]

TOOL_MAP = {
    "get_current_time": get_current_time,
    "get_github_repo_info": get_github_repo_info,
}


if __name__ == "__main__":
    print("=== 测试 tools.py（重构版，用 GitHubClient）===")
    print(get_current_time())
    print()
    print("Schema 列表：")
    for s in TOOL_SCHEMAS:
        print(f"  - {s['function']['name']}")
    print()
    print("--- 正常仓库 ---")
    print(get_github_repo_info("psf", "requests"))
    print()
    print("--- 不存在的仓库 ---")
    print(get_github_repo_info("foo", "bar_xyz_not_exist"))
