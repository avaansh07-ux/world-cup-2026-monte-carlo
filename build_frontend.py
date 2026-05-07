from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
PUBLIC_DIR = ROOT / "public"
DIST_DIR = FRONTEND_DIR / "dist"


def main() -> None:
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    shutil.copytree(DIST_DIR, PUBLIC_DIR)


if __name__ == "__main__":
    main()
