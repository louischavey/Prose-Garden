[CmdletBinding()]
param(
    [string]$Port = 'auto',
    [switch]$Remap,
    [switch]$MouseOnly,
    [string]$Load,
    [switch]$ShowSaveButtons,
    [switch]$InstallDependencies,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv\Scripts\python.exe'

Push-Location -LiteralPath $projectDirectory
try {
    if (-not (Test-Path -LiteralPath $pythonExecutable)) {
        throw 'Project virtual environment missing. Run: py -3.12 -m venv .venv'
    }

    if ($InstallDependencies) {
        $oldTemp = $env:TEMP
        $oldTmp = $env:TMP
        $oldPipCache = $env:PIP_CACHE_DIR
        try {
            $env:TEMP = Join-Path $projectDirectory '.tmp'
            $env:TMP = $env:TEMP
            $env:PIP_CACHE_DIR = Join-Path $projectDirectory '.pip-cache'
            New-Item -ItemType Directory -Force -Path $env:TEMP, $env:PIP_CACHE_DIR | Out-Null
            & $pythonExecutable -m pip install -r requirements-garden.txt
            if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
        }
        finally {
            $env:TEMP = $oldTemp
            $env:TMP = $oldTmp
            $env:PIP_CACHE_DIR = $oldPipCache
        }
    }

    Write-Host 'Checking Python dependencies...'
    $dependencyCheck = 'import pygame, edge_tts, sounddevice, speech_recognition'
    if (-not $MouseOnly) { $dependencyCheck += '; import serial' }
    & $pythonExecutable -c $dependencyCheck
    if ($LASTEXITCODE -ne 0) {
        throw 'Dependencies are missing. Run this launcher again with -InstallDependencies.'
    }

    if ($MouseOnly) {
        $gardenArguments = @('garden.py', '--mouse-only')
        Write-Host 'Mouse mode: no Metro connection or probe mapping. Click grass to plant; click a plant to water.'
    }
    else {
    Write-Host 'Available serial ports:'
    & $pythonExecutable -m serial.tools.list_ports
    if ($LASTEXITCODE -ne 0) { throw 'Could not list serial ports.' }

    $portCode = @'
import sys
from serial.tools import list_ports
from dirt_input import resolve_port
try:
    print(resolve_port(sys.argv[1], list_ports.comports()))
except ValueError as exc:
    sys.exit(str(exc))
'@
    $resolvedPort = & $pythonExecutable -c $portCode $Port
    if ($LASTEXITCODE -ne 0) { throw 'No unique Metro port found. Use -Port COM6 (or the correct listed port).' }
    $resolvedPort = "$resolvedPort".Trim()

    $gardenArguments = @('garden.py', '--serial-port', $resolvedPort)
    if ($Remap) { $gardenArguments += '--map-probes' }

    Write-Host "Metro port: $resolvedPort"
    Write-Host 'Upload arduino\poetree_24\poetree_24.ino first; close Arduino Serial Monitor/Plotter.'
    Write-Host 'Only garden.py runs. It imports dirt_input.py and plant_poem.py automatically.'
    if ($Remap -or -not (Test-Path -LiteralPath 'output\probe-map.json')) {
        Write-Host 'Location mapping will run first. Touch each highlighted location, lift, then click Use mapping.'
    }
    else {
        Write-Host 'Using the saved probe map. Use -Remap only if you need to redo it.'
    }
    }
    if (-not $ShowSaveButtons) { $gardenArguments += '--gallery-mode' }
    if ($Load) { $gardenArguments += @('--load', $Load) }

    if ($CheckOnly) {
        Write-Host 'Checks passed. The serial port was not opened and the garden was not launched.'
        return
    }

    & $pythonExecutable @gardenArguments
    if ($LASTEXITCODE -ne 0) { throw "Garden exited with code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
