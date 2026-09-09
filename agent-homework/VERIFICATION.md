# 验收说明

## 1. agent.py LLM 对话链路实测 ✅

本地运行命令：
```bash
python agent.py
```

实际运行日志（节选）：

```
==================================================
  🤖 GitHub 项目分析 Agent 已启动
==================================================
  你好，Sunny！这是 Agent 的第一个工具函数 🎉

  🧠 大模型：deepseek-chat (✅ 已连接)
  🛠️  可用工具 2 个：
    • say_hello
    • get_github_repo_info
==================================================

🙋 你：你好
🤖 Agent：思考中...
🤖 Agent：你好！我是 GitHub 项目分析 Agent，可以帮你查询和分析 GitHub 仓库信息。有什么需要帮助的吗？

🙋 你：帮我写个 Python 函数算斐波那契数列
🤖 Agent：思考中...
🤖 Agent：好的！这是一个经典的编程问题。我可以直接帮你写一个 Python 函数来计算斐波那契数列，不需要调用 GitHub 工具。
         (后面是完整的 Python 代码和解释)

🙋 你：quit
👋 再见！下次见～
```

可以确认：**普通输入走 `self.call_llm()` 分支，不依赖"分析 xxx/xxx"的工具调用路径，LLM 能对任意问题返回生成式回答。**

## 2. GitHub Token 配置 ✅

已在本机 `.env` 文件中配置 `GITHUB_TOKEN`，并实际调用成功：

```
🔍 正在测试 GitHub API...
✅ API 通了！Token 有效！
   仓库：psf/requests
   Stars：54286
   简介：A simple, yet elegant, HTTP library.
```

`.env` 文件未上传到仓库（符合安全规范），密钥仅在本地生效。

## 3. DeepSeek API Key 配置 ✅

同样在本机 `.env` 中配置 `DEEPSEEK_API_KEY`，LLM 调用测试成功。代码通过 `python-dotenv + os.getenv` 读取密钥，未硬编码。

---

## 任务 2：Agent Loop 最小闭环实测 ✅

运行命令：
```bash
python agent.py --trace
```

### 测试场景 A：内置工具 get_current_time

```
🙋 你：现在几点了？
🤖 Agent：思考中...
  🔍 [Loop 1] 调 LLM，messages 共 2 条
  🔍 [LLM 返回] content=
  🔍 [检测到 tool_calls] 1 个
  🔍 [执行工具] get_current_time({'timezone': 'Asia/Shanghai'})
  🔍 [工具结果] 当前时间是：2026-09-07 17:45:42，时区 Asia/Shanghai
  🔍 [Loop 2] 调 LLM，messages 共 4 条
  🔍 [最终回答] 当前时间是 2026年9月7日 17:45:42
🤖 Agent：当前时间是 **2026年9月7日 17:45:42**（北京时间）。
```

闭环验证：
- ✅ 模型自主决定调用工具（未硬编码关键词匹配）
- ✅ JSON Schema 生效（LLM 知道有 get_current_time 工具）
- ✅ 执行 → 回传 → 再调用的 Loop 跑了 2 轮
- ✅ 最终回答基于工具真实结果

### 测试场景 B：GitHub 工具 get_github_repo_info

```
🙋 你：帮我查一下 psf/requests 这个仓库有多少星
🤖 Agent：思考中...
  🔍 [Loop 1] 调 LLM，messages 共 4 条
  🔍 [LLM 返回] content=
  🔍 [检测到 tool_calls] 1 个
  🔍 [执行工具] get_github_repo_info({'owner': 'psf', 'repo': 'requests'})
  🔍 [工具结果] {"full_name": "psf/requests", "stars": 54286, ...}
  🔍 [Loop 2] 调 LLM，messages 共 6 条
  🔍 [最终回答] psf/requests 仓库目前有 54,286 颗星
🤖 Agent：**psf/requests** 仓库目前有 **54,286 颗星**，**10,131 个 Fork**，...
```

### role="tool" 回传的关键代码片段（agent.py run_agent_loop）

```python
# 工具执行完，必须以 role="tool" + tool_call_id 塞回 messages
# 这样 LLM 才能看到工具返回值，基于它生成最终回答
for tc in tool_calls:
    tc_id = tc["id"]                          # 模型给的调用 ID
    func_name = tc["function"]["name"]
    func_args = json.loads(tc["function"]["arguments"])

    # 1. 执行工具
    tool_fn = TOOL_MAP[func_name]
    tool_result = str(tool_fn(**func_args))

    # 2. ⭐ 构造 role="tool" 消息并回传 — 这是闭环的关键！
    messages.append({
        "role": "tool",                       # 固定字段：告诉模型这是工具返回
        "tool_call_id": tc_id,                # 必须和上面 tc["id"] 一致
        "name": func_name,                    # 工具名
        "content": tool_result,               # 工具真实返回值
    })
```

运行时 trace 里可看到：
```
🔍 [检测到 tool_calls] 1 个
🔍 [执行工具] get_current_time({'timezone': 'Asia/Shanghai'})
🔍 [工具结果] 当前时间是：2026-09-09 15:16:27，时区 Asia/Shanghai
🔍 [回传] role=tool, tool_call_id=call_00_diN6zPgDyKaISMs1hSmS2258   ← 关键证据
🔍 [Loop 2] 调 LLM，messages 共 4 条
🔍 [最终回答] 当前时间是 2026年9月9日 下午3点16分27秒
```

### 💡 为什么工具结果必须回传给模型？

这是 Agent 闭环的核心设计，原因有三：

**1. LLM 根本看不到工具执行结果**
我们代码里直接 `print(tool_result)` — 这只是打印在终端，LLM 完全不知道执行返回了什么。LLM 的"眼睛"就是 messages 列表，如果不把结果塞进 messages，它就当工具什么都没返回。

**2. 最终回答必须基于工具返回值生成**
用户问"现在几点了？"，工具返回 `15:16:27`。如果不把这个数字给 LLM，它怎么回答？只能瞎编。**把结果回传后，LLM 才能基于真实数据生成自然语言回答**："现在是下午 3 点 16 分"。

**3. 多工具串联时更关键**
假设一个任务需要：先调 GitHub API 拿仓库信息 → 再调另一个工具分析代码 → 最后总结。每一步的返回值都是下一步的输入，不回传就断链了。

```
如果只是 print 工具结果 → LLM 看不到 → 只能瞎编
如果是 role="tool" 回传 → LLM 能看到真实数据 → 生成准确回答 ✅
```

### --trace 生成的 agent_trace.json

已在仓库根目录上传实际运行生成的 [agent_trace.json](https://github.com/Sunny741106/deepseek-chatbot/blob/main/agent-homework/agent_trace.json)，共 10 条记录，包含完整闭环轨迹（用户输入 → Loop1 调 LLM → tool_calls → 执行 → role=tool 回传 → Loop2 调 LLM → 最终回答）。

### 关键实现确认

| 要求 | 实现 |
|---|---|
| JSON Schema 声明工具 | tools.py 中 GET_CURRENT_TIME_SCHEMA / GET_GITHUB_REPO_INFO_SCHEMA |
| 模型自主决定调用 | chat_with_tools() 传 tools + tool_choice="auto" |
| 执行 → 回传 → 回答闭环 | run_agent_loop() 循环检测 tool_calls，用 role="tool" 回传 |
| --trace 写入文件 | log() 追加 trace_log，save_trace() 写 agent_trace.json |
| 解释回传原因 | 见上方"为什么工具结果必须回传给模型"段落 |
