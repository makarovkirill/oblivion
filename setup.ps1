$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Administrative privileges required. Please execute install.bat with Run as Administrator."
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $ScriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   OBLIVION — Dead Man's Switch & Secure Eraser           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] Verifying Python runtime..." -ForegroundColor Cyan
$PythonExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} else {
    Write-Error "Python 3 is not found in system PATH. Please install Python 3.11+ from https://www.python.org/"
    exit 1
}

$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[2/5] Initializing Python virtual environment..." -ForegroundColor Cyan
    & $PythonExe -m venv $VenvDir
}

Write-Host "[3/5] Verifying and updating dependencies..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt") --quiet

$StaticIndex = Join-Path $ScriptDir "oblivion\static\index.html"
if (-not (Test-Path $StaticIndex)) {
    Write-Host "Static assets missing in oblivion/static. Running web build..." -ForegroundColor Yellow
    $WebDir = Join-Path $ScriptDir "web"
    Push-Location $WebDir
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        npm install --quiet
        npm run build --quiet
    } else {
        Write-Warning "npm not available to compile web assets."
    }
    Pop-Location
}

Write-Host "[4/5] Registering Windows Scheduled Task (OblivionWatchdog, HIGHEST privileges)..." -ForegroundColor Cyan
$TaskName = "OblivionWatchdog"

& schtasks /delete /tn $TaskName /f 2>$null | Out-Null

$TaskAction = New-ScheduledTaskAction -Execute $VenvPythonW -Argument "-m oblivion.main --daemon" -WorkingDirectory $ScriptDir
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerLogon = New-ScheduledTaskTrigger -AtLogon
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit 0

try {
    Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger @($TriggerStartup, $TriggerLogon) -Principal $Principal -Settings $Settings -Force | Out-Null
    Write-Host "  -> Scheduled task registered as NT AUTHORITY\SYSTEM" -ForegroundColor Green
} catch {
    $UserPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger @($TriggerStartup, $TriggerLogon) -Principal $UserPrincipal -Settings $Settings -Force | Out-Null
    Write-Host "  -> Scheduled task registered under current elevated user" -ForegroundColor Green
}

Write-Host "[5/5] Launching background service..." -ForegroundColor Cyan
& schtasks /run /tn $TaskName 2>$null | Out-Null

$MaxRetries = 15
$Online = $false
for ($i = 0; $i -lt $MaxRetries; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/setup/status" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -eq 200) {
            $Online = $true
            break
        }
    } catch {
    }
}

if (-not $Online) {
    Start-Process -FilePath $VenvPythonW -ArgumentList "-m oblivion.main --daemon" -WorkingDirectory $ScriptDir
    Start-Sleep -Seconds 2
}

Start-Process "http://127.0.0.1:8765"
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   OBLIVION is running at http://127.0.0.1:8765           " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
