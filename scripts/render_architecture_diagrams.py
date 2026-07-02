#!/usr/bin/env python3
# Author: Member D — architecture diagram renderer
# Purpose: Export Mermaid .mmd files to PNG for slides and demo day

"""Render docs/architecture/*.mmd to PNG using @mermaid-js/mermaid-cli (mmdc)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCH_DIR = PROJECT_ROOT / "docs" / "architecture"
OUTPUT_DIR = ARCH_DIR / "images"


def find_mmdc() -> list[str] | None:
    """Return command prefix to invoke mermaid-cli."""
    if shutil.which("mmdc"):
        return ["mmdc"]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "@mermaid-js/mermaid-cli"]
    return None


def render_one(mmdc_cmd: list[str], mmd_file: Path, out_png: Path) -> int:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *mmdc_cmd,
        "-i",
        str(mmd_file),
        "-o",
        str(out_png),
        "-b",
        "transparent",
        "-w",
        "1600",
        "-H",
        "900",
    ]
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=PROJECT_ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Render architecture Mermaid diagrams to PNG")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for PNG output (default: docs/architecture/images)",
    )
    args = parser.parse_args()

    mmd_files = sorted(ARCH_DIR.glob("*.mmd"))
    if not mmd_files:
        print(f"No .mmd files found in {ARCH_DIR}", file=sys.stderr)
        return 1

    mmdc_cmd = find_mmdc()
    if not mmdc_cmd:
        print(
            "ERROR: mermaid-cli not found. Install with:\n"
            "  npm install -g @mermaid-js/mermaid-cli\n"
            "  # or ensure npx is available",
            file=sys.stderr,
        )
        return 1

    failed = 0
    for mmd_file in mmd_files:
        out_png = args.output_dir / f"{mmd_file.stem}.png"
        rc = render_one(mmdc_cmd, mmd_file, out_png)
        if rc != 0:
            failed += 1
            print(f"FAILED: {mmd_file.name}", file=sys.stderr)
        else:
            print(f"OK: {out_png.relative_to(PROJECT_ROOT)}")

    if failed:
        print(f"\n{failed} diagram(s) failed to render.", file=sys.stderr)
        return 1

    print(f"\nRendered {len(mmd_files)} diagram(s) -> {args.output_dir.relative_to(PROJECT_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
