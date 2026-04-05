#!/usr/bin/env pwsh
# 备份文件夹诊断工具

param(
    [Parameter(Mandatory = $false)]
    [string]$BackupPath = "D:\datas\RagflowAuth"
)

Write-Host "=== 备份文件夹诊断工具 ===" -ForegroundColor Cyan
Write-Host ""

# 检查备份路径
if (-not (Test-Path $BackupPath)) {
    Write-Host "❌ 备份路径不存在: $BackupPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 备份路径存在: $BackupPath" -ForegroundColor Green
Write-Host ""

# 列出所有备份文件夹
Write-Host "查找备份文件夹..." -ForegroundColor Cyan
$backupFolders = Get-ChildItem -Path $BackupPath -Directory | Where-Object { $_.Name -like "migration_pack_*" } | Sort-Object LastWriteTime -Descending

if ($backupFolders.Count -eq 0) {
    Write-Host "❌ 未找到任何备份文件夹" -ForegroundColor Red
    Write-Host ""
    Write-Host "请检查：" -ForegroundColor Yellow
    Write-Host "1. 备份路径是否正确: $BackupPath" -ForegroundColor White
    Write-Host "2. 是否有迁移包（migration_pack_*）" -ForegroundColor White
    exit 1
}

Write-Host "找到 $($backupFolders.Count) 个备份文件夹:" -ForegroundColor Green
Write-Host ""

foreach ($folder in $backupFolders) {
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "文件夹: $($folder.Name)" -ForegroundColor Cyan
    Write-Host "路径: $($folder.FullName)" -ForegroundColor White
    Write-Host "修改时间: $($folder.LastWriteTime)" -ForegroundColor White
    Write-Host ""

    # 检查必要文件
    $authDb = Join-Path $folder.FullName "auth.db"
    $imagesTar = Join-Path $folder.FullName "images.tar"
    $volumesDir = Join-Path $folder.FullName "volumes"
    $uploadsDir = Join-Path $folder.FullName "uploads"

    Write-Host "包含文件:" -ForegroundColor Cyan

    if (Test-Path $authDb) {
        $size = (Get-Item $authDb).Length / 1KB
        Write-Host "  ✅ auth.db ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ auth.db (不存在)" -ForegroundColor Red
    }

    if (Test-Path $imagesTar) {
        $size = (Get-Item $imagesTar).Length / 1MB
        Write-Host "  ✅ images.tar ($([math]::Round($size, 2)) MB)" -ForegroundColor Green

        # 检查文件路径是否有问题
        $pathIssue = $false
        try {
            $testPath = Test-Path -LiteralPath $imagesTar -PathType Leaf
            if (-not $testPath) {
                Write-Host "     ⚠️  路径测试失败" -ForegroundColor Yellow
                $pathIssue = $true
            }
        } catch {
            Write-Host "     ⚠️  路径测试异常: $_" -ForegroundColor Yellow
            $pathIssue = $true
        }

        if ($pathIssue) {
            Write-Host "     建议: 使用手动上传脚本" -ForegroundColor Yellow
            Write-Host "     .\tool\scripts\upload-large-file.ps1 -LocalFile '$($imagesTar)'" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ❌ images.tar (不存在)" -ForegroundColor Red
    }

    if (Test-Path $volumesDir) {
        $volFiles = Get-ChildItem -Path $volumesDir -Filter "*.tar.gz" | Measure-Object
        Write-Host "  ✅ volumes/ ($($volFiles.Count) 个文件)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ volumes/ (不存在)" -ForegroundColor Red
    }

    if (Test-Path $uploadsDir) {
        Write-Host "  ✅ uploads/ (存在)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ uploads/ (不存在)" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Gray
Write-Host ""
Write-Host "最近的备份（按修改时间）：" -ForegroundColor Cyan
$latestBackup = $backupFolders | Select-Object -First 1
Write-Host "  路径: $($latestBackup.FullName)" -ForegroundColor White
Write-Host "  时间: $($latestBackup.LastWriteTime)" -ForegroundColor White
Write-Host ""
Write-Host "建议操作：" -ForegroundColor Yellow
Write-Host "1. 在 tool.py 中选择这个文件夹：" -ForegroundColor White
Write-Host "   $($latestBackup.FullName)" -ForegroundColor White
Write-Host ""
Write-Host "2. 如果 images.tar 上传失败，使用手动上传：" -ForegroundColor White
Write-Host "   .\tool\scripts\upload-large-file.ps1 -LocalFile '$(Join-Path $latestBackup.FullName images.tar)'" -ForegroundColor Gray
