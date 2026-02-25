param(
  [string]$BackendCommand = 'python -m unittest discover -s backend/tests -p "test_*.py"',
  [string]$FrontendCommand = 'npm run e2e:all',
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

  Write-Host ("[RUN] {0} -> {1}" -f $Name, $Command) -ForegroundColor Cyan
  Push-Location $WorkDir
  try {
    $global:LASTEXITCODE = 0
    $rawLines = & ([scriptblock]::Create($Command)) 2>&1
    $cmdOk = $?
    if ($cmdOk) {
      $exitCode = [int]$global:LASTEXITCODE
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
    Pop-Location
  }

  if ($null -eq $exitCode) { $exitCode = 0 }
  $output = if ($null -eq $rawLines) { '' } else { ($rawLines | Out-String) }
  $statusColor = 'Red'
  if ($exitCode -eq 0) { $statusColor = 'Green' }
  Write-Host ("[DONE] {0} exit={1}" -f $Name, $exitCode) -ForegroundColor $statusColor

  return @{
    name = $Name
    command = $Command
    workdir = $WorkDir
    exit_code = [int]$exitCode
    output = $output
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

$backendResult = Invoke-TestCommand -Name 'Backend' -Command $BackendCommand -WorkDir $repoRoot
$frontendResult = Invoke-TestCommand -Name 'Frontend' -Command $FrontendCommand -WorkDir (Join-Path $repoRoot 'fronted')

$backendSummary = Parse-BackendSummary -Result $backendResult
$frontendSummary = Parse-FrontendSummary -Result $frontendResult
$backendFailed = $backendSummary.failures + $backendSummary.errors

$overallPass = ($backendResult.exit_code -eq 0 -and $frontendResult.exit_code -eq 0)
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
$report += "| Scope | Exit Code | Total | Passed | Failed | Errors | Skipped |"
$report += "|---|---:|---:|---:|---:|---:|---:|"
$report += ("| Backend | {0} | {1} | {2} | {3} | {4} | {5} |" -f $backendResult.exit_code, $backendSummary.ran, $backendSummary.passed, $backendFailed, $backendSummary.errors, $backendSummary.skipped)
$report += ("| Frontend | {0} | {1} | {2} | {3} | 0 | {4} |" -f $frontendResult.exit_code, $frontendSummary.total, $frontendSummary.passed, $frontendSummary.failed, $frontendSummary.skipped)
$report += ""
$report += "## Commands"
$report += ""
$report += ("- Backend: {0}{1}{0} (cwd: {0}{2}{0})" -f $codeTick, $backendResult.command, $backendResult.workdir)
$report += ("- Frontend: {0}{1}{0} (cwd: {0}{2}{0})" -f $codeTick, $frontendResult.command, $frontendResult.workdir)
$report += ""
$report += "## Backend Raw Output"
$report += ""
$report += '```text'
$report += ($backendResult.output.TrimEnd())
$report += '```'
$report += ""
$report += "## Frontend Raw Output"
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
