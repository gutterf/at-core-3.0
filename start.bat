@echo off
chcp 65001 >nul
title 冷咖啡 · 全自动破甲
cd /d "%~dp0"

set PY="C:\Users\admin\AppData\Local\Programs\Python\Python312\pythonw.exe"
if not exist %PY% set PY=pythonw

start "" %PY% "%~dp0coffee_breaker.py"
exit
