param(
  [string]$BackendCommand = 'python -m unittest discover -s backend/tests -p "test_*.py"',
  [string]$FrontendBuildCommand = 'npm run build',
  [string]$FrontendCommand = 'npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/rbac.viewer.permissions-matrix.spec.js e2e/tests/rbac.uploader.permissions-matrix.spec.js e2e/tests/rbac.reviewer.permissions-matrix.spec.js e2e/tests/audit.logs.filters-combined.spec.js e2e/tests/document.version-history.spec.js e2e/tests/documents.review.approve.spec.js e2e/tests/review.notification.spec.js e2e/tests/review.signature.spec.js e2e/tests/document.watermark.spec.js e2e/tests/company.data-isolation.spec.js e2e/tests/admin.config-change-reason.spec.js e2e/tests/admin.data-security.backup.failure.spec.js e2e/tests/admin.data-security.backup.polling.spec.js e2e/tests/admin.data-security.settings.save.spec.js e2e/tests/admin.data-security.share.validation.spec.js e2e/tests/admin.data-security.validation.spec.js e2e/tests/data-security.advanced-panel.spec.js e2e/tests/admin.data-security.restore-drill.spec.js --workers=1',
  [string]$OutputFile = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$reportDir = Join-Path $repoRoot 'doc/test/reports'
if (-not (Test-Path $reportDir)) {
  New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}
if ([string]::IsNullOrWhiteSpace($OutputFile)) {
  $OutputFile = Join-Path $reportDir ("fullstack_test_report_{0}.md" -f $timestamp)
} elseif (-not [System.IO.Path]::IsPathRooted($OutputFile)) {
  $OutputFile = Join-Path $repoRoot $OutputFile
}

function Invoke-TestCommand {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][string]$WorkDir
  )

  if ([string]::IsNullOrWhiteSpace($Command)) {
    return @{
      name = $Name
      command = $Command
      workdir = $WorkDir
      exit_code = 0
      output = ''
      skipped = $true
    }
  }

  Write-Host ("[RUN] {0} -> {1}" -f $Name, $Command) -ForegroundColor Cyan
  $scriptPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ragflow_fullstack_{0}_{1}.ps1" -f (($Name -replace '[^a-zA-Z0-9]+', '_').ToLowerInvariant()), [guid]::NewGuid().ToString('N'))
  $scriptLines = @(
    '$ErrorActionPreference = ''Stop'''
    '$global:LASTEXITCODE = $null'
    $Command
    'if ($null -ne $global:LASTEXITCODE) { exit ([int]$global:LASTEXITCODE) }'
    'if ($?) { exit 0 }'
    'exit 1'
  )
  Set-Content -Path $scriptPath -Value $scriptLines -Encoding UTF8

  Push-Location $WorkDir
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $global:LASTEXITCODE = $null
    $ErrorActionPreference = 'Continue'
    $rawLines = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath 2>&1
    $cmdOk = $?
    if ($null -ne $global:LASTEXITCODE) {
      $exitCode = [int]$global:LASTEXITCODE
    } elseif ($cmdOk) {
      if ($null -ne $global:LASTEXITCODE) {
        $exitCode = [int]$global:LASTEXITCODE
      } else {
        $exitCode = 0
      }
    } else {
      if ($null -ne $global:LASTEXITCODE -and [int]$global:LASTEXITCODE -ne 0) {
        $exitCode = [int]$global:LASTEXITCODE
      } else {
        $exitCode = 1
      }
    }
  } catch {
    $rawLines = @($_.Exception.Message)
    $exitCode = 1
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Pop-Location
    Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
  }

  if ($null -eq $exitCode) { $exitCode = 0 }
  $output = Normalize-CommandOutput -Items $rawLines
  $statusColor = 'Red'
  if ($exitCode -eq 0) { $statusColor = 'Green' }
  Write-Host ("[DONE] {0} exit={1}" -f $Name, $exitCode) -ForegroundColor $statusColor

  return @{
    name = $Name
    command = $Command
    workdir = $WorkDir
    exit_code = [int]$exitCode
    output = $output
    skipped = $false
  }
}

function Get-LastRegexInt {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text,
    [Parameter(Mandatory = $true)][string]$Pattern
  )
  $m = [regex]::Matches($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if ($m.Count -eq 0) { return 0 }
  return [int]$m[$m.Count - 1].Groups[1].Value
}

function Parse-BackendSummary {
  param([Parameter(Mandatory = $true)][hashtable]$Result)
  $text = [string]$Result.output
  $ran = Get-LastRegexInt -Text $text -Pattern 'Ran\s+(\d+)\s+tests?'
  $failures = 0
  $errors = 0
  $skipped = 0

  $failedMatch = [regex]::Match($text, 'FAILED\s*\(([^)]*)\)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if ($failedMatch.Success) {
    $parts = $failedMatch.Groups[1].Value -split ','
    foreach ($p in $parts) {
      $kv = ($p -split '=')
      if ($kv.Count -ne 2) { continue }
      $key = $kv[0].Trim().ToLowerInvariant()
      $val = 0
      [void][int]::TryParse($kv[1].Trim(), [ref]$val)
      switch ($key) {
        'failures' { $failures = $val }
        'errors' { $errors = $val }
        'skipped' { $skipped = $val }
      }
    }
  } else {
    $skipped = Get-LastRegexInt -Text $text -Pattern 'skipped=(\d+)'
  }

  return @{
    ran = $ran
    passed = [Math]::Max(0, $ran - $failures - $errors - $skipped)
    failures = $failures
    errors = $errors
    skipped = $skipped
  }
}

function Parse-FrontendSummary {
  param([Parameter(Mandatory = $true)][hashtable]$Result)
  $text = [string]$Result.output
  $passed = Get-LastRegexInt -Text $text -Pattern '(\d+)\s+passed'
  $failed = Get-LastRegexInt -Text $text -Pattern '(\d+)\s+failed'
  $skipped = Get-LastRegexInt -Text $text -Pattern '(\d+)\s+skipped'
  $total = $passed + $failed + $skipped

  return @{
    total = $total
    passed = $passed
    failed = $failed
    skipped = $skipped
  }
}

function Normalize-CommandOutput {
  param([AllowNull()][object[]]$Items)
  if ($null -eq $Items) { return '' }

  $normalized = foreach ($item in $Items) {
    if ($null -eq $item) { continue }

    if ($item -is [System.Management.Automation.ErrorRecord]) {
      $message = [string]$item.Exception.Message
      if (-not [string]::IsNullOrWhiteSpace($message)) {
        $message.TrimEnd()
      }
      continue
    }

    [string]$item
  }

  return ($normalized | Out-String)
}

function Get-ResultStatus {
  param([Parameter(Mandatory = $true)][hashtable]$Result)
  if ($Result.skipped) { return 'SKIPPED' }
  if ($Result.exit_code -eq 0) { return 'PASS' }
  return 'FAIL'
}

function Get-BackendDetail {
  param(
    [Parameter(Mandatory = $true)][hashtable]$Result,
    [Parameter(Mandatory = $true)][hashtable]$Summary
  )
  if ($Result.skipped) { return 'skipped' }
  if ($Summary.ran -gt 0) {
    return '{0}/{1}' -f $Summary.passed, $Summary.ran
  }
  if ($Result.exit_code -eq 0) { return 'pass' }
  return 'fail'
}

function Get-FrontendDetail {
  param(
    [Parameter(Mandatory = $true)][hashtable]$Result,
    [Parameter(Mandatory = $true)][hashtable]$Summary
  )
  if ($Result.skipped) { return 'skipped' }
  if ($Summary.total -gt 0) {
    return '{0}/{1}' -f $Summary.passed, $Summary.total
  }
  if ($Result.exit_code -eq 0) { return 'pass' }
  return 'fail'
}

$backendResult = Invoke-TestCommand -Name 'Backend' -Command $BackendCommand -WorkDir $repoRoot
$frontendBuildResult = Invoke-TestCommand -Name 'Frontend Build' -Command $FrontendBuildCommand -WorkDir (Join-Path $repoRoot 'fronted')
$frontendResult = Invoke-TestCommand -Name 'Frontend Acceptance' -Command $FrontendCommand -WorkDir (Join-Path $repoRoot 'fronted')

$backendSummary = Parse-BackendSummary -Result $backendResult
$frontendBuildSummary = Parse-FrontendSummary -Result $frontendBuildResult
$frontendSummary = Parse-FrontendSummary -Result $frontendResult

$overallPass = (
  ($backendResult.skipped -or $backendResult.exit_code -eq 0) -and
  ($frontendBuildResult.skipped -or $frontendBuildResult.exit_code -eq 0) -and
  ($frontendResult.skipped -or $frontendResult.exit_code -eq 0)
)
$overallStatus = if ($overallPass) { 'PASS' } else { 'FAIL' }

$report = @()
$codeTick = [char]96
$report += "# Fullstack Test Report"
$report += ""
$report += "- Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$report += ("- Repository: {0}{1}{0}" -f $codeTick, $repoRoot)
$report += "- Overall: **$overallStatus**"
$report += ""
$report += "## Summary"
$report += ""
$report += "| Scope | Status | Exit Code | Detail |"
$report += "|---|---|---:|---|"
$report += ("| Backend | {0} | {1} | {2} |" -f (Get-ResultStatus -Result $backendResult), $backendResult.exit_code, (Get-BackendDetail -Result $backendResult -Summary $backendSummary))
$report += ("| Frontend Build | {0} | {1} | {2} |" -f (Get-ResultStatus -Result $frontendBuildResult), $frontendBuildResult.exit_code, (Get-FrontendDetail -Result $frontendBuildResult -Summary $frontendBuildSummary))
$report += ("| Frontend Acceptance | {0} | {1} | {2} |" -f (Get-ResultStatus -Result $frontendResult), $frontendResult.exit_code, (Get-FrontendDetail -Result $frontendResult -Summary $frontendSummary))
$report += ""
$report += "## Commands"
$report += ""
$report += ("- Backend: {0}{1}{0} (cwd: {0}{2}{0})" -f $codeTick, $backendResult.command, $backendResult.workdir)
$report += ("- Frontend Build: {0}{1}{0} (cwd: {0}{2}{0})" -f $codeTick, $frontendBuildResult.command, $frontendBuildResult.workdir)
$report += ("- Frontend Acceptance: {0}{1}{0} (cwd: {0}{2}{0})" -f $codeTick, $frontendResult.command, $frontendResult.workdir)
$report += ""
$report += "## Backend Raw Output"
$report += ""
$report += '```text'
$report += ($backendResult.output.TrimEnd())
$report += '```'
$report += ""
$report += "## Frontend Build Raw Output"
$report += ""
$report += '```text'
$report += ($frontendBuildResult.output.TrimEnd())
$report += '```'
$report += ""
$report += "## Frontend Acceptance Raw Output"
$report += ""
$report += '```text'
$report += ($frontendResult.output.TrimEnd())
$report += '```'
$report += ""

Set-Content -Path $OutputFile -Value $report -Encoding UTF8
$latest = Join-Path $reportDir 'fullstack_test_report_latest.md'
Copy-Item -Path $OutputFile -Destination $latest -Force

Write-Host ("REPORT: " + $OutputFile) -ForegroundColor Green
Write-Host ("REPORT: " + $latest) -ForegroundColor Green

if (-not $overallPass) { exit 1 }
exit 0
