@echo off
title [EAP_Dashboard] EAP_Dashboard APP

chcp 65001 >nul
cd /d %~dp0

echo 🔄 等待網路連線就緒...
for /l %%i in (3,-1,1) do (
    <nul set /p="⏳ %%i 秒後啟動程式... "
    timeout /t 1 >nul
    echo.
)

echo ✅ 啟動 Python 腳本！
"C:\Users\A3cim\AppData\Local\Programs\Python\Python39\python.exe" EAP_dashboard.py

pause
