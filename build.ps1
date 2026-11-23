# © 2026 Miguel Ángel Martínez. Todos los derechos reservados.
# Construye dist\StudySmart\StudySmart.exe (PyInstaller) y el instalador dist\StudySmart-Setup-<versión>.exe (Inno Setup).
#   .\build.ps1                      # con el entorno .venv del proyecto
#   .\build.ps1 -Python python       # con el Python activo (lo usa GitHub Actions)
param([string]$Python = ".venv\Scripts\python.exe")
$ErrorActionPreference = "Continue"  # PyInstaller escribe su progreso en stderr; los fallos se revisan con $LASTEXITCODE
Set-Location $PSScriptRoot

$version = (& $Python src\version.py).Trim()
$tupla = "(" + (($version -split '\.') + '0' -join ', ') + ")"
Write-Host "Construyendo StudySmart $version"

New-Item -ItemType Directory -Force build | Out-Null
$info = (Get-Content installer\version_info.txt -Raw -Encoding UTF8).Replace('{TUPLA}', $tupla).Replace('{VERSION}', $version)
[IO.File]::WriteAllText("$PWD\build\version_info.txt", $info)   # sin BOM: PyInstaller lo evalúa como Python
[IO.File]::WriteAllText("$PWD\build\LICENSE.txt", (Get-Content LICENSE -Raw -Encoding UTF8), [Text.UTF8Encoding]::new($true))  # con BOM para Inno Setup

& $Python -m PyInstaller --noconfirm --clean --windowed --name StudySmart `
    --icon installer\studysmart.ico --version-file build\version_info.txt `
    --add-data "app.py;." --add-data "src\*.py;src" --add-data "models;models" `
    --add-data "data\plan_estudios.csv;data" --add-data "data\processed\registros_limpios.csv;data\processed" `
    --add-data ".streamlit\config.toml;.streamlit" --add-data "CHANGELOG.md;." --add-data "LICENSE;." `
    --add-data "installer\studysmart.ico;installer" `
    --collect-all streamlit --collect-submodules sklearn `
    --exclude-module matplotlib --exclude-module seaborn --exclude-module IPython --exclude-module notebook `
    --exclude-module jupyter_client --exclude-module tkinter --exclude-module imblearn `
    lanzador.py
if ($LASTEXITCODE) { throw "PyInstaller falló" }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "No se encontró Inno Setup 6 (winget install JRSoftware.InnoSetup)" }
& $iscc /Q "/DAppVersion=$version" installer\StudySmart.iss
if ($LASTEXITCODE) { throw "Inno Setup falló" }
Write-Host "Listo: dist\StudySmart-Setup-$version.exe"
