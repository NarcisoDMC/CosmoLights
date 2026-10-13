# build.ps1 - Compila CosmoLights: frontend React -> .exe (PyInstaller) -> instalador (Inno Setup)
# Uso:  powershell -ExecutionPolicy Bypass -File build.ps1 [-SkipFrontend] [-SkipInstaller]
param(
    [switch]$SkipFrontend,
    [switch]$SkipInstaller
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "No se encontró $py. Crea el entorno virtual e instala requirements.txt" }

# Asegura que ninguna instancia de CosmoLights.exe bloquee la carpeta dist
Get-Process CosmoLights -ErrorAction SilentlyContinue | Stop-Process -Force

if (-not $SkipFrontend) {
    Write-Host "==> [1/3] Compilando frontend (npm run build)..." -ForegroundColor Cyan
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build falló" }
}

Write-Host "==> [2/3] Empaquetando con PyInstaller..." -ForegroundColor Cyan
& $py -m PyInstaller CosmoLights.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }
Write-Host "    OK -> dist\CosmoLights\CosmoLights.exe" -ForegroundColor Green

if (-not $SkipInstaller) {
    $iscc = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source,
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

    if (-not $iscc) {
        Write-Warning "Inno Setup 6 no está instalado. Instálalo con: winget install JRSoftware.InnoSetup"
        Write-Warning "Se omitió la creación del instalador."
        exit 0
    }
    Write-Host "==> [3/3] Creando instalador con Inno Setup..." -ForegroundColor Cyan
    & $iscc "packaging\installer.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
    Write-Host "    OK -> installer\" -ForegroundColor Green
}
