# GitHub 项目分析 Agent

基于 DeepSeek 大模型 + GitHub API 的命令行 Agent 课程作业。

## 🤖 Agent 和普通聊天机器人有什么区别？

我理解主要有 **3 点核心区别**：

### 1. Agent 能调用工具，聊天机器人只能靠脑子
普通聊天机器人（比如早期套壳机器人）只有模型本身的能力，你问它 "帮我查一下 Python requests 库有多少星"，它没法真的去 GitHub 看一眼，只能凭训练数据猜。
**Agent 不一样**，它手里有"工具箱"（tools.py），可以真的发起 HTTP 请求、查 GitHub API、读本地文件。比如这个项目里的 `get_github_repo_info` 工具，Agent 说调就调。

### 2. Agent 会多步执行，聊天机器人是一轮一问一答结束
聊天机器人典型模式是：你问 → 它答 → 结束。要完成一件复杂事，得用户一步步引导。
**Agent 是自主规划的**，你说 "帮我分析一下这个 GitHub 项目"，它会自己拆成：① 去拉仓库信息 → ② 看 README → ③ 扫目录结构 → ④ 汇总给你。中间不需要你再说话。

### 3. Agent 能自主决策，聊天机器人你说啥它干啥
聊天机器人不会 "多想一步"，你给它一个 prompt 它就按那个跑，跑不通就报错。
**Agent 有判断能力**：调用工具失败了会换参数重试，或者换个工具；发现路径不对会停下来问你；你说 "帮我分析 GitHub 项目"，它会判断是调 GitHub API 还是直接用大模型知识回答。

### 一句话总结
> 聊天机器人是"只会回答问题的嘴"，Agent 是"有手有脚有脑子的小助手"。

## 📂 项目结构

```
agent-homework/
├── agent.py          # 主程序入口，接入 DeepSeek LLM + CLI 对话
├── tools.py          # 工具箱（say_hello、get_github_repo_info）
├── requirements.txt  # 依赖清单
├── .env              # 密钥配置（不要上传！）
└── README.md         # 本文档
```

## 🚀 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Agent
python agent.py
```

## 🛠️ 可用工具

| 工具 | 作用 |
|---|---|
| `say_hello(name)` | 打招呼（演示用） |
| `get_github_repo_info(owner, repo)` | 查 GitHub 仓库基本信息 |

## 📝 配置

`.env` 文件里需要配：

- `GITHUB_TOKEN` — GitHub 个人访问令牌（用于调 GitHub API）
- `DEEPSEEK_API_KEY` — DeepSeek 大模型 API Key
- `DEEPSEEK_BASE_URL` — API 地址
- `DEEPSEEK_MODEL` — 使用的模型名
