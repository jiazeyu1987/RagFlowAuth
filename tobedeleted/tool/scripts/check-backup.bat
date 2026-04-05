@echo off
setlocal enabledelayedexpansion

echo ============================================
echo RagflowAuth 备份文件夹验证工具
echo ============================================
echo.

set "BACKUP_DIR=D:\datas\RagflowAuth"

echo 检查备份目录: %BACKUP_DIR%
echo.

for /f "delims=" %%d in ('dir /b /ad "%BACKUP_DIR%\migration_pack_*" 2^>nul') do (
    set "FULL_PATH=%BACKUP_DIR%\%%d"

    echo 文件夹: %%d
    dir "!FULL_PATH!" | find "images.tar" >nul 2^>nul
    if !errorlevel! equ 0 (
        echo   [OK] 包含 images.tar
        for /f "tokens=3" %%s in ('dir "!FULL_PATH!\images.tar" ^| find "images.tar"') do (
            echo   大小: %%s
        )
        echo   推荐使用此文件夹: !FULL_PATH!
        echo.
    ) else (
        echo   [SKIP] 不包含 images.tar
        echo.
    )
)

echo ============================================
echo.
echo 使用说明:
echo 1. 打开 tool.py
echo 2. 进入"数据还原"页签
echo 3. 点击"选择备份文件夹"
echo 4. 选择上面标记 [OK] 的文件夹
echo 5. 勾选需要还原的内容
echo 6. 点击"开始还原"
echo.
pause
