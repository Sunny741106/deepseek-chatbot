"""
github_client.py — GitHub REST API 轻量客户端

封装了：
  ✅ 自动带 Token 请求头（Authorization: Bearer <token>）
  ✅ 区分三种错误：401 认证失败 / 403 限流 / 404 不存在
  ✅ 403 限流时按 Retry-After 退避，最多重试一次（有次数上限，不会无限重试）
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

    # ---------- 核心：带错误分类 + 有限次数限流重试的请求方法 ----------

    def request(self, method: str, path: str, max_retries: int = 1, **kwargs) -> dict:
        """
        发起一次 GitHub API 请求。

        成功时 {ok:True, data}；失败时 {ok:False, code, error}。

        Args:
            method: "GET" / "POST"...
            path:   "/repos/psf/requests" 这种，自动拼 BASE_URL
            max_retries: 404 限流时的最大重试次数（默认 1，即最多额外再试一次）。
                         重试次数受此参数限制，不会无限重试。
            **kwargs: 透传给 requests.request 的参数
        """
        # 有限循环：1 次原始请求 + max_retries 次限流重试
        for attempt in range(max_retries + 1):
            result = self._single_request(method, path, **kwargs)

            # 成功 → 直接返回
            if result["ok"]:
                return result

            # 只有"限流"错误才值得重试；且已到重试上限 → 不再重试
            is_rate_limit = result["code"] == 403 and result.get("retry_after") is not None
            if not is_rate_limit or attempt >= max_retries:
                return result

            # 限流且还有重试机会 → 按 Retry-After 退避后进入下一轮循环
            wait_sec = result["retry_after"]
            time.sleep(wait_sec)

        # 不会走到这里（循环每次都会 return），仅作兜底
        return {"ok": False, "code": None, "error": "未知错误"}

    def _single_request(self, method: str, path: str, **kwargs) -> dict:
        """
        真正发一次 HTTP 请求并分类返回。不做任何重试。
        额外信息（如 retry_after）以键形式附加，供上层决定是否重试。
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

                # 等待时间过长（>300s）就不重试了，直接返回错误
                if wait_sec > 300:
                    return {
                        "ok": False,
                        "code": 403,
                        "error": f"触发 GitHub API 限流，等待时间过长（{wait_sec}s），建议稍后手动重试",
                    }

                # 标记为可重试的限流，retry_after 供上层控制退避
                return {
                    "ok": False,
                    "code": 403,
                    "retry_after": wait_sec,
                    "error": f"触发 GitHub API 限流，等待 {wait_sec}s 后再试",
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