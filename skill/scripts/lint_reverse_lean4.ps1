param(
  [Parameter(Mandatory = $true)]
  [string]$LeanPath,

  [string]$MarkdownPath,

  [int]$MinSteps = 6,

  # Enforce a textual mapping block so steps are traceable, not just compilable.
  [switch]$RequireStepMap,

  # Strict semantic mode: require Lake project + Mathlib; forbid local semantic stubs.
  [switch]$RequireMathlib
)

[Console]::InputEncoding  = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
chcp 65001 > $null

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$lint = Join-Path $here "lint_reverse_lean4.py"

if (-not (Test-Path $lint)) { throw "Lean lint script not found: $lint" }

function Require-Command([string]$Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "Required command not found: $Name" }
}

Require-Command "python"

$LeanPath = [IO.Path]::GetFullPath($LeanPath)
if (-not (Test-Path $LeanPath)) { throw "Lean file not found: $LeanPath" }

$args = @(
  $lint,
  "--lean", $LeanPath,
  "--min-steps", "$MinSteps"
)
if (-not [string]::IsNullOrWhiteSpace($MarkdownPath)) {
  $MarkdownPath = [IO.Path]::GetFullPath($MarkdownPath)
  $args += @("--markdown", $MarkdownPath)
}
if ($RequireStepMap) {
  $args += "--require-step-map"
}
if ($RequireMathlib) {
  $args += "--require-mathlib"
}

& python @args | Out-Host
exit $LASTEXITCODE
