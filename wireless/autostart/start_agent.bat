@echo off
chcp 936 >nul
title MYBIT PC Agent

rem ============================================================
rem  使用前请把下面的 <PROJECT_DIR> 改成你的实际项目目录
rem  例如：cd /d "D:\myproject\mybit-ai-companion"
rem ============================================================
cd /d "<PROJECT_DIR>"

set PYTHONIOENCODING=utf-8

echo ============================================
echo  MYBIT PC Agent
echo ============================================
echo.

:loop
echo [%date% %time%] start pc_agent
python pc_agent.py
echo [%date% %time%] exited, restart in 5s
timeout /t 5 /nobreak >nul
goto loop
