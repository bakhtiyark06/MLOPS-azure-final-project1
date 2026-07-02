#!/usr/bin/env python3
# Author: Member C — Docker image build helper
# Purpose: Build and optionally push the API image to Azure Container Registry

"""Build and optionally push the outage prediction API Docker image."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Docker image for the outage prediction API")
    parser.add_argument("--image", default=os.getenv("IMAGE_NAME", "outage-predictor"))
    parser.add_argument("--tag", default=os.getenv("IMAGE_TAG", "latest"))
    parser.add_argument("--acr", default=os.getenv("ACR_NAME"), help="Azure Container Registry name")
    parser.add_argument("--push", action="store_true", help="Push image to ACR after build")
    parser.add_argument("--platform", default="linux/amd64")
    args = parser.parse_args()

    local_tag = f"{args.image}:{args.tag}"
    run(["docker", "build", "--platform", args.platform, "-t", local_tag, "."])

    if args.push:
        if not args.acr:
            print("ERROR: --acr or ACR_NAME is required when using --push", file=sys.stderr)
            return 1
        remote = f"{args.acr}.azurecr.io/{local_tag}"
        run(["az", "acr", "login", "--name", args.acr])
        run(["docker", "tag", local_tag, remote])
        run(["docker", "push", remote])
        print(f"Pushed {remote}")

    print(f"Built {local_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
