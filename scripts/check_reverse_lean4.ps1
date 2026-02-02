param(
  [Parameter(Mandatory = $true)]
  [string]$Path,
  [string]$ProjectDir,
  [switch]$RequireMathlib,
  [switch]$SkipLint,
  [int]$TimeoutSec = 120,
  [string]$LakePath,
  [string]$LeanPath,
  [string]$Python = "python",
  [string]$LintScript,
  [switch]$RequireStepMap
)

$ErrorActionPreference = "Stop"

function Find-Command([string]$Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd }

  # Prefer PATH, but fall back to elan shims for fresh installs (PATH may require a new shell).
  $elanBin = Join-Path $env:USERPROFILE ".elan\\bin"
  $p = Join-Path $elanBin ($Name + ".exe")
  if (Test-Path $p) { return Get-Command $p -ErrorAction SilentlyContinue }
  return $null
}

function Invoke-WithTimeout([string]$Exe, [string[]]$ArgList, [string]$WorkingDirectory, [int]$TimeoutSec) {
  function Quote-Arg([string]$a) {
    if ($null -eq $a) { return "" }
    if ($a -match '[\s"]') { return '"' + ($a -replace '"', '""') + '"' }
    return $a
  }

  $argString = ($ArgList | ForEach-Object { Quote-Arg $_ }) -join ' '

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $Exe
  $psi.Arguments = $argString
  $psi.WorkingDirectory = $WorkingDirectory
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi

  if (-not $p.Start()) {
    throw "Failed to start process: $Exe"
  }

  $ok = $p.WaitForExit($TimeoutSec * 1000)
  if (-not $ok) {
    try { $p.Kill() } catch {}
    throw "Lean4 gate timed out after ${TimeoutSec}s."
  }
  # Read captured output after the process exits.
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $exitCode = $p.ExitCode
  if ($exitCode -ne 0) {
    throw ("Gate failed (exit={0}).\nSTDERR:\n{1}\nSTDOUT:\n{2}" -f $exitCode, $stderr, $stdout)
  }
  return @{ stdout = $stdout; stderr = $stderr; exit = $exitCode }
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$leanFile = (Resolve-Path $Path).Path
$leanDir = Split-Path -Parent $leanFile

if (-not $LintScript -or $LintScript.Trim() -eq "") {
  $LintScript = Join-Path $here "lint_reverse_lean4.py"
}

if (-not $SkipLint) {
  $py = if ($Python -and $Python.Trim() -ne "") { $Python } else { "python" }
  $lintArgs = @($LintScript, "--lean", $leanFile)
  if ($RequireMathlib) { $lintArgs += "--require-mathlib" }
  if ($RequireStepMap) { $lintArgs += "--require-step-map" }
  Invoke-WithTimeout -Exe $py -ArgList $lintArgs -WorkingDirectory $here -TimeoutSec $TimeoutSec | Out-Null
}

if ($RequireMathlib) {
  $project = if ($ProjectDir -and $ProjectDir.Trim() -ne "") { (Resolve-Path $ProjectDir).Path } else { $leanDir }
  $hasLakeProject = (Test-Path (Join-Path $project "lakefile.lean")) -or (Test-Path (Join-Path $project "lakefile.toml"))
  if (-not $hasLakeProject) {
    throw "Strict mode requires a Lake+Mathlib project dir: $project (missing lakefile.lean/toml)."
  }

  $lake = if ($LakePath -and $LakePath.Trim() -ne "") { Get-Command (Resolve-Path $LakePath).Path -ErrorAction SilentlyContinue } else { Find-Command "lake" }
  if (-not $lake) {
    throw "Strict mode requires 'lake'. Install Lean4 toolchain (elan recommended) and ensure lake is on PATH."
  }

  $r = Invoke-WithTimeout -Exe $lake.Source -ArgList @("env", "lean", $leanFile) -WorkingDirectory $project -TimeoutSec $TimeoutSec
  Write-Output (ConvertTo-Json @{ status = "passed"; mode = "lake_env_lean"; project = $project; path = $leanFile } -Depth 5)
  exit 0
}

$lean = if ($LeanPath -and $LeanPath.Trim() -ne "") { Get-Command (Resolve-Path $LeanPath).Path -ErrorAction SilentlyContinue } else { Find-Command "lean" }
if (-not $lean) {
  throw "Required command not found: lean. Install Lean4 (elan recommended) and ensure 'lean' is on PATH."
}

Invoke-WithTimeout -Exe $lean.Source -ArgList @($leanFile) -WorkingDirectory $leanDir -TimeoutSec $TimeoutSec | Out-Null
Write-Output (ConvertTo-Json @{ status = "passed"; mode = "lean"; path = $leanFile } -Depth 5)
exit 0
