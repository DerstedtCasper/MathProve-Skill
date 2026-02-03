#!/usr/bin/env pwsh
# Wrapper: forward to standard skill location.

$Target = Join-Path $PSScriptRoot "..\\skill\\scripts\\check_reverse_lean4.ps1"
& $Target @args
exit $LASTEXITCODE

