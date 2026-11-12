import ctypes
import os
import stat
import uuid
from pathlib import Path
from typing import List, Union

def _clear_file_attributes(file_path: Path) -> None:
    try:
        os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetFileAttributesW(str(file_path), 0x80)
        except Exception:
            pass

def shred_file(path: Union[str, Path], passes: int = 3) -> bool:
    target = Path(path).resolve()
    if not target.exists() or not target.is_file():
        return False

    _clear_file_attributes(target)
    file_size = target.stat().st_size
    chunk_size = 64 * 1024

    try:
        with open(target, "r+b") as f:
            fd = f.fileno()
            for p in range(passes):
                f.seek(0)
                remaining = file_size
                while remaining > 0:
                    current_chunk = min(remaining, chunk_size)
                    if p == passes - 1:
                        f.write(b"\x00" * current_chunk)
                    elif p % 2 == 1:
                        f.write(b"\xaa" * current_chunk)
                    else:
                        f.write(os.urandom(current_chunk))
                    remaining -= current_chunk
                f.flush()
                os.fsync(fd)
            f.seek(0)
            f.truncate(0)

        random_name = target.parent / f"oblivion_shred_{uuid.uuid4().hex}.tmp"
        target.rename(random_name)
        random_name.unlink(missing_ok=True)
        return True
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except Exception:
            pass
        return False

def shred_directory(path: Union[str, Path], passes: int = 3) -> bool:
    target = Path(path).resolve()
    if not target.exists() or not target.is_dir():
        return False

    for root, dirs, files in os.walk(target, topdown=False):
        for name in files:
            file_path = Path(root) / name
            shred_file(file_path, passes=passes)
        for name in dirs:
            dir_path = Path(root) / name
            _clear_file_attributes(dir_path)
            try:
                dir_path.rmdir()
            except Exception:
                pass

    _clear_file_attributes(target)
    try:
        target.rmdir()
        return True
    except Exception:
        return False

def shred_target_paths(paths: List[str], passes: int = 3) -> List[dict]:
    results = []
    for p in paths:
        path_obj = Path(p).resolve()
        if not path_obj.exists():
            results.append({"path": p, "status": "not_found", "success": False})
            continue
        if path_obj.is_file():
            ok = shred_file(path_obj, passes=passes)
            results.append({"path": p, "status": "shredded_file", "success": ok})
        elif path_obj.is_dir():
            ok = shred_directory(path_obj, passes=passes)
            results.append({"path": p, "status": "shredded_dir", "success": ok})
    return results

def shred_database_files(db_path: Path, passes: int = 3) -> None:
    wal_file = Path(str(db_path) + "-wal")
    shm_file = Path(str(db_path) + "-shm")

    if wal_file.exists():
        shred_file(wal_file, passes=passes)
    if shm_file.exists():
        shred_file(shm_file, passes=passes)
    if db_path.exists():
        shred_file(db_path, passes=passes)
