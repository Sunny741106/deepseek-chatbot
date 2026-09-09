"""
test_github_client.py — GitHubClient 单元测试

用 unittest.mock 模拟 HTTP 响应，不发起真实网络请求。

运行方式：
  python -m unittest test_github_client -v
"""

import unittest
from unittest import mock

from github_client import GitHubClient


def fake_response(status_code, json_data=None, headers=None):
    """构造一个假的 requests.Response"""
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = headers or {}
    resp.text = str(json_data)
    return resp


class GitHubClientTest(unittest.TestCase):

    # ---------- 测试 1：请求头是 Bearer 格式 ----------

    @mock.patch("github_client.requests.Session.request")
    def test_bearer_header(self, mock_req):
        mock_req.return_value = fake_response(200, {"id": 1})

        client = GitHubClient(token="ghp_test_bearer")

        # 校验请求头确实是 Bearer <token>
        self.assertEqual(
            client.session.headers["Authorization"],
            "Bearer ghp_test_bearer",
            "请求头必须是 Authorization: Bearer <token>",
        )

    # ---------- 测试 2：成功返回 {ok:True, data} ----------

    @mock.patch("github_client.requests.Session.request")
    def test_success_returns_dict(self, mock_req):
        payload = {
            "full_name": "psf/requests",
            "stargazers_count": 54000,
            "forks_count": 10000,
            "language": "Python",
        }
        mock_req.return_value = fake_response(200, payload)

        client = GitHubClient(token="t")
        result = client.get_repo("psf", "requests")

        # 必须是字典且结构为 {ok, data}
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], payload)

    # ---------- 测试 3：404 返回 {ok:False, code:404, error} ----------

    @mock.patch("github_client.requests.Session.request")
    def test_404_returns_dict_error(self, mock_req):
        mock_req.return_value = fake_response(404, {"message": "Not Found"})

        client = GitHubClient(token="t")
        result = client.get_repo("foo", "no_such_repo")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 404)
        self.assertTrue(result["error"])

    # ---------- 测试 4：401 返回 {ok:False, code:401, error} ----------

    @mock.patch("github_client.requests.Session.request")
    def test_401_returns_dict_error(self, mock_req):
        mock_req.return_value = fake_response(401, {"message": "Bad credentials"})

        client = GitHubClient(token="bad_token")
        result = client.get("repositories")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 401)
        self.assertTrue(result["error"])

    # ---------- 测试 5：限流后按 Retry-After 退避重试成功 ----------

    @mock.patch("time.sleep")
    @mock.patch("github_client.requests.Session.request")
    def test_rate_limit_retry_after_retry_once(self, mock_req, mock_sleep):
        # 第一次响应 403 限流，带 Retry-After: 5
        # 第二次响应 200 成功
        mock_req.side_effect = [
            fake_response(
                403,
                {"message": "rate limited"},
                headers={"Retry-After": "5"},
            ),
            fake_response(200, {"full_name": "psf/requests"}),
        ]

        client = GitHubClient(token="t")
        result = client.get("some/path")

        # 重试成功
        self.assertTrue(result["ok"])
        # 确实 sleep 了 Retry-After 秒（5 秒）
        mock_sleep.assert_called_once_with(5)
        # 确实请求了两次（一次失败 + 一次重试）
        self.assertEqual(mock_req.call_count, 2)


if __name__ == "__main__":
    unittest.main()