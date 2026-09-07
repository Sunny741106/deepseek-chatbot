"""
tools.py — Agent 的工具箱

每个工具函数 + 对应的 JSON Schema（告诉大模型怎么用）
"""

import os
import json
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


# ========== 工具 1：获取当前时间（内置，不需要网络） ==========

def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前日期和时间"""
    now = datetime.datetime.now()
    return f"当前时间是：{now.strftime('%Y-%m-%d %H:%M:%S')}，时区 {timezone}"


# get_current_time 的 JSON Schema（给大模型看的"说明书"）
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


# ========== 工具 2：GitHub 仓库信息（需要 Token） ==========

def get_github_repo_info(owner: str, repo: str) -> str:
    """
    用 GitHub API 获取仓库信息。
    返回：格式化后的仓库信息字符串（方便大模型直接回答）
    """
    if not GITHUB_TOKEN or GITHUB_TOKEN == "在这里填你的Token":
        return "错误：还没配置 GitHub Token，无法调用此工具。"

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            info = resp.json()
            return json.dumps({
                "full_name": info["full_name"],
                "stars": info["stargazers_count"],
                "forks": info["forks_count"],
                "language": info.get("language"),
                "description": info["description"],
            }, ensure_ascii=False)
        else:
            return f"错误：GitHub API 返回 {resp.status_code}"
    except Exception as e:
        return f"错误：请求失败 {e}"


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

# 工具函数列表（给任务 1 的旧代码兼容用）
AVAILABLE_TOOLS = [
    get_current_time,
    get_github_repo_info,
]

# JSON Schema 列表（给大模型看的"工具菜单"）
TOOL_SCHEMAS = [
    GET_CURRENT_TIME_SCHEMA,
    GET_GITHUB_REPO_INFO_SCHEMA,
]

# 函数名 → 实际函数 的映射表（Agent Loop 里根据名字调）
TOOL_MAP = {
    "get_current_time": get_current_time,
    "get_github_repo_info": get_github_repo_info,
}


if __name__ == "__main__":
    print("=== 测试 tools.py ===")
    print(get_current_time())
    print()
    print("Schema 列表：")
    for s in TOOL_SCHEMAS:
        print(f"  - {s['function']['name']}")
