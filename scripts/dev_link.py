"""Make the monorepo packages importable in the active virtualenv.

Why this exists: on some setups (notably when the project path contains a
space), setuptools' editable-install `.pth` uses an *import-hook* that the
interpreter's site processing does not execute, so `pip install -e .` leaves
`import shared` failing. Plain *path-line* `.pth` files ARE processed reliably,
so this script writes one listing every package source directory.

Run once after creating the venv / installing deps:

    python scripts/dev_link.py

It is idempotent and writes into whichever site-packages is currently active.
"""

from __future__ import annotations

import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIRS = [
    "packages/shared",
    "packages/ingestion",
    "packages/retrieval",
    "packages/synthesis",
    "packages/verification",
    "packages/evals",
    "packages/audit",
    "apps/api",
]
PTH_NAME = "trustrag_packages.pth"


def _site_packages() -> Path:
    # Prefer the venv's site-packages; fall back to the first global one.
    candidates = site.getsitepackages() if hasattr(site, "getsitepackages") else []
    for c in candidates:
        if "site-packages" in c:
            return Path(c)
    if candidates:
        return Path(candidates[0])
    return Path(site.getusersitepackages())


def main() -> None:
    sp = _site_packages()
    sp.mkdir(parents=True, exist_ok=True)
    lines = [str(ROOT / d) for d in PACKAGE_DIRS]
    pth = sp / PTH_NAME
    pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {pth}")
    print("Linked package directories:")
    for line in lines:
        print(f"  {line}")
    print(f"\nUsing interpreter: {sys.executable}")
    print("Now `import shared`, `import retrieval`, etc. work in any process.")


if __name__ == "__main__":
    main()
