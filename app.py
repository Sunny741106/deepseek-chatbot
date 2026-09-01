# app.py —— 套壳聊天机器人后端
# 职责：接收前端消息 → 调用 DeepSeek API → 返回回复
import os
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# 加载 .env 里的环境变量（API Key 等）
load_dotenv()

app = Flask(__name__)

# 从环境变量读取配置，避免把 Key 硬编码进代码
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 内存里存对话历史（演示用，重启后清空）
conversation_history = []


@app.route("/")
def index():
    """返回前端聊天页面"""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """核心接口：接收用户消息，返回 AI 回复"""
    # 1. 拿到前端传来的 JSON
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    if not API_KEY:
        return jsonify({"error": "请先在 .env 文件中配置 DEEPSEEK_API_KEY"}), 500

    # 2. 把用户消息追加到历史
    conversation_history.append({"role": "user", "content": user_message})

    # 3. 调用 DeepSeek Chat Completions API
    try:
        resp = requests.post(
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
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        bot_reply = result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError:
        # 把远端返回的错误原样吐给前端，方便调试
        try:
            err = resp.json()
        except Exception:
            err = {"detail": resp.text}
        return jsonify({"error": f"上游 API 报错: {err}"}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"网络请求失败: {e}"}), 502

    # 4. 把 AI 回复也记进历史，实现多轮对话
    conversation_history.append({"role": "assistant", "content": bot_reply})

    # 5. 控制历史长度，避免上下文无限膨胀
    if len(conversation_history) > 20:
        conversation_history.pop(0)
        conversation_history.pop(0)

    return jsonify({"reply": bot_reply})


@app.route("/clear", methods=["POST"])
def clear():
    """清空对话历史"""
    global conversation_history
    conversation_history = []
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    # debug=True 方便开发时自动重载；生产环境请关闭
    app.run(host="127.0.0.1", port=5000, debug=True)
