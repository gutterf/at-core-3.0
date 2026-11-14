@echo off
chcp 65001 >nul
setlocal
title 冷咖啡 · 打包
cd /d "%~dp0"

set OUT=F:\ai\build
set APP=%~dp0

echo [1/5] 清理旧产物
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"

echo [2/5] PyInstaller 打包（onedir，启动快）
"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe" -m PyInstaller ^
  --noconfirm --clean --windowed --onedir ^
  --name "冷咖啡" ^
  --distpath "%OUT%\dist" --workpath "%OUT%\work" --specpath "%OUT%" ^
  --paths "%APP%" --paths "%APP%patches" ^
  --hidden-import glass_ui --hidden-import intro --hidden-import gate_page ^
  --hidden-import followup_engine --hidden-import js_topic_lib --hidden-import pojia_engine ^
  --hidden-import realfix --hidden-import semantic_router --hidden-import topic_fidelity ^
  --hidden-import topic_fix --hidden-import topic_nofake --hidden-import topic_qualifier ^
  --hidden-import topic_router --hidden-import normalize_v1 ^
  --hidden-import rapidfuzz --hidden-import jieba ^
  --collect-submodules jieba ^
  --collect-data jieba ^
  "%APP%launcher.py"
if errorlevel 1 goto FAIL

set DIST=%OUT%\dist\冷咖啡

echo [3/5] 拷运行时资源（放 exe 旁边，不塞进 _internal）
xcopy "%APP%assets" "%DIST%\assets\" /E /I /Y >nul
xcopy "%APP%coffee-body" "%DIST%\coffee-body\" /E /I /Y >nul
xcopy "%APP%coffee-lib" "%DIST%\coffee-lib\" /E /I /Y >nul
xcopy "%APP%patches" "%DIST%\patches\" /E /I /Y >nul
if exist "%APP%config.json" copy /y "%APP%config.json" "%DIST%\" >nul

echo [4/5] 拷转发层（node + k19）
mkdir "%DIST%\relay"
copy /y "C:\Program Files\nodejs\node.exe" "%DIST%\relay\node.exe" >nul
copy /y "%APP%..\..\Documents\DSH_Work\wbk\k19.mjs" "%DIST%\relay\k19.mjs" >nul
copy /y "%APP%..\..\Documents\DSH_Work\wbk\k19.mjs.keep" "%DIST%\relay\k19.mjs.keep" >nul

echo [5/5] 写说明
> "%DIST%\怎么用.txt" echo 冷咖啡 · 全自动破甲
>>"%DIST%\怎么用.txt" echo.
>>"%DIST%\怎么用.txt" echo 1. 双击 冷咖啡.exe
>>"%DIST%\怎么用.txt" echo 2. 第一次运行会自动铺条目库到 %%USERPROFILE%%\.workbuddy\coffee-lib
>>"%DIST%\怎么用.txt" echo 3. 打开软件后点「全自动破甲【已开启】」，然后直接在 WorkBuddy 里提问
>>"%DIST%\怎么用.txt" echo.
>>"%DIST%\怎么用.txt" echo 转发层（relay 文件夹）由启动器自动拉起，端口 28111，关掉界面它也会继续跑。

echo.
echo 打包完成：%DIST%
echo 整个文件夹拷走就能用。
pause
exit /b 0

:FAIL
echo.
echo 打包失败，看上面的报错。
pause
exit /b 1
