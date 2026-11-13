$ErrorActionPreference = 'Stop'

function Test-PythonExecutable {
    param([string]$Candidate)

    if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate)) {
        return $false
    }

    try {
        & $Candidate -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-UserPython {
    foreach ($CommandName in @('python', 'py')) {
        $command = Get-Command $CommandName -ErrorAction SilentlyContinue
        if ($command -and (Test-PythonExecutable $command.Source)) {
            return $command.Source
        }
    }

    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        $candidate = (& $uv.Source python find 3.12 2>$null | Select-Object -First 1).Trim()
        if ($LASTEXITCODE -eq 0 -and (Test-PythonExecutable $candidate)) {
            return $candidate
        }
    }

    throw 'Python 3.10+ was not found for this user. Install Python for your user or install uv with a managed Python, then run install.ps1 again.'
}

$sourceRoot = Split-Path -Parent $PSCommandPath
$installRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.local\TwitterVideo'
$venvRoot = Join-Path $installRoot 'venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
$binRoot = Join-Path $installRoot 'bin'
$shimPath = Join-Path $binRoot 'twitter-video.cmd'
$python = Find-UserPython

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
$tempRoot = Join-Path $installRoot 'tmp'
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$env:TMP = $tempRoot
$env:TEMP = $tempRoot
$env:PIP_CACHE_DIR = Join-Path $tempRoot 'pip-cache'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create the user-local Python environment.'
    }
}

& $venvPython -m pip install --upgrade --force-reinstall $sourceRoot
if ($LASTEXITCODE -ne 0) {
    throw 'Could not install Twitter Video and its dependencies.'
}

New-Item -ItemType Directory -Path $binRoot -Force | Out-Null
$entryPoint = Join-Path $venvRoot 'Scripts\twitter-video.exe'
"@echo off`r`n`"$entryPoint`" %*`r`n" | Set-Content -LiteralPath $shimPath -Encoding ascii

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = @($userPath -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (($entries | Where-Object { $_ -ieq $binRoot }).Count -eq 0) {
    $newPath = (@($entries) + $binRoot) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning 'ffmpeg was not found on PATH. Install it before downloading the best combined video/audio quality.'
}

Write-Host "Installed for the current user. Open a new PowerShell and run: twitter-video --version"
