import os
import shutil
from pathlib import Path
from platformdirs import user_cache_path

def cache_path(override=None):
    return Path(override).expanduser().resolve() if override else user_cache_path("apk-audit", appauthor=False)

def find_jadx():
    configured = os.environ.get("JADX_PATH")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
    return shutil.which("jadx") or shutil.which("jadx.bat")

def doctor():
    from .engines import CodexEngine, ClaudeEngine
    return {"jadx": find_jadx(), "java": shutil.which("java"),
            "claude": shutil.which("claude"), "codex": shutil.which("codex"),
            "live_engine_adapters": f"{CodexEngine().name if shutil.which('codex') else 'codex (chưa cài)'}, {ClaudeEngine.name}", "cache_dir": str(cache_path())}
