import argparse
from contextlib import asynccontextmanager
import copy
import ctypes
import os
import subprocess
import sys
from typing import Optional
import webbrowser
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from uvicorn.config import LOGGING_CONFIG

class SafeStream:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path

    def write(self, data: str):
        if not data:
            return
        if self.log_path:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(data)
            except Exception:
                pass

    def flush(self):
        pass

    def isatty(self) -> bool:
        return False

if sys.stdout is None or not hasattr(sys.stdout, "isatty"):
    sys.stdout = SafeStream()

if sys.stderr is None or not hasattr(sys.stderr, "isatty"):
    sys.stderr = SafeStream()

_current_file = Path(__file__).resolve()
_app_root = _current_file.parent.parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

if __package__ is None or __package__ == "":
    from oblivion.config import settings
    from oblivion.storage.database import init_db, get_config_value
    from oblivion.engine.watchdog import watchdog
    from oblivion.integrations.telegram_bot import telegram_worker
    from oblivion.api.routes import api_router
else:
    from .config import settings
    from .storage.database import init_db, get_config_value
    from .engine.watchdog import watchdog
    from .integrations.telegram_bot import telegram_worker
    from .api.routes import api_router

_mutex_handle = None

def acquire_single_instance_mutex(mutex_name: str) -> bool:
    global _mutex_handle
    if os.name != "nt":
        return True
    try:
        ERROR_ALREADY_EXISTS = 183
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _mutex_handle = handle
        return True
    except Exception:
        return True

def register_scheduled_task(target_exe: Optional[str] = None) -> bool:
    if os.name != "nt":
        print("Scheduled tasks can only be registered on Windows.")
        return False
    
    exe_path = target_exe or sys.executable
    args = "--daemon"
    workdir = str(Path(exe_path).parent)
    
    unregister_scheduled_task()

    xml_template = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>OBLIVION Watchdog Background Service</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe_path}</Command>
      <Arguments>{args}</Arguments>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

    xml_path = Path(workdir) / "task_def.xml"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        xml_path.write_text(xml_template, encoding="utf-16")
        res = subprocess.run(["schtasks", "/create", "/tn", settings.task_name, "/xml", str(xml_path), "/f"], capture_output=True, text=True, creationflags=flags)
        if xml_path.exists():
            try:
                xml_path.unlink()
            except Exception:
                pass
        if res.returncode == 0:
            print(f"[OK] Task '{settings.task_name}' registered successfully (XML, Boot+Logon, Battery=ON).")
            return True
    except Exception:
        pass

    cmd_action = f'"{exe_path}" {args}'
    cmd = [
        "schtasks", "/create",
        "/tn", settings.task_name,
        "/tr", cmd_action,
        "/sc", "ONSTART",
        "/rl", "HIGHEST",
        "/f"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
        if res.returncode == 0:
            print(f"[OK] Task '{settings.task_name}' registered successfully (ONSTART, HIGHEST).")
            return True
        else:
            print(f"[ERROR] Failed to register task: {res.stderr.strip() or res.stdout.strip()}")
            return False
    except Exception as exc:
        print(f"[ERROR] Task creation failed: {exc}")
        return False

def unregister_scheduled_task() -> bool:
    if os.name != "nt":
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    try:
        subprocess.run(["schtasks", "/end", "/tn", settings.task_name], capture_output=True, creationflags=flags)
        res = subprocess.run(["schtasks", "/delete", "/tn", settings.task_name, "/f"], capture_output=True, text=True, creationflags=flags)
        if res.returncode == 0:
            print(f"[OK] Task '{settings.task_name}' deleted successfully.")
            return True
        return False
    except Exception:
        return False

def attach_parent_console():
    """If running under pythonw/noconsole, attach to the parent cmd/powershell process console."""
    if os.name != "nt":
        return
    try:
        ATTACH_PARENT_PROCESS = 0xFFFFFFFF
        if ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            import io
            sys.stdin = io.TextIOWrapper(open("CONIN$", "rb", buffering=0), encoding="utf-8", errors="replace")
            sys.stdout = io.TextIOWrapper(open("CONOUT$", "wb", buffering=0), encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(open("CONOUT$", "wb", buffering=0), encoding="utf-8", errors="replace")
    except Exception:
        pass

def perform_uninstallation(candidate_pin: Optional[str] = None) -> bool:
    attach_parent_console()
    import asyncio
    from oblivion.crypto.vault import verify_secret

    print("=" * 60)
    print("                 OBLIVION UNINSTALLATION")
    print("=" * 60)

    async def _check_pin():
        await init_db()
        setup_done = (await get_config_value("setup_completed", "0")) == "1"
        pin_hash = await get_config_value("uninstall_pin_hash")
        return setup_done, pin_hash

    try:
        setup_done, pin_hash = asyncio.run(_check_pin())
    except Exception:
        setup_done, pin_hash = False, None

    if setup_done and pin_hash:
        candidate = candidate_pin
        if not candidate:
            try:
                candidate = input("Enter Uninstall Key / Введите ключ удаления: ").strip()
            except Exception:
                candidate = ""

        if not verify_secret(pin_hash, candidate):
            print("\n[ERROR] Invalid uninstall key! Access denied.")
            print("[ОШИБКА] Неверный ключ удаления! Отказано в доступе.\n")
            return False
        print("\n[OK] Uninstall authorization verified.")
    else:
        print("[INFO] System not initialized or no PIN required.")

    print("[1/3] Stopping background service and task...")
    unregister_scheduled_task()
    try:
        current_pid = os.getpid()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -like '*oblivion*' -or $_.CommandLine -like '*oblivion.main*') -and $_.ProcessId -ne {current_pid} }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"],
            capture_output=True,
            creationflags=flags
        )
    except Exception:
        pass

    print("[2/3] Removing desktop shortcuts...")
    for desk in [
        Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
        Path.home() / "Desktop"
    ]:
        sc = desk / "OBLIVION.url"
        if sc.exists():
            try:
                sc.unlink()
            except Exception:
                pass

    print("[3/3] Service uninstalled successfully.")
    try:
        ans = input("\nPurge data directory (C:\\ProgramData\\OBLIVION)? [y/N]: ").strip().lower()
        if ans == "y":
            data_dir = settings.data_dir
            if data_dir.exists():
                import shutil
                shutil.rmtree(data_dir, ignore_errors=True)
                print(f"[OK] Purged {data_dir}")
    except Exception:
        pass

    print("\n[OK] OBLIVION has been removed.")
    return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    is_setup = (await get_config_value("setup_completed", "0")) == "1"
    if is_setup:
        await watchdog.start()
        await telegram_worker.start()
    yield
    await telegram_worker.stop()
    await watchdog.stop()

app = FastAPI(
    title="OBLIVION",
    description="Dead Man's Switch & Secure Eraser",
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

static_path = settings.static_dir
assets_dir = static_path / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    if full_path.startswith("api/"):
        return HTMLResponse(status_code=404, content="API endpoint not found")

    target_file = static_path / full_path
    if target_file.is_file():
        return FileResponse(str(target_file))

    index_html = static_path / "index.html"
    if index_html.is_file():
        return FileResponse(str(index_html))

    return HTMLResponse(
        content=(
            "<!doctype html><html><head><title>OBLIVION</title></head>"
            "<body style='background:#0B0F17;color:#F3F4F6;font-family:sans-serif;padding:40px;text-align:center'>"
            "<h2>OBLIVION Engine Active</h2>"
            "<p>UI bundle is loading or rebuilding...</p></body></html>"
        ),
        status_code=200
    )

def main():
    parser = argparse.ArgumentParser(description="OBLIVION — Dead Man's Switch & Secure Eraser")
    parser.add_argument("--daemon", action="store_true", help="Run headless service in background")
    parser.add_argument("--register", action="store_true", help="Register Windows Scheduled Task with highest privileges")
    parser.add_argument("--unregister", action="store_true", help="Unregister and remove Windows Scheduled Task")
    parser.add_argument("--uninstall", nargs="?", const="", default=None, help="Authorize with uninstall key and remove service")
    parser.add_argument("--host", default=settings.host, help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=settings.port, help="Bind port (default: 8765)")
    args = parser.parse_args()

    if args.uninstall is not None:
        pin = args.uninstall.strip() if isinstance(args.uninstall, str) and args.uninstall.strip() else None
        success = perform_uninstallation(pin)
        sys.exit(0 if success else 1)

    if args.register:
        success = register_scheduled_task()
        sys.exit(0 if success else 1)

    if args.unregister:
        success = unregister_scheduled_task()
        sys.exit(0 if success else 1)

    has_mutex = acquire_single_instance_mutex(settings.mutex_name)
    if not has_mutex:
        if not args.daemon:
            webbrowser.open(f"http://{args.host}:{args.port}")
        print(f"OBLIVION is already running on http://{args.host}:{args.port}")
        sys.exit(0)

    if not args.daemon:
        try:
            webbrowser.open(f"http://{args.host}:{args.port}")
        except Exception:
            pass

    log_config = copy.deepcopy(LOGGING_CONFIG)
    if "formatters" in log_config:
        if "default" in log_config["formatters"]:
            log_config["formatters"]["default"]["use_colors"] = False
        if "access" in log_config["formatters"]:
            log_config["formatters"]["access"]["use_colors"] = False

    if args.daemon or sys.stdout is None or isinstance(sys.stdout, SafeStream):
        service_log = settings.logs_dir / "service.log"
        sys.stdout = SafeStream(service_log)
        sys.stderr = SafeStream(service_log)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
        use_colors=False,
        log_config=log_config
    )

if __name__ == "__main__":
    main()
