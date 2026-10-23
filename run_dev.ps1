param(
    [ValidateSet('audit','base','parser','knn','all')]
    [string]$Stage = 'all',
    [string]$PythonExe = ''
)
$ErrorActionPreference = 'Stop'
if (-not $PythonExe) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) {
        $PythonExe = $bundledPython
    } else {
        $PythonExe = 'python'
    }
}
Push-Location $PSScriptRoot
try {
    & $PythonExe -u run_dev.py --stage $Stage
    if ($LASTEXITCODE -ne 0) { throw "Development run failed (exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}

