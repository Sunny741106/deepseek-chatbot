"""
github_client.py — GitHub REST API 轻量客户端

封装了：
  ✅ 自动带 Token 请求头
  ✅ 区分三种错误：401 认证失败 / 403 限流 / 404 不存在
  ✅ 403 限流时按 Retry-After 退避，自动重试一次
  ✅ 所有错误以结构化对象返回（不静默吞掉）
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


# ========== 结构化返回值 ==========

@dataclass
class GitHubResult:
    """成功时的返回"""
    ok: bool = True
    data: Any = None          # API 返回的 JSON 数据
    status_code: int = 200
    headers: dict = field(default_factory=dict)


@dataclass
class GitHubError:
    """失败时的结构化错误"""
    ok: bool = False
    error_type: str = ""      # "auth" / "rate_limit" / "not_found" / "http" / "network"
    status_code: int = 0
    message: str = ""
    retry_after: Optional[int] = None  # 只有 rate_limit 时才有
    raw_response: Optional[str] = None

    def __str__(self):
        return f"[GitHubError type={self.error_type} code={self.status_code}] {self.message}"


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
        # 共用一个 Session 连接池，性能更好
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHubAgent-Client/1.0",
        })
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

    # ---------- 核心：带错误分类 + 限流重试的请求方法 ----------

    def request(self, method: str, path: str, **kwargs) -> GitHubResult | GitHubError:
        """
        发起一次 GitHub API 请求。
        返回 GitHubResult（成功）或 GitHubError（失败），永远不抛异常。

        Args:
            method: "GET" / "POST" ...
            path:   "/repos/psf/requests" 这种路径，会自动拼 BASE_URL
            **kwargs: 透传给 requests.request 的参数
        """
        url = f"{self.BASE_URL}{path}"

        try:
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.Timeout:
            return GitHubError(error_type="network", message="请求超时")
        except requests.ConnectionError as e:
            return GitHubError(error_type="network", message=f"网络连接失败：{e}")
        except requests.RequestException as e:
            return GitHubError(error_type="network", message=f"请求异常：{e}")

        # 成功
        if resp.status_code == 200:
            return GitHubResult(
                ok=True,
                data=resp.json(),
                status_code=200,
                headers=dict(resp.headers),
            )

        # ---------- 401：认证失败 ----------
        if resp.status_code == 401:
            return GitHubError(
                error_type="auth",
                status_code=401,
                message="Token 无效或未配置，请检查 .env 里的 GITHUB_TOKEN",
                raw_response=resp.text[:200],
            )

        # ---------- 403：可能是限流 ----------
        if resp.status_code == 403:
            retry_after = resp.headers.get("Retry-After")
            # GitHub 有两套限流指示：
            # 1) Retry-After 响应头（精确秒数）
            # 2) X-RateLimit-Remaining == 0 + X-RateLimit-Reset
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset_ts = resp.headers.get("X-RateLimit-Reset")

            # 判断是不是真限流
            if retry_after is not None or (remaining == "0"):
                # 算退避秒数
                if retry_after is not None:
                    wait_sec = int(retry_after)
                elif reset_ts is not None:
                    wait_sec = max(1, int(reset_ts) - int(time.time()))
                else:
                    wait_sec = 60  # 兜底

                # ⭐ 按 Retry-After 退避一次重试
                if wait_sec <= 300:  # 超过 5 分钟就不等了，直接返回错误
                    print(f"  ⏳ GitHub 限流了，等 {wait_sec} 秒后重试一次...")
                    time.sleep(wait_sec)
                    retry_result = self.request(method, path, **kwargs)
                    if isinstance(retry_result, GitHubResult):
                        return retry_result  # 重试成功！

                # 重试也失败了（或者限流时间太长不等）
                return GitHubError(
                    error_type="rate_limit",
                    status_code=403,
                    message=f"触发 GitHub API 限流，建议等 {wait_sec} 秒后再试",
                    retry_after=wait_sec,
                    raw_response=resp.text[:200],
                )
            else:
                # 不是限流的 403（比如没有权限访问私有仓库）
                return GitHubError(
                    error_type="http",
                    status_code=403,
                    message="403 Forbidden（非限流，可能是权限问题）",
                    raw_response=resp.text[:200],
                )

        # ---------- 404：资源不存在 ----------
        if resp.status_code == 404:
            return GitHubError(
                error_type="not_found",
                status_code=404,
                message="请求的资源不存在（仓库名/用户名可能拼错了，或者是私有仓库）",
                raw_response=resp.text[:200],
            )

        # ---------- 其他 HTTP 错误 ----------
        return GitHubError(
            error_type="http",
            status_code=resp.status_code,
            message=f"HTTP {resp.status_code}",
            raw_response=resp.text[:200],
        )

    # ---------- 便捷方法 ----------

    def get(self, path: str, **kwargs) -> GitHubResult | GitHubError:
        return self.request("GET", path, **kwargs)

    def get_repo(self, owner: str, repo: str) -> GitHubResult | GitHubError:
        """获取仓库信息，封装成易用的方法"""
        return self.get(f"/repos/{owner}/{repo}")


# ========== 小测试 ==========

if __name__ == "__main__":
    client = GitHubClient()

    print("=== 测试 1：正常仓库 psf/requests ===")
    r = client.get_repo("psf", "requests")
    if r.ok:
        print(f"  ✅ ok: {r.data['full_name']} ⭐ {r.data['stargazers_count']}")
    else:
        print(f"  ❌ {r}")

    print("\n=== 测试 2：不存在的仓库 foo/bar_xyz_not_exist ===")
    r = client.get_repo("foo", "bar_xyz_not_exist")
    if r.ok:
        print(f"  ✅ {r.data['full_name']}")
    else:
        print(f"  ❌ {r}")
        print(f"     error_type = {r.error_type}")

    print("\n=== 测试 3：乱拼的用户名 asdfghjkl1234567890123 ===")
    r = client.get_repo("asdfghjkl1234567890123", "requests")
    if r.ok:
        print(f"  ✅ {r.data['full_name']}")
    else:
        print(f"  ❌ {r}")
        print(f"     error_type = {r.error_type}")
