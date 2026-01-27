#!/usr/bin/env pwsh
# Test script to identify parameter issue

Write-Host "Testing parameter declarations..." -ForegroundColor Cyan

try {
    # Test 1: Simple script block with switch parameters
    Write-Host "`nTest 1: Defining script with switch parameters..." -ForegroundColor Yellow

    $scriptBlock = {
        param(
            [switch]$SkipBuild,
            [switch]$SkipTransfer
        )
        Write-Host "Switch parameters defined successfully"
        Write-Host "SkipBuild: $SkipBuild"
        Write-Host "SkipTransfer: $SkipTransfer"
    }

    & $scriptBlock
    Write-Host "Test 1: PASSED" -ForegroundColor Green
} catch {
    Write-Host "Test 1: FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

try {
    # Test 2: Calling deploy.ps1 with no parameters
    Write-Host "`nTest 2: Calling deploy.ps1 with no parameters..." -ForegroundColor Yellow

    Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

    # Try to source/deploy.ps1 to check parameter definitions
    $null = Get-Command "tool/scripts/deploy.ps1" -Syntax
    Write-Host "Test 2: PASSED" -ForegroundColor Green
} catch {
    Write-Host "Test 2: FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`nTests completed" -ForegroundColor Cyan
