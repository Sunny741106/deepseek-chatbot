@echo off
chcp 65001 >nul
title 套壳聊天机器人 (FastAPI + DeepSeek)
echo ============================================
echo    套壳聊天机器人 - 一键启动
echo    框架：FastAPI + uvicorn + DeepSeek
echo ============================================
echo.
echo [1/2] 进入项目目录...
cd /d "%~dp0"
echo [2/2] 启动后端服务 (端口 8000) ...
echo.
echo     浏览器访问:   http://127.0.0.1:8000
echo     退出:         按 Ctrl + C
echo.
uvicorn main:app --reload --port 8000
