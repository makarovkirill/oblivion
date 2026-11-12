import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import webbrowser

class SafeStream:
    def write(self, data: str):
        pass

    def flush(self):
        pass

    def isatty(self) -> bool:
        return False

if sys.stdout is None or not hasattr(sys.stdout, "isatty"):
    sys.stdout = SafeStream()

if sys.stderr is None or not hasattr(sys.stderr, "isatty"):
    sys.stderr = SafeStream()

APP_NAME = "OBLIVION"
APP_VERSION = "1.0.0"
APP_SUBTITLE_EN = "Dead Man's Switch & Secure Eraser"
APP_SUBTITLE_RU = "Dead Man's Switch и безопасное удаление"
DEFAULT_INSTALL_DIR = r"C:\Program Files\OBLIVION"
TASK_NAME = "OblivionWatchdog"

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_if_needed():
    if "--help" in sys.argv or "-h" in sys.argv:
        return
    if not is_admin() and os.name == "nt":
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

def set_dark_titlebar(hwnd: int):
    if os.name != "nt":
        return
    try:
        value = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass

class DarkProgressBar(tk.Canvas):
    def __init__(self, parent, height=8, bg="#1E293B", fill="#2563EB", **kwargs):
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.bar_color = fill
        self.bg_color = bg
        self._fraction = 0.0

    def set_progress(self, percent: float):
        self._fraction = max(0.0, min(100.0, float(percent))) / 100.0
        self.delete("bar")
        w = self.winfo_width()
        h = self.winfo_height()
        bar_w = int(w * self._fraction)
        if bar_w > 0:
            self.create_rectangle(0, 0, bar_w, h, fill=self.bar_color, width=0, tags="bar")
        self.update_idletasks()

class OblivionInstallerApp(tk.Tk):
    def __init__(self, silent: bool = False):
        super().__init__()
        self.silent = silent
        self.lang = "en"
        self.target_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR if is_admin() else str(Path.home() / "OBLIVION"))
        self.opt_task = tk.BooleanVar(value=True)
        self.opt_shortcut = tk.BooleanVar(value=True)
        self.opt_start = tk.BooleanVar(value=True)
        self.opt_browser = tk.BooleanVar(value=True)
        self._is_completed = False

        self._configure_window()
        self._load_icon()
        self._init_ui()

    def _configure_window(self):
        self.title("OBLIVION Setup")
        w, h = 540, 460
        self.resizable(False, False)
        self.configure(bg="#0F172A")

        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = max(0, (ws // 2) - (w // 2))
        y = max(0, (hs // 2) - (h // 2))
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.update_idletasks()
        if os.name == "nt":
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if hwnd:
                    set_dark_titlebar(hwnd)
            except Exception:
                pass

    def _get_resource_path(self, rel_path: str) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        candidate1 = base / rel_path
        if candidate1.exists():
            return candidate1
        candidate2 = Path(__file__).resolve().parent / rel_path
        if candidate2.exists():
            return candidate2
        candidate3 = base / Path(rel_path).name
        if candidate3.exists():
            return candidate3
        return candidate1

    def _load_icon(self):
        ico_file = self._get_resource_path("installer/app.ico")
        if ico_file.exists():
            try:
                self.iconbitmap(str(ico_file))
            except Exception:
                pass

        png_file = self._get_resource_path("installer/app.png")
        if png_file.exists():
            try:
                win_icon = tk.PhotoImage(file=str(png_file))
                self.iconphoto(True, win_icon)
            except Exception:
                pass

        logo_file = self._get_resource_path("installer/logo36.png")
        self.logo_img = None
        if logo_file.exists():
            try:
                self.logo_img = tk.PhotoImage(file=str(logo_file))
            except Exception:
                pass

    def _init_ui(self):
        # 1. Header
        header = tk.Frame(self, bg="#1E293B", height=70, padx=20, pady=12)
        header.pack(fill=tk.X)

        header_left = tk.Frame(header, bg="#1E293B")
        header_left.pack(side=tk.LEFT, fill=tk.Y)

        if getattr(self, "logo_img", None):
            logo_lbl = tk.Label(header_left, image=self.logo_img, bg="#1E293B")
            logo_lbl.pack(side=tk.LEFT, padx=(0, 12))

        title_frame = tk.Frame(header_left, bg="#1E293B")
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        title_row = tk.Frame(title_frame, bg="#1E293B")
        title_row.pack(anchor=tk.W)

        tk.Label(
            title_row,
            text=APP_NAME,
            font=("Segoe UI", 14, "bold"),
            fg="#F8FAFC",
            bg="#1E293B"
        ).pack(side=tk.LEFT)

        tk.Label(
            title_row,
            text=f"v{APP_VERSION}",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#1E293B"
        ).pack(side=tk.LEFT, padx=(6, 0), pady=(3, 0))

        self.subtitle_lbl = tk.Label(
            title_frame,
            text=APP_SUBTITLE_EN,
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#1E293B"
        )
        self.subtitle_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Language Selector (Segmented Button)
        lang_frame = tk.Frame(header, bg="#0F172A", padx=2, pady=2)
        lang_frame.pack(side=tk.RIGHT, pady=4)

        self.btn_lang_en = tk.Button(
            lang_frame,
            text="EN",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            bg="#2563EB",
            fg="#FFFFFF",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.set_language("en")
        )
        self.btn_lang_en.pack(side=tk.LEFT)

        self.btn_lang_ru = tk.Button(
            lang_frame,
            text="RU",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            bg="#0F172A",
            fg="#94A3B8",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.set_language("ru")
        )
        self.btn_lang_ru.pack(side=tk.LEFT)

        # 2. Body
        body = tk.Frame(self, bg="#0F172A", padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        self.dest_lbl = tk.Label(
            body,
            text="Destination Folder",
            font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0",
            bg="#0F172A"
        )
        self.dest_lbl.pack(anchor=tk.W, pady=(0, 4))

        dest_box = tk.Frame(body, bg="#1E293B", padx=2, pady=2, relief=tk.FLAT)
        dest_box.pack(fill=tk.X, pady=(0, 14))

        self.dest_entry = tk.Entry(
            dest_box,
            textvariable=self.target_dir,
            font=("Segoe UI", 9),
            bg="#1E293B",
            fg="#F8FAFC",
            insertbackground="#38BDF8",
            relief=tk.FLAT
        )
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, ipady=4)

        self.browse_btn = tk.Button(
            dest_box,
            text="Browse...",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#F8FAFC",
            activebackground="#475569",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self._browse_dir
        )
        self.browse_btn.pack(side=tk.RIGHT, padx=2)

        # Options Box
        self.options_title_lbl = tk.Label(
            body,
            text="Setup Options",
            font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0",
            bg="#0F172A"
        )
        self.options_title_lbl.pack(anchor=tk.W, pady=(0, 4))

        options_box = tk.Frame(body, bg="#1E293B", padx=12, pady=8)
        options_box.pack(fill=tk.X, pady=(0, 14))

        self.cb_task = tk.Checkbutton(
            options_box,
            text="Run at Windows startup (background watchdog)",
            variable=self.opt_task,
            bg="#1E293B",
            fg="#F1F5F9",
            selectcolor="#0F172A",
            activebackground="#1E293B",
            activeforeground="#38BDF8",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.cb_task.pack(anchor=tk.W, pady=2)

        self.cb_shortcut = tk.Checkbutton(
            options_box,
            text="Create desktop shortcut",
            variable=self.opt_shortcut,
            bg="#1E293B",
            fg="#F1F5F9",
            selectcolor="#0F172A",
            activebackground="#1E293B",
            activeforeground="#38BDF8",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.cb_shortcut.pack(anchor=tk.W, pady=2)

        self.cb_start = tk.Checkbutton(
            options_box,
            text="Start background service after installation",
            variable=self.opt_start,
            bg="#1E293B",
            fg="#F1F5F9",
            selectcolor="#0F172A",
            activebackground="#1E293B",
            activeforeground="#38BDF8",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.cb_start.pack(anchor=tk.W, pady=2)

        self.cb_browser = tk.Checkbutton(
            options_box,
            text="Open web dashboard in browser upon completion",
            variable=self.opt_browser,
            bg="#1E293B",
            fg="#F1F5F9",
            selectcolor="#0F172A",
            activebackground="#1E293B",
            activeforeground="#38BDF8",
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.cb_browser.pack(anchor=tk.W, pady=2)

        # Progress
        self.progress_bar = DarkProgressBar(body, height=6, bg="#1E293B", fill="#2563EB")
        self.progress_bar.pack(fill=tk.X, pady=(4, 6))

        self.status_lbl = tk.Label(
            body,
            text="Ready to install.",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0F172A"
        )
        self.status_lbl.pack(anchor=tk.W)

        # 3. Footer
        separator = tk.Frame(self, bg="#1E293B", height=1)
        separator.pack(fill=tk.X, side=tk.BOTTOM)

        footer = tk.Frame(self, bg="#0F172A", height=50, padx=24, pady=10)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.exit_btn = tk.Button(
            footer,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#1E293B",
            fg="#E2E8F0",
            activebackground="#334155",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=16,
            pady=5,
            cursor="hand2",
            command=self.destroy
        )
        self.exit_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self.install_btn = tk.Button(
            footer,
            text="Install",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=20,
            pady=5,
            cursor="hand2",
            command=self.perform_installation
        )
        self.install_btn.pack(side=tk.RIGHT)

    def set_language(self, lang: str):
        self.lang = lang
        if lang == "ru":
            self.btn_lang_ru.config(bg="#2563EB", fg="#FFFFFF")
            self.btn_lang_en.config(bg="#0F172A", fg="#94A3B8")
            self.title("Установка OBLIVION")
            self.subtitle_lbl.config(text=APP_SUBTITLE_RU)
            self.dest_lbl.config(text="Папка установки")
            self.browse_btn.config(text="Обзор...")
            self.options_title_lbl.config(text="Параметры")
            self.cb_task.config(text="Запускать при старте Windows (фоновый сторож)")
            self.cb_shortcut.config(text="Создать ярлык на рабочем столе")
            self.cb_start.config(text="Запустить службу после установки")
            self.cb_browser.config(text="Открыть панель управления в браузере")
            if not self._is_completed:
                self.status_lbl.config(text="Готов к установке.")
                self.install_btn.config(text="Установить")
                self.exit_btn.config(text="Отмена")
            else:
                self.status_lbl.config(text="Установка успешно завершена.")
                self.install_btn.config(text="Открыть панель")
                self.exit_btn.config(text="Закрыть")
        else:
            self.btn_lang_en.config(bg="#2563EB", fg="#FFFFFF")
            self.btn_lang_ru.config(bg="#0F172A", fg="#94A3B8")
            self.title("OBLIVION Setup")
            self.subtitle_lbl.config(text=APP_SUBTITLE_EN)
            self.dest_lbl.config(text="Destination Folder")
            self.browse_btn.config(text="Browse...")
            self.options_title_lbl.config(text="Setup Options")
            self.cb_task.config(text="Run at Windows startup (background watchdog)")
            self.cb_shortcut.config(text="Create desktop shortcut")
            self.cb_start.config(text="Start background service after installation")
            self.cb_browser.config(text="Open web dashboard in browser upon completion")
            if not self._is_completed:
                self.status_lbl.config(text="Ready to install.")
                self.install_btn.config(text="Install")
                self.exit_btn.config(text="Cancel")
            else:
                self.status_lbl.config(text="Installation completed successfully.")
                self.install_btn.config(text="Open Dashboard")
                self.exit_btn.config(text="Close")

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.target_dir.get())
        if chosen:
            self.target_dir.set(chosen)

    def perform_installation(self):
        if self._is_completed:
            if self.opt_browser.get():
                try:
                    webbrowser.open("http://127.0.0.1:8765")
                except Exception:
                    pass
            self.destroy()
            return

        self.install_btn.config(state=tk.DISABLED)
        self.exit_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.dest_entry.config(state=tk.DISABLED)

        msg_prep = "Подготовка к установке..." if self.lang == "ru" else "Preparing installation..."
        self.status_lbl.config(text=msg_prep, fg="#38BDF8")
        self.progress_bar.set_progress(10)
        self.update()

        target = Path(self.target_dir.get()).resolve()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to create directory:\n{exc}")
            self.install_btn.config(state=tk.NORMAL)
            self.exit_btn.config(state=tk.NORMAL)
            self.browse_btn.config(state=tk.NORMAL)
            self.dest_entry.config(state=tk.NORMAL)
            return

        source_dir = Path(__file__).resolve().parent.parent
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            source_dir = Path(sys._MEIPASS)

        msg_copy = "Копирование файлов..." if self.lang == "ru" else "Extracting application files..."
        self.status_lbl.config(text=msg_copy)
        self.progress_bar.set_progress(35)
        self.update()

        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
            subprocess.run(["schtasks", "/end", "/tn", TASK_NAME], capture_output=True, creationflags=flags)
            subprocess.run(["taskkill", "/f", "/im", "oblivion.exe"], capture_output=True, creationflags=flags)
        except Exception:
            pass

        try:
            main_exe_candidates = [
                source_dir / "oblivion.exe",
                source_dir / "dist" / "oblivion.exe",
                Path(sys.executable).parent / "oblivion.exe"
            ]
            for cand in main_exe_candidates:
                if cand.exists():
                    shutil.copy2(cand, target / "oblivion.exe")
                    break

            oblivion_src = source_dir / "oblivion"
            if oblivion_src.exists():
                oblivion_dest = target / "oblivion"
                if oblivion_dest.exists():
                    shutil.rmtree(oblivion_dest, ignore_errors=True)
                shutil.copytree(oblivion_src, oblivion_dest)

            for item in source_dir.glob("*.py"):
                shutil.copy2(item, target / item.name)
            for item in source_dir.glob("*.bat"):
                shutil.copy2(item, target / item.name)
            for item in source_dir.glob("*.md"):
                shutil.copy2(item, target / item.name)

            ico_src = self._get_resource_path("installer/app.ico")
            if not ico_src.exists():
                ico_src = self._get_resource_path("app.ico")
            if ico_src.exists():
                shutil.copy2(ico_src, target / "app.ico")

            uninstall_content = (
                "@echo off\r\n"
                "setlocal EnableDelayedExpansion\r\n"
                "net session >nul 2>&1\r\n"
                "if %errorlevel% neq 0 (\r\n"
                "    echo Requesting Administrator privileges...\r\n"
                "    powershell -NoProfile -ExecutionPolicy Bypass -Command \"Start-Process -FilePath '%~f0' -Verb RunAs\"\r\n"
                "    exit /b\r\n"
                ")\r\n"
                "cd /d \"%~dp0\"\r\n"
                "title OBLIVION Uninstaller\r\n"
                "echo ============================================================\r\n"
                "echo                  OBLIVION UNINSTALLATION\r\n"
                "echo ============================================================\r\n"
                "set /p USER_PIN=\"Enter Uninstall Key / Vvedite klyuch udaleniya: \"\r\n"
                "echo Verifying authorization key...\r\n"
                "powershell -NoProfile -ExecutionPolicy Bypass -Command \"& { $pin = '%USER_PIN%'.Trim(); $db = [System.IO.Path]::Combine($env:ProgramData, 'OBLIVION', 'oblivion.db'); if (-not (Test-Path $db)) { exit 0 }; if (Test-Path 'oblivion.exe') { $out = (& .\\oblivion.exe --uninstall $pin 2>&1 | Out-String); if ($LASTEXITCODE -eq 0 -or $out -like '*verified*') { exit 0 } else { exit 1 } } }\"\r\n"
                "if %errorlevel% neq 0 (\r\n"
                "    echo.\r\n"
                "    echo [ERROR] Invalid uninstall key! Access denied.\r\n"
                "    echo [OSHIBKA] Neverny klyuch udaleniya! Otkazano v dostupe.\r\n"
                "    echo.\r\n"
                "    pause\r\n"
                "    exit /b 1\r\n"
                ")\r\n"
                "echo.\r\n"
                "echo [OK] Uninstall authorization verified.\r\n"
                "echo [1/3] Stopping background service and task...\r\n"
                f"schtasks /end /tn {TASK_NAME} >nul 2>&1\r\n"
                f"schtasks /delete /tn {TASK_NAME} /f >nul 2>&1\r\n"
                "taskkill /f /im oblivion.exe >nul 2>&1\r\n"
                "echo [2/3] Removing shortcuts...\r\n"
                "del /f /q \"%PUBLIC%\\Desktop\\OBLIVION.url\" >nul 2>&1\r\n"
                "del /f /q \"%USERPROFILE%\\Desktop\\OBLIVION.url\" >nul 2>&1\r\n"
                "echo [3/3] Service uninstalled successfully.\r\n"
                "echo.\r\n"
                "set /p PURGE_DATA=\"Purge data directory (C:\\ProgramData\\OBLIVION)? [y/N]: \"\r\n"
                "if /i \"%PURGE_DATA%\"==\"y\" (\r\n"
                "    rd /s /q \"%ProgramData%\\OBLIVION\" >nul 2>&1\r\n"
                "    echo [OK] Purged data directory.\r\n"
                ")\r\n"
                "echo.\r\n"
                "echo [OK] OBLIVION has been removed.\r\n"
                "pause\r\n"
            )
            (target / "uninstall.bat").write_text(uninstall_content, encoding="utf-8")

        except Exception as exc:
            messagebox.showerror("Error", f"Installation error:\n{exc}")
            self.install_btn.config(state=tk.NORMAL)
            self.exit_btn.config(state=tk.NORMAL)
            return

        programdata_dir = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "OBLIVION"
        try:
            programdata_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Configure task
        if self.opt_task.get():
            msg_task = "Настройка автозапуска..." if self.lang == "ru" else "Configuring Windows background service..."
            self.status_lbl.config(text=msg_task)
            self.progress_bar.set_progress(60)
            self.update()
            self._register_task(target)

        # Create shortcut
        if self.opt_shortcut.get():
            msg_sc = "Создание ярлыка..." if self.lang == "ru" else "Creating desktop shortcut..."
            self.status_lbl.config(text=msg_sc)
            self.progress_bar.set_progress(80)
            self.update()
            self._create_desktop_shortcut(target)

        # Start service
        if self.opt_start.get():
            msg_st = "Запуск фоновой службы..." if self.lang == "ru" else "Starting background service..."
            self.status_lbl.config(text=msg_st)
            self.progress_bar.set_progress(95)
            self.update()
            self._start_service(target)

        if self.opt_browser.get():
            try:
                webbrowser.open("http://127.0.0.1:8765")
            except Exception:
                pass

        self._is_completed = True
        self.progress_bar.set_progress(100)

        msg_done = "Установка успешно завершена." if self.lang == "ru" else "Installation completed successfully."
        btn_open = "Открыть панель" if self.lang == "ru" else "Open Dashboard"
        btn_close = "Закрыть" if self.lang == "ru" else "Close"

        self.status_lbl.config(text=msg_done, fg="#34D399")
        self.install_btn.config(
            text=btn_open,
            state=tk.NORMAL,
            bg="#10B981",
            activebackground="#059669"
        )
        self.exit_btn.config(text=btn_close, state=tk.NORMAL)

    def _register_task(self, target_dir: Path):
        exe_file = target_dir / "oblivion.exe"
        if exe_file.exists():
            cmd_exec = str(exe_file)
            cmd_args = "--daemon"
        else:
            python_exe = sys.executable
            cmd_exec = str(python_exe)
            cmd_args = "-m oblivion.main --daemon"

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
      <Command>{cmd_exec}</Command>
      <Arguments>{cmd_args}</Arguments>
      <WorkingDirectory>{str(target_dir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"], capture_output=True, creationflags=flags)
        xml_path = target_dir / "task_def.xml"
        try:
            xml_path.write_text(xml_template, encoding="utf-16")
            res = subprocess.run(["schtasks", "/create", "/tn", TASK_NAME, "/xml", str(xml_path), "/f"], capture_output=True, creationflags=flags)
            if xml_path.exists():
                try:
                    xml_path.unlink()
                except Exception:
                    pass
            if res.returncode == 0:
                return
        except Exception:
            pass

        action = f'"{cmd_exec}" {cmd_args}'
        for trig in ["ONSTART", "ONLOGON"]:
            cmd = [
                "schtasks", "/create",
                "/tn", TASK_NAME,
                "/tr", action,
                "/sc", trig,
                "/rl", "HIGHEST",
                "/f"
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, check=False, creationflags=flags)
                if res.returncode == 0:
                    break
            except Exception:
                pass

    def _create_desktop_shortcut(self, target_dir: Path):
        locations = []
        public_desktop = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"
        if public_desktop.exists():
            locations.append(public_desktop)
        user_desktop = Path.home() / "Desktop"
        if user_desktop.exists() and user_desktop not in locations:
            locations.append(user_desktop)

        ico_file = target_dir / "app.ico"
        icon_line = f"IconFile={ico_file}\n" if ico_file.exists() else ""
        content = f"[InternetShortcut]\nURL=http://127.0.0.1:8765\n{icon_line}IconIndex=0\n"

        for dest_folder in locations:
            try:
                shortcut_path = dest_folder / "OBLIVION.url"
                shortcut_path.write_text(content, encoding="utf-8")
            except Exception:
                pass

    def _start_service(self, target_dir: Path):
        exe_file = target_dir / "oblivion.exe"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        try:
            if exe_file.exists():
                subprocess.Popen([str(exe_file), "--daemon"], cwd=str(target_dir), creationflags=flags)
            else:
                pythonw = Path(sys.executable).parent / "pythonw.exe"
                py = str(pythonw) if pythonw.exists() else sys.executable
                subprocess.Popen([py, "-m", "oblivion.main", "--daemon"], cwd=str(target_dir), creationflags=flags)
        except Exception:
            pass

def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    elevate_if_needed()
    parser = argparse.ArgumentParser(description="OBLIVION Installer", prefix_chars="-/")
    parser.add_argument("--silent", "-s", "/silent", "/SILENT", dest="silent", action="store_true", help="Silent installation")
    parser.add_argument("--verysilent", "/verysilent", "/VERYSILENT", dest="verysilent", action="store_true", help="Very silent installation")
    args, _ = parser.parse_known_args()

    is_silent = bool(args.silent or args.verysilent)
    app = OblivionInstallerApp(silent=is_silent)
    if is_silent:
        app.perform_installation()
        sys.exit(0)
    app.mainloop()

if __name__ == "__main__":
    main()
