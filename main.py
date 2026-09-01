# main.py —— 套壳聊天机器人后端（FastAPI 版本）
# 职责：接收前端消息 → 调用 DeepSeek API → 返回回复
# 启动命令：uvicorn main:app --reload --port 8000
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# 加载 .env 里的环境变量（API Key 等）
load_dotenv()

# 从环境变量读取配置，避免把 Key 硬编码进代码
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 内存里存对话历史（演示用，重启后清空）
conversation_history: list[dict] = []


# ---------- 请求/响应模型（Pydantic） ----------
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息")


class ChatResponse(BaseModel):
    reply: str
    history_size: int


# ---------- 应用生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 DeepSeek ChatBot (FastAPI) 启动在 http://127.0.0.1:8000")
    yield


app = FastAPI(
    title="套壳聊天机器人",
    description="基于 FastAPI + DeepSeek 的聊天机器人后端",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------- CORS 中间件：允许跨域请求（兼容不同部署方式） ----------
# 同源部署（前后端都走 127.0.0.1:8000）时本来不需要 CORS
# 但加上 CORS 更安全，即便以后前端跑在其他端口/域名也能正常访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 演示环境放开所有来源；生产环境请替换为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 首页：返回前端聊天页面 ----------
@app.get("/", response_class=HTMLResponse)
async def index():
    # FastAPI 不自带模板引擎，这里直接把 index.html 读出来返回
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ---------- 核心接口：聊天 ----------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """核心接口：接收用户消息，返回 AI 回复"""
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    if not API_KEY:
        raise HTTPException(status_code=500, detail="请先在 .env 文件中配置 DEEPSEEK_API_KEY")

    # 把用户消息追加到历史
    conversation_history.append({"role": "user", "content": user_message})

    # 调用 DeepSeek Chat Completions API
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": conversation_history,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail={"upstream_status": resp.status_code, "body": resp.text[:500]},
                )
            result = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"网络请求失败: {e}")

    bot_reply = result["choices"][0]["message"]["content"].strip()

    # 把 AI 回复也记进历史，实现多轮对话
    conversation_history.append({"role": "assistant", "content": bot_reply})

    # 控制历史长度，用切片直接保留最后 20 条（比 pop 两次更健壮，不怕长度奇偶）
    MAX_HISTORY = 20
    if len(conversation_history) > MAX_HISTORY:
        conversation_history[:] = conversation_history[-MAX_HISTORY:]

    return ChatResponse(reply=bot_reply, history_size=len(conversation_history))


# ---------- 清空对话历史 ----------
@app.post("/clear")
async def clear():
    """清空对话历史"""
    conversation_history.clear()
    return JSONResponse({"status": "cleared"})


if __name__ == "__main__":
    # 直接 python main.py 也能跑（开发用），生产用 uvicorn main:app
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
