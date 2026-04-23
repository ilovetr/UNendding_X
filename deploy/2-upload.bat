@echo off
chcp 65001 >nul
title 上传部署包到服务器

echo.
echo ========================================
echo   川流/UnendingX 部署包上传工具
echo ========================================
echo.
echo 请确保腾讯云控制台已开放 22 端口
echo.

set /p SERVER_IP="服务器 IP (直接回车使用默认 81.70.187.125): "
if "%SERVER_IP%"=="" set SERVER_IP=81.70.187.125

set /p SSH_USER="SSH 用户名 (root/lighthouse/ubuntu，直接回车用 lighthouse): "
if "%SSH_USER%"=="" set SSH_USER=lighthouse

set /p KEY_PATH="密钥文件路径 (直接回车使用默认): "
if "%KEY_PATH%"=="" set KEY_PATH=%USERPROFILE%\.ssh\unendingx.pem

echo.
echo [1/4] 复制安装脚本到临时目录...
copy /Y "E:\工作\AI\agent_grounp\deploy\1-install.sh" "%TEMP%\1-install.sh" >nul
copy /Y "E:\工作\AI\agent_grounp\deploy\README.md" "%TEMP%\deploy-readme.md" >nul
echo       完成

echo.
echo [2/4] 尝试上传...
echo       服务器: %SSH_USER%@%SERVER_IP%
echo       密钥:   %KEY_PATH%

:: 尝试上传到 /tmp/
pscp -i "%KEY_PATH%" -o StrictHostKeyChecking=no "%TEMP%\1-install.sh" %SSH_USER%@%SERVER_IP%:/tmp/1-install.sh
if errorlevel 1 (
    echo.
    echo [2/4 失败] SCP 上传失败，请手动上传
    echo   服务器 IP: %SERVER_IP%
    echo   密钥文件:  %KEY_PATH%
    echo.
    echo   手动上传方法:
    echo   1. 用腾讯云控制台的 VNC 登录服务器
    echo   2. 把 1-install.sh 的内容粘贴到: vi /tmp/1-install.sh
    echo   3. chmod +x /tmp/1-install.sh
    echo.
) else (
    echo       上传成功
    echo.
    echo [3/4] 上传 README...
    pscp -i "%KEY_PATH%" -o StrictHostKeyChecking=no "%TEMP%\deploy-readme.md" %SSH_USER%@%SERVER_IP%:/tmp/deploy-readme.md
    echo       完成
    echo.
    echo [4/4] 设置执行权限并运行...
    plink -i "%KEY_PATH%" -o StrictHostKeyChecking=no %SSH_USER%@%SERVER_IP% "chmod +x /tmp/1-install.sh && echo '权限设置成功'"
    echo.
    echo ========================================
    echo   上传完成！
    echo ========================================
    echo.
    echo 下一步，请 SSH 登录服务器运行安装：
    echo   ssh -i "%KEY_PATH%" %SSH_USER%@%SERVER_IP%
    echo   bash /tmp/1-install.sh
    echo.
    echo 或让 plink 自动运行（非交互式服务器）:
    echo   plink -i "%KEY_PATH%" %SSH_USER%@%SERVER_IP% "bash /tmp/1-install.sh"
    echo.
)

del /Q "%TEMP%\1-install.sh" 2>nul
del /Q "%TEMP%\deploy-readme.md" 2>nul
pause
