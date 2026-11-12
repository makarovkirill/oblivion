import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field

def get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

def get_default_data_dir() -> Path:
    custom = os.environ.get("OBLIVION_DATA_DIR")
    if custom:
        return Path(custom)
    
    candidates = []
    if os.name == "nt":
        candidates.append(Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "OBLIVION")
    candidates.append(Path(__file__).resolve().parent.parent / "data")
    candidates.append(Path.home() / ".oblivion")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue

    fallback = Path(__file__).resolve().parent.parent / "data"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return fallback

class Settings(BaseModel):
    app_name: str = "OBLIVION"
    app_version: str = "1.0.0"
    task_name: str = "OblivionWatchdog"
    mutex_name: str = "Global\\Oblivion_Instance_Mutex"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Field(default_factory=get_default_data_dir)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "oblivion.db"
        
    @property
    def uploads_dir(self) -> Path:
        d = self.data_dir / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        d = self.data_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def bundles_dir(self) -> Path:
        d = self.data_dir / "bundles"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def static_dir(self) -> Path:
        bundle = get_bundle_dir()
        candidate1 = bundle / "oblivion" / "static"
        if candidate1.exists():
            return candidate1
        candidate2 = Path(__file__).resolve().parent / "static"
        if candidate2.exists():
            return candidate2
        return candidate1

settings = Settings()
