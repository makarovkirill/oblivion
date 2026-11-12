# OBLIVION

Local Dead Man's Switch, encrypted credential escrow, and file shredder for Windows 10/11.

OBLIVION runs silently as a background Windows service (OblivionWatchdog) with a local web dashboard at http://127.0.0.1:8765 and two-way Telegram bot integration. If you fail to check in within your configured timeframe, the service automatically delivers assigned secrets to your trusted contacts and permanently wipes local data.

## Features

- Encrypted Vault (oblivion.db): Secrets and file attachments are encrypted locally with AES-256-GCM using keys derived via Argon2id. Plaintext credentials are never stored on disk.
- Split-Key Escrow: Each encryption key is split (2-of-2) between an offline recovery key given to your contact and a release fragment held by the service. Neither side can decrypt the data alone until the switch triggers.
- Passphrase-Gated Check-Ins: Resetting the countdown or cancelling an active grace period requires a dedicated passphrase of 16+ characters, protected by exponential backoff against brute-force attempts.
- Two-Way Telegram Bot: Check status (/status), receive urgent grace-period alerts, perform remote check-ins by sending your passphrase (auto-deleted instantly), and trigger emergency wipes via /panic.
- File and Database Shredder: Multi-pass overwrite (random bytes and zeroes) of configured directories, attachments, and the database before unlinking. Supports Transfer & Delete and Delete Only policies, plus a dry-run simulation mode.

## Installation

### Windows Installer
1. Run dist/OblivionSetup.exe (requests UAC Administrator elevation).
2. Choose interface language (EN or RU) and target directory (C:\Program Files\OBLIVION by default).
3. Click Install. The installer registers the OblivionWatchdog scheduled task, starts the service, and opens http://127.0.0.1:8765 in your default browser.

### First-Run Setup Wizard
On first launch, the guided web wizard configures:
1. Interface language (EN / RU).
2. Master vault password, 16+ character check-in passphrase, and 4+ character uninstall key.
3. Telegram bot token (from @BotFather), your Chat ID (with inline test ping), and optional SMTP settings.
4. Inactivity timer threshold and grace period duration.

### Uninstallation
Run uninstall.bat as Administrator from the installation directory, enter your uninstall PIN, and the script will terminate background processes, remove the scheduled task, and delete shortcuts.

---
AI-assisted development