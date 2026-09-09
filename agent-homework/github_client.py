"""
github_client.py — GitHub REST API 轻量客户端

封装了：
  ✅ 自动带 Token 请求头（Authorization: Bearer <token>）
  ✅ 区分三种错误：401 认证失败 / 403 限流 / 404 不存在
  ✅ 403 限流时按 Retry-After 退避，自动重试一次
  ✅ 所有错误以结构化字典 {ok:False, code, error} 返回（不静默吞掉）
  ✅ 成功以 {ok:True, data} 返回
"""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


# ========== 客户端类 ==========

class GitHubClient:
    """一个简单的 GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None, timeout: int = 10):
        """
        Args:
            token: GitHub PAT，不传就从 .env 的 GITHUB_TOKEN 读
            timeout: 单次请求超时秒数
        """
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHubAgent-Client/1.0",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    # ---------- 核心：带错误分类 + 限流重试的请求方法 ----------

    def request(self, method: str, path: str, **kwargs) -> dict:
        """
        发起一次 GitHub API 请求。
        返回结构化字典，成功时 {ok:True, data}, 失败时 {ok:False, code, error}。
        """
        url = f"{self.BASE_URL}{path}"

        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.Timeout:
            return {"ok": False, "code": None, "error": "请求超时"}
        except requests.ConnectionError as e:
            return {"ok": False, "code": None, "error": f"网络连接失败：{e}"}
        except requests.RequestException as e:
            return {"ok": False, "code": None, "error": f"请求异常：{e}"}

        # 成功
        if resp.status_code == 200:
            return {"ok": True, "data": resp.json()}

        # ---------- 401：认证失败 ----------
        if resp.status_code == 401:
            return {
                "ok": False,
                "code": 401,
                "error": "Token 无效或未配置，请检查 .env 里的 GITHUB_TOKEN",
            }

        # ---------- 403：可能是限流 ----------
        if resp.status_code == 403:
            retry_after = resp.headers.get("Retry-After")
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset_ts = resp.headers.get("X-RateLimit-Reset")

            # 判断是不是真限流
            if retry_after is not None or (remaining == "0"):
                if retry_after is not None:
                    wait_sec = int(retry_after)
                elif reset_ts is not None:
                    wait_sec = max(1, int(reset_ts) - int(time.time()))
                else:
                    wait_sec = 60

                # ⭐ 按 Retry-After 退避一次重试
                if wait_sec <= 300:  # 超过 5 分钟就不等了
                    time.sleep(wait_sec)
                    retry_result = self.request(method, path, **kwargs)
                    if retry_result.get("ok"):
                        return retry_result  # 重试成功！
                    # 重试也失败：把原 403 限流信息带出来
                    return {
                        "ok": False,
                        "code": 403,
                        "error": (
                            f"触发 GitHub API 限流（Retry-After={wait_sec}s），"
                            f"重试后仍失败：{retry_result.get('error')}"
                        ),
                    }

                # 限流时间太长，不等待直接返回
                return {
                    "ok": False,
                    "code": 403,
                    "error": f"触发 GitHub API 限流，等待时间过长（{wait_sec}s），建议稍后手动重试",
                }
            else:
                # 非限流的 403
                return {
                    "ok": False,
                    "code": 403,
                    "error": "403 Forbidden（非限流，可能是权限不足）",
                }

        # ---------- 404：资源不存在 ----------
        if resp.status_code == 404:
            return {
                "ok": False,
                "code": 404,
                "error": "请求的资源不存在（仓库名/用户名可能拼错了，或者是私有仓库）",
            }

        # ---------- 其他 HTTP 错误 ----------
        return {
            "ok": False,
            "code": resp.status_code,
            "error": f"HTTP {resp.status_code}",
        }

    # ---------- 便捷方法 ----------

    def get(self, path: str, **kwargs) -> dict:
        """GET 请求，返回结构化字典"""
        return self.request("GET", path, **kwargs)

    def get_repo(self, owner: str, repo: str) -> dict:
        """获取仓库信息"""
        return self.get(f"/repos/{owner}/{repo}")