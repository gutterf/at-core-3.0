@echo off
chcp 65001 >nul
cd /d "C:\Users\admin\Desktop\冷咖啡全自动破甲"

set PY312=C:\Users\admin\AppData\Local\Programs\Python\Python312\pythonw.exe
set PY312C=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%PY312%" (
    echo [ERROR] pythonw.exe 不存在：%PY312%
    pause
    exit /b 1
)

del /q "C:\Users\admin\Desktop\冷咖啡全自动破甲\crash.log" 2>nul

start "" "%PY312%" "C:\Users\admin\Desktop\冷咖啡全自动破甲\启动_稳定.pyw"
exit /b 0
