# © 2026 Miguel Ángel Martínez. Todos los derechos reservados.
# Publica una versión nueva de StudySmart:
#   1. Escribe sus novedades y correcciones en CHANGELOG.md bajo "## [1.1.0] - AAAA-MM-DD".
#   2. Ejecuta:  .\publicar.ps1 1.1.0
# El script actualiza src\version.py, hace commit, crea la etiqueta v1.1.0 y la sube a GitHub.
# GitHub Actions construye el instalador y crea la release; los usuarios la verán al buscar actualizaciones.
param([Parameter(Mandatory = $true)][string]$Version)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Usa el formato 1.2.3 (sin la v)." }
if (git tag --list "v$Version") { throw "La versión $Version ya existe." }
if (-not (Select-String -Path CHANGELOG.md -Pattern "^## \[$([regex]::Escape($Version))\]" -Quiet)) {
    throw "Primero agrega en CHANGELOG.md la sección '## [$Version] - fecha' con sus novedades y correcciones."
}

$py = Get-Content src\version.py -Raw -Encoding UTF8
[IO.File]::WriteAllText("$PWD\src\version.py", ($py -replace '__version__ = "[^"]*"', "__version__ = `"$Version`""))

git add -A
git commit -m "Versión $Version"
git tag -a "v$Version" -m "StudySmart $Version"
git push origin HEAD
git push origin "v$Version"
Write-Host "Listo. Sigue la construcción en https://github.com/OpTicXit/StudySmart/actions"
