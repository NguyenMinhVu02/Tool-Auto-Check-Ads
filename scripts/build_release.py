"""Build the end-user ZIP (apk-audit-<version>.zip) from the committed tree.

Usage: uv run python scripts/build_release.py [--ref HEAD] [--out dist]
Only files tracked by git at --ref are packed, so local outputs, caches and
secrets never end up in the archive.
"""

import argparse
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["apk_audit", "rulepacks", "installer", "pyproject.toml", "uv.lock", "README.md"]
REQUIRED = ["apk_audit/web_assets/app.js", "installer/Cai-dat-Windows.bat",
            "installer/Cai-dat-macOS.command", "installer/cai-dat-linux.sh", "uv.lock"]


def version():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def build(ref="HEAD", out=ROOT / "dist", name=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    name = name or f"apk-audit-{version()}"
    target = out / f"{name}.zip"
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip", f"--prefix={name}/",
                    "-o", str(target), ref, *INCLUDE], check=True)
    with zipfile.ZipFile(target) as bundle:
        names = set(bundle.namelist())
        missing = [path for path in REQUIRED if f"{name}/{path}" not in names]
        unwanted = [n for n in names if "/tests/" in n or "/out/" in n or n.endswith(".pyc")]
    if missing or unwanted:
        target.unlink()
        raise SystemExit(f"Gói không hợp lệ. Thiếu: {missing}. Không được có: {unwanted[:5]}")
    return target


def main():
    parser = argparse.ArgumentParser(description="Đóng gói ZIP cho người dùng cuối")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--name")
    args = parser.parse_args()
    print(build(args.ref, args.out, args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
