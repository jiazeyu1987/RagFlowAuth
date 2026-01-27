#!/usr/bin/env pwsh
# Wrapper script for deploy.ps1 to avoid parameter passing issues

$ErrorActionPreference = "Stop"

# Change to repo root
Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

# Execute deploy.ps1 without any parameters
& "tool/scripts/deploy.ps1"
