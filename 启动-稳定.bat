@echo off
chcp 65001 >nul
title 冷咖啡 · 全自动破甲
cd /d "%~dp0"
start "" "C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0coffee_breaker.py"
exit
