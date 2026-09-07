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
