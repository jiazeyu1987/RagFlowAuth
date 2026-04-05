# RagflowAuth 备份下载脚本（通用版）
# 用途：从服务器下载最新的备份包（自动选择增量或全量）

# 配置参数
$Server     = '172.30.30.57'
$ServerUser = 'root'
$SshPort    = 22
$LocalPath  = 'D:\datas'
$RemotePath = '/opt/ragflowauth/backups'
$LogPath    = 'D:\ProjectPackage\RagflowAuth\tool\scripts\backup-download.log'

# 创建本地目录（如不存在）
New-Item -ItemType Directory -Force -Path $LocalPath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null

function Write-Log {
    param([Parameter(Mandatory)][string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogPath -Value $logMessage
}

Write-Log '========== 开始备份下载任务（通用版）=========='

$tempPath = $null

try {
    Write-Log "测试服务器连接（SSH 端口 $SshPort）..."
    $portOk = $false
    if (Get-Command Test-NetConnection -ErrorAction SilentlyContinue) {
        $portOk = Test-NetConnection -ComputerName $Server -Port $SshPort -InformationLevel Quiet
    }
    else {
        Write-Log '未找到 Test-NetConnection，改用 ICMP Ping...'
        $portOk = Test-Connection -ComputerName $Server -Count 2 -Quiet
    }
    if (-not $portOk) {
        throw "无法连接到服务器 ${Server}:$SshPort"
    }
    Write-Log '服务器连接成功'

    Write-Log '检查 ssh 和 scp 命令...'
    $sshCmd = Get-Command ssh -ErrorAction SilentlyContinue | Where-Object { $_.Source -like '*Windows*' -or $_.Source -like '*System32*' }
    $scpCmd = Get-Command scp -ErrorAction SilentlyContinue | Where-Object { $_.Source -like '*Windows*' -or $_.Source -like '*System32*' }

    if (-not $sshCmd) {
        $sshCmd = Get-Command ssh -ErrorAction SilentlyContinue
    }
    if (-not $scpCmd) {
        $scpCmd = Get-Command scp -ErrorAction SilentlyContinue
    }

    if (-not $sshCmd -or -not $scpCmd) {
        throw '找不到 ssh 或 scp 命令。请确保已安装 OpenSSH Client。'
    }
    Write-Log "ssh 可用: $($sshCmd.Source)"
    Write-Log "scp 可用: $($scpCmd.Source)"

    Write-Log '查找服务器上最新的备份包...'
    $findLatestCmd = "ls -td ${RemotePath}/*_pack_* 2>/dev/null | head -1"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $findLatestCmd)
    $latestOutput = & $sshCmd.Source @sshArgs 2>&1
    $latestBackup = ($latestOutput | Out-String).Trim()

    if (-not $latestBackup -or $latestBackup -match 'No such file' -or $latestBackup -eq '') {
        throw "未找到备份包。请检查服务器路径: ${RemotePath}"
    }

    $latestBackupName = Split-Path $latestBackup -Leaf

    # 判断备份类型
    if ($latestBackupName -match 'full_backup_pack') {
        $backupType = '全量备份'
    }
    elseif ($latestBackupName -match 'migration_pack') {
        $backupType = '增量备份'
    }
    else {
        $backupType = '未知类型'
    }

    Write-Log "最新备份: $latestBackupName ($backupType)"

    # 检查是否有压缩版本
    $checkCompressedCmd = "test -f ${RemotePath}/${latestBackupName}.tar.gz && echo 'EXISTS' || echo 'NOT_FOUND'"
    $sshArgs = @('-q', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL', '-p', $SshPort, "${ServerUser}@${Server}", $checkCompressedCmd)
    $compressedOutput = (& $sshCmd.Source @sshArgs 2>&1).Trim()

    $useCompressed = ($compressedOutput -eq 'EXISTS')
    if ($useCompressed) {
        Write-Log "发现压缩版本，将下载 ${latestBackupName}.tar.gz"
    }

    $tempPath = Join-Path $env:TEMP "ragflow_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Force -Path $tempPath | Out-Null
    Write-Log "创建临时目录: $tempPath"

    if ($useCompressed) {
        Write-Log "开始下载压缩文件: ${latestBackupName}.tar.gz ..."
        $remoteSource = "${ServerUser}@${Server}:${RemotePath}/${latestBackupName}.tar.gz"
        $localDest = $tempPath

        $scpArgs = @(
            '-q'
            '-P', $SshPort
            '-o', 'StrictHostKeyChecking=no'
            '-o', 'UserKnownHostsFile=NUL'
            $remoteSource
            $localDest
        )

        Write-Log "执行: $($scpCmd.Source) $($scpArgs -join ' ')"

        $errorOutput = ""
        try {
            & $scpCmd.Source @scpArgs 2>&1 | Tee-Object -Variable output | Out-Null
            $exitCode = $LASTEXITCODE
        } catch {
            $errorOutput = $_.Exception.Message
            $exitCode = -1
        }

        if ($exitCode -ne 0) {
            Write-Log "SCP 退出码: $exitCode"
            if ($output) {
                Write-Log "输出: $($output -join [Environment]::NewLine)"
            }
            Write-Log "错误: $errorOutput"
            throw "SCP 下载失败，退出码: $exitCode"
        }

        Write-Log '压缩文件下载完成'

        Write-Log '解压文件...'
        $compressedFile = Join-Path $tempPath "${latestBackupName}.tar.gz"

        # 使用 tar 命令解压
        $tarCmd = Get-Command tar -ErrorAction SilentlyContinue
        if ($tarCmd) {
            Write-Log "使用 tar 解压: $($tarCmd.Source)"
            & tar -xzf $compressedFile -C $tempPath
            if ($LASTEXITCODE -ne 0) {
                throw "tar 解压失败，退出码: $LASTEXITCODE"
            }
        } else {
            $sevenZip = "${env:ProgramFiles}\7-Zip\7z.exe"
            if (Test-Path $sevenZip) {
                Write-Log "使用 7-Zip 解压: $sevenZip"
                & $sevenZip x $compressedFile "-o$tempPath" -y | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "7-Zip 解压失败，退出码: $LASTEXITCODE"
                }
            } else {
                throw '找不到 tar 或 7-Zip 命令。请安装 Git for Windows（包含 tar）或 7-Zip。'
            }
        }

        Write-Log "删除本地旧备份并移动新文件到: $LocalPath"
        $targetDir = Join-Path $LocalPath $latestBackupName
        if (Test-Path $targetDir) {
            Write-Log "删除旧备份: $($latestBackupName)"
            Remove-Item -Path $targetDir -Recurse -Force
        }

        $downloadedDir = Join-Path $tempPath $latestBackupName
        if (-not (Test-Path $downloadedDir)) {
            throw "解压后的目录不存在: $downloadedDir"
        }
        Move-Item -Path $downloadedDir -Destination $LocalPath -Force
        Write-Log "已移动: $($latestBackupName)"
    }
    else {
        Write-Log "开始下载备份文件: $latestBackupName ..."
        $scpArgs = @(
            '-q'
            '-r'
            '-P', $SshPort
            '-o', 'StrictHostKeyChecking=no'
            '-o', 'UserKnownHostsFile=NUL'
            "${ServerUser}@${Server}:${latestBackup}"
            $tempPath
        )

        Write-Log "执行: $($scpCmd.Source) $($scpArgs -join ' ')"

        $errorOutput = ""
        try {
            & $scpCmd.Source @scpArgs 2>&1 | Tee-Object -Variable output | Out-Null
            $exitCode = $LASTEXITCODE
        } catch {
            $errorOutput = $_.Exception.Message
            $exitCode = -1
        }

        if ($exitCode -ne 0) {
            Write-Log "SCP 退出码: $exitCode"
            if ($output) {
                Write-Log "输出: $($output -join [Environment]::NewLine)"
            }
            Write-Log "错误: $errorOutput"
            throw "SCP 下载失败，退出码: $exitCode"
        }

        Write-Log '备份文件下载完成'

        Write-Log "检查下载的文件..."
        $downloadedItems = Get-ChildItem -Path $tempPath -Force
        Write-Log "临时目录内容: $($downloadedItems.Name -join ', ')"

        Write-Log "删除本地旧备份并移动新文件到: $LocalPath"
        $targetDir = Join-Path $LocalPath $latestBackupName
        if (Test-Path $targetDir) {
            Write-Log "删除旧备份: $($latestBackupName)"
            Remove-Item -Path $targetDir -Recurse -Force
        }

        $downloadedDir = Join-Path $tempPath $latestBackupName
        if (-not (Test-Path $downloadedDir)) {
            throw "下载的目录不存在: $downloadedDir"
        }
        Move-Item -Path $downloadedDir -Destination $LocalPath -Force
        Write-Log "已移动: $($latestBackupName)"
    }

    Write-Log '========== 备份下载完成 =========='
    Write-Log "备份类型: $backupType"
    Write-Log "备份已下载到: $targetDir"

    Write-Log '任务完成'
}
catch {
    Write-Log "错误: $($_.Exception.Message)"
    Write-Log '任务失败'
    exit 1
}
finally {
    if ($tempPath -and (Test-Path $tempPath)) {
        Remove-Item -Path $tempPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}
