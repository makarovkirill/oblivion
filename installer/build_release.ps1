$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
Set-Location -Path $RootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   OBLIVION - Automated Release and Packaging Pipeline    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Frontend compilation
Write-Host "[1/5] Compiling Web UI bundle (React 18 + Vite)..." -ForegroundColor Yellow
$WebDir = Join-Path $RootDir "web"
$StaticIndex = Join-Path $RootDir "oblivion\static\index.html"

if (Test-Path (Join-Path $WebDir "package.json")) {
    Push-Location $WebDir
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        npm run build
    } else {
        Write-Error "npm is required to build the web UI."
        exit 1
    }
    Pop-Location
}

if (-not (Test-Path $StaticIndex)) {
    Write-Error "Web bundle build failed: $StaticIndex not found."
    exit 1
}
Write-Host "  -> Static assets compiled to oblivion/static" -ForegroundColor Green

# 2. Locate Python runtime
Write-Host "[2/5] Verifying Python build environment..." -ForegroundColor Yellow
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$DistDir = Join-Path $RootDir "dist"
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir | Out-Null
}

$BuildDir = Join-Path $RootDir "build"
if (-not (Test-Path $BuildDir)) {
    New-Item -ItemType Directory -Path $BuildDir | Out-Null
}

$AppIcon = Join-Path $RootDir "installer\app.ico"
$AppPng = Join-Path $RootDir "installer\app.png"
$AppLogo = Join-Path $RootDir "installer\logo36.png"

# 3. Compile standalone background service binary (oblivion.exe)
Write-Host "[3/5] Building standalone engine binary (dist/oblivion.exe)..." -ForegroundColor Yellow
$OblivionMain = Join-Path $RootDir "oblivion\main.py"
$OblivionStatic = Join-Path $RootDir "oblivion\static"

& $PythonExe -m PyInstaller `
    --noconfirm `
    --onefile `
    --noconsole `
    --icon "$AppIcon" `
    --name "oblivion" `
    --distpath $DistDir `
    --workpath (Join-Path $BuildDir "oblivion") `
    --specpath (Join-Path $BuildDir "oblivion") `
    --add-data "${OblivionStatic};oblivion/static" `
    --hidden-import "fastapi" `
    --hidden-import "uvicorn" `
    --hidden-import "uvicorn.logging" `
    --hidden-import "uvicorn.loops" `
    --hidden-import "uvicorn.loops.auto" `
    --hidden-import "uvicorn.protocols" `
    --hidden-import "uvicorn.protocols.http" `
    --hidden-import "uvicorn.protocols.http.auto" `
    --hidden-import "uvicorn.protocols.websockets" `
    --hidden-import "uvicorn.protocols.websockets.auto" `
    --hidden-import "uvicorn.lifespans" `
    --hidden-import "uvicorn.lifespans.on" `
    --hidden-import "aiosqlite" `
    --hidden-import "cryptography" `
    --hidden-import "argon2" `
    --hidden-import "apscheduler" `
    --hidden-import "apscheduler.schedulers.asyncio" `
    --hidden-import "aiogram" `
    --hidden-import "pydantic" `
    --hidden-import "python_multipart" `
    --hidden-import "aiofiles" `
    --hidden-import "httpx" `
    $OblivionMain

$OblivionExe = Join-Path $DistDir "oblivion.exe"
if (-not (Test-Path $OblivionExe)) {
    Write-Error "Failed to build dist/oblivion.exe"
    exit 1
}
$EngineSizeMB = [math]::Round((Get-Item $OblivionExe).Length / 1MB, 2)
Write-Host "  -> Core engine binary built: dist/oblivion.exe ($($EngineSizeMB) MB)" -ForegroundColor Green

# 4. Compile native GUI installer (OblivionSetup.exe)
Write-Host "[4/5] Building standalone GUI installer (dist/OblivionSetup.exe)..." -ForegroundColor Yellow
$SetupScript = Join-Path $RootDir "installer\setup_wizard.py"
$OblivionData = Join-Path $RootDir "oblivion"

& $PythonExe -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --uac-admin `
    --icon "$AppIcon" `
    --name "OblivionSetup" `
    --distpath $DistDir `
    --workpath (Join-Path $BuildDir "installer") `
    --specpath (Join-Path $BuildDir "installer") `
    --add-data "${OblivionExe};." `
    --add-data "${OblivionData};oblivion" `
    --add-data "${AppIcon};installer" `
    --add-data "${AppPng};installer" `
    --add-data "${AppLogo};installer" `
    --hidden-import "tkinter" `
    $SetupScript

# 5. Verify release artifacts
Write-Host "[5/5] Verifying release artifacts..." -ForegroundColor Yellow
$InstallerExe = Join-Path $DistDir "OblivionSetup.exe"
if (Test-Path $InstallerExe) {
    $SizeMB = [math]::Round((Get-Item $InstallerExe).Length / 1MB, 2)
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "   BUILD SUCCESSFUL: dist/OblivionSetup.exe ($($SizeMB) MB) " -ForegroundColor Green
    Write-Host "   CORE ENGINE:      dist/oblivion.exe ($($EngineSizeMB) MB)" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "Build failed: OblivionSetup.exe was not created."
    exit 1
}
