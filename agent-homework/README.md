# GitHub 项目分析 Agent

基于 DeepSeek 大模型 + GitHub API 的命令行 Agent 课程作业。

## 📂 项目结构

```
agent-homework/
├── agent.py          # 主程序：Agent Loop 闭环 + --trace 轨迹
├── tools.py          # 工具箱：函数实现 + JSON Schema
├── requirements.txt  # 依赖清单
├── .env              # 密钥配置（不要上传！）
├── README.md         # 本文档
└── VERIFICATION.md   # 验收证据
```

## 🚀 运行方式

```bash
pip install -r requirements.txt

# 普通对话
python agent.py

# 带执行轨迹（调试用）
python agent.py --trace
```

## 🧠 Agent Loop 最小闭环（任务 2）

核心思路：**模型决定 → 执行工具 → 结果回传 → 模型回答**

```
用户："现在几点了？"
  ↓
Loop 1：调 LLM（带 tools 参数）
  → LLM 返回 tool_calls: [{name: "get_current_time", args: {}}]
  ↓
执行工具：get_current_time() → "当前时间 2026-09-07 17:45"
  ↓
Loop 2：把工具结果塞回 messages，再调 LLM
  → LLM 返回最终回答
```

### 关键代码点

1. **JSON Schema**（tools.py）：用 `type: "function"` 描述每个工具的名字、用途、参数结构，传给 LLM 当"菜单"
2. **TOOL_MAP**：函数名字符串 → 实际 Python 函数的映射表
3. **chat_with_tools()**：调 LLM 时带 `tools` 和 `tool_choice: "auto"` 参数
4. **run_agent_loop()**：循环检测 tool_calls，有就执行、塞回、再调，没有就拿 content 当最终回答
5. **--trace 参数**：开启后每一步都打印（Loop / 工具名 / 结果 / 最终回答）

### --trace 输出示例

```
🙋 你：现在几点了？
🤖 Agent：思考中...
  🔍 [Loop 1] 调 LLM，messages 共 2 条
  🔍 [LLM 返回] content=
  🔍 [检测到 tool_calls] 1 个
  🔍 [执行工具] get_current_time({'timezone': 'Asia/Shanghai'})
  🔍 [工具结果] 当前时间是：2026-09-07 17:45:42
  🔍 [Loop 2] 调 LLM，messages 共 4 条
  🔍 [最终回答] 当前时间是 2026年9月7日 17:45:42
🤖 Agent：当前时间是 **2026年9月7日 17:45:42**（北京时间）。
```

## 🛠️ 可用工具

| 工具 | 作用 |
|---|---|
| `get_current_time(timezone)` | 获取当前日期时间（内置，无需网络） |
| `get_github_repo_info(owner, repo)` | 查询 GitHub 仓库详情（Stars / Forks / 语言 / 简介） |

## 📝 配置

`.env` 文件里需要配：

- `GITHUB_TOKEN` — GitHub 个人访问令牌
- `DEEPSEEK_API_KEY` — DeepSeek 大模型 API Key
- `DEEPSEEK_BASE_URL` — API 地址
- `DEEPSEEK_MODEL` — 使用的模型名

---

## 🔒 Token 泄露风险与处理方式

### 风险

GitHub Token 和 DeepSeek API Key 等密钥相当于账户密码。一旦泄露，攻击者可以：
- **GitHub Token 泄露**：冒充你的身份操作仓库（删仓库、改代码、读私有仓库），消耗你的 API 配额
- **DeepSeek API Key 泄露**：盗用你的调用额度，产生费用

### 防护措施（本项目已做到）

1. **密钥不入源码**：`github_client.py` 通过 `os.getenv("GITHUB_TOKEN")` 读取，源码中无硬编码
2. **.gitignore 排除 .env**：`.gitignore` 文件第一行即为 `.env`，确保 `git add` 时不会将密钥文件纳入版本控制
3. **单元测试用假 Token**：`test_github_client.py` 中所有 Token 均为 `ghp_test_bearer` 等假值，不涉及真实凭据

### 万一泄露了怎么办（Revoke 流程）

如果发现 Token 已经泄露（比如不小心 `git push` 了 `.env`）：

1. **立即 Revoke（吊销）已泄露的 Token**
   - GitHub：打开 https://github.com/settings/tokens → 找到泄露的 Token → 点击 **Delete（删除）** 即可 Revoke
   - DeepSeek：打开 https://platform.deepseek.com/api_keys → 删除泄露的 Key

2. **清除 Git 历史中的密钥**（如果 .env 曾被提交过）
   - 从 Git 历史中移除该文件：`git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all`
   - 或者使用 [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) 清理
   - 然后强制推送：`git push --force`

3. **重新生成新 Token**，填入本地 `.env`，确认 `.gitignore` 生效后再提交

> 关键原则：**Revoke 越早越好**，泄露的 Token 在 Revoke 之前一直有效。

---

## 🧪 单元测试

运行命令：
```bash
python -m unittest test_github_client -v
```

测试输出（6 个测试全部通过）：
```
test_401_returns_dict_error ... ok
test_404_returns_dict_error ... ok
test_bearer_header ... ok
test_rate_limit_no_infinite_retry ... ok
test_rate_limit_retry_after_retry_once ... ok
test_success_returns_dict ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.055s

OK
```

测试覆盖：
- Bearer 请求头格式
- 成功返回 {ok:True, data}
- 401 返回 {ok:False, code:401, error}
- 404 返回 {ok:False, code:404, error}
- 限流按 Retry-After 退避重试一次成功
- 限流不无限重试（有次数上限）

---

## 🤖 Agent 和普通聊天机器人有什么区别？

我理解主要有 **3 点核心区别**：

### 1. Agent 能调用工具，聊天机器人只能靠脑子
普通聊天机器人只有模型本身的能力，你问它 "帮我查一下 Python requests 库有多少星"，它没法真的去 GitHub 看一眼，只能凭训练数据猜。
**Agent 不一样**，它手里有"工具箱"（tools.py），可以真的发起 HTTP 请求、查 GitHub API、读本地文件。

### 2. Agent 会多步执行，聊天机器人是一轮一问一答结束
聊天机器人典型模式是：你问 → 它答 → 结束。要完成一件复杂事，得用户一步步引导。
**Agent 是自主规划的**，你说 "帮我分析一下这个 GitHub 项目"，它会自己拆成：① 去拉仓库信息 → ② 看 README → ③ 扫目录结构 → ④ 汇总给你。

### 3. Agent 能自主决策，聊天机器人你说啥它干啥
聊天机器人不会 "多想一步"，你给它一个 prompt 它就按那个跑。
**Agent 有判断能力**：调用工具失败了会换参数重试；你说 "帮我分析 GitHub 项目"，它会判断是调 GitHub API 还是直接用大模型知识回答。

### 一句话总结
> 聊天机器人是"只会回答问题的嘴"，Agent 是"有手有脚有脑子的小助手"。
