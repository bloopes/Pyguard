@echo off
chcp 65001 >nul
:: 强制跳转到脚本所在目录，防止路径错乱
cd /d "%~dp0"

set "APP_NAME=PyGuard"
set "TARGET_PATH=%~f0"
set "WORKING_DIR=%~dp0"
set "ICON_PATH=%~dp0pyguard.ico"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\%APP_NAME%.lnk"

title %APP_NAME% 启动调试模式

echo [1/3] 检查桌面快捷方式...
if not exist "%SHORTCUT_PATH%" (
    echo [!] 正在创建快捷方式...
    
    :: 简化为单行指令，避免转义符错误
    powershell -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%TARGET_PATH%'; $s.WorkingDirectory='%WORKING_DIR%'; if(Test-Path '%ICON_PATH%'){$s.IconLocation='%ICON_PATH%'}; $s.Save()"
    
    if exist "%SHORTCUT_PATH%" (echo [+] 快捷方式创建成功！) else (echo [-] 快捷方式创建失败。)
) else (
    echo [i] 快捷方式已存在，跳过。
)

echo.
echo [2/3] 检查 Python 环境...
set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
    echo [i] 使用虚拟环境: .venv
)

echo.
echo [3/3] 启动程序...
:: 运行程序
%PY_EXE% cli/interface.py

:: 如果程序正常退出或崩溃，都会停在这里
echo.
echo ---------------------------------------
pause